# *** imports

# ** core
import os
from pathlib import Path
import subprocess
import sys
import sysconfig
import venv

# ** infra
import pytest

# *** fixtures

# ** fixture: installed_cli
@pytest.fixture(scope='session')
def installed_cli(tmp_path_factory):
    '''
    Build/install the wheel offline, outside checkout, sharing only test dependencies.
    '''

    root = Path(__file__).resolve().parents[1]
    sandbox = tmp_path_factory.mktemp('installed-cli')
    wheels = sandbox / 'wheels'
    wheels.mkdir()
    env = {key: value for key, value in os.environ.items() if key != 'PYTHONPATH'}
    env['PYTHONNOUSERSITE'] = '1'
    built = subprocess.run(
        [sys.executable, '-m', 'pip', 'wheel', '--no-deps', '--no-build-isolation', '--no-index', '--wheel-dir', str(wheels), str(root)],
        cwd=sandbox,
        env=env,
        capture_output=True,
        text=True,
        timeout=60,
    )
    assert built.returncode == 0, built.stdout + built.stderr

    # Use a separate noneditable installation, with released dependencies already on disk.
    environment = sandbox / 'venv'
    venv.EnvBuilder(with_pip=True).create(environment)
    python = environment / 'bin' / 'python'
    site_packages = next((environment / 'lib').glob('python*/site-packages'))
    (site_packages / 'released-test-dependencies.pth').write_text(sysconfig.get_path('purelib') + '\n')
    wheel = next(wheels.glob('tiferet_stocks-*.whl'))
    installed = subprocess.run(
        [str(python), '-m', 'pip', 'install', '--no-deps', '--no-index', str(wheel)],
        cwd=sandbox,
        env=env,
        capture_output=True,
        text=True,
        timeout=60,
    )
    assert installed.returncode == 0, installed.stdout + installed.stderr
    return {'python': python, 'script': environment / 'bin' / 'tiferet-stocks', 'env': env, 'root': sandbox, 'site': site_packages}
