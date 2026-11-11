"""Public CLI bootstrap and offline installed-wheel tests."""

# *** imports

# ** core
from importlib import metadata
from pathlib import Path
import subprocess

# ** infra
import pytest
import yaml

# ** app
from tiferet_stocks.blueprints.cli import build_cli, create_cli_request_context, main
from tiferet_stocks.contexts import StocksCliRequestContext

# *** fixtures

# ** fixture: cli_config
@pytest.fixture
def cli_config(tmp_path):
    '''
    Supply a real CLI catalog in a directory independent of process CWD.

    :param tmp_path: The isolated temporary data directory.
    :type tmp_path: Path
    :return: The configured fixture value or completed response.
    :rtype: Any
    '''

    source = Path(__file__).resolve().parents[1] / 'config.yml'
    config = yaml.safe_load(source.read_text())
    config['services']['watchlist_service']['params']['watchlist_config'] = str(tmp_path / 'never-created.yml')
    target = tmp_path / 'selected.yml'
    target.write_text(yaml.safe_dump(config, sort_keys=False))
    return target

# *** tests

# ** test: create_cli_request_context
def test_create_cli_request_context_preserves_core_shape():
    '''
    Preserve the public CLI request construction contract.

    :return: None; assertions enforce the contract.
    :rtype: None
    '''

    context = create_cli_request_context('stocks_cli', 'quotes.get', headers={'test': 'value'}, data={'symbols': ['AAPL']})
    assert isinstance(context, StocksCliRequestContext)
    assert context.headers == {'test': 'value', 'interface_id': 'stocks_cli'}
    assert context.feature_id == 'quotes.get'
    assert context.data == {'symbols': ['AAPL']}

# ** test: explicit_config
def test_explicit_config_drives_all_core_readers(cli_config, tmp_path, monkeypatch, capsys):
    '''
    Exercise the configured CLI bootstrap contract.

    :param cli_config: The selected reference configuration path.
    :type cli_config: Path
    :param tmp_path: The isolated temporary data directory.
    :type tmp_path: Path
    :param monkeypatch: The scoped environment/working-directory adapter.
    :type monkeypatch: pytest.MonkeyPatch
    :param capsys: The captured core response streams.
    :type capsys: pytest.CaptureFixture
    :return: None; assertions enforce the contract.
    :rtype: None
    '''

    elsewhere = tmp_path / 'elsewhere'
    elsewhere.mkdir()
    monkeypatch.chdir(elsewhere)
    build_cli(app_config=str(cli_config), argv=['exchanges', 'list'])
    assert 'NYSE_ARCA' in capsys.readouterr().out
    build_cli(app_config=str(cli_config), argv=['watchlists', 'list'])
    assert not (tmp_path / 'never-created.yml').exists()
    assert list(elsewhere.iterdir()) == []

# ** test: default_config
def test_main_defaults_to_cwd_config(cli_config, tmp_path, monkeypatch, capsys):
    '''
    Exercise the configured CLI bootstrap contract.

    :param cli_config: The selected reference configuration path.
    :type cli_config: Path
    :param tmp_path: The isolated temporary data directory.
    :type tmp_path: Path
    :param monkeypatch: The scoped environment/working-directory adapter.
    :type monkeypatch: pytest.MonkeyPatch
    :param capsys: The captured core response streams.
    :type capsys: pytest.CaptureFixture
    :return: None; assertions enforce the contract.
    :rtype: None
    '''

    (tmp_path / 'config.yml').write_bytes(cli_config.read_bytes())
    monkeypatch.chdir(tmp_path)
    assert main(argv=['exchanges', 'list']) is None
    assert 'NASDAQ' in capsys.readouterr().out

# ** test: installed_wheel
def test_installed_wheel_uses_site_packages_and_released_beta(installed_cli):
    '''
    Exercise the configured CLI bootstrap contract.

    :param installed_cli: The offline noneditable installed console environment.
    :type installed_cli: dict
    :return: None; assertions enforce the contract.
    :rtype: None
    '''

    # Read host pytest-env versions independently of the sandbox subprocess.
    expected_tiferet = metadata.version('tiferet')
    expected_stocks = metadata.version('tiferet-stocks')
    checkout = str(Path(__file__).resolve().parents[1])

    evidence = subprocess.run(
        [str(installed_cli['python']), '-c', 'import importlib.metadata as m; import tiferet_stocks; import tiferet; print(tiferet_stocks.__file__); print(m.version("tiferet")); print(tiferet.__file__); print(m.version("tiferet-stocks"))'],
        cwd=installed_cli['root'],
        env=installed_cli['env'],
        capture_output=True,
        text=True,
        timeout=20,
    )
    assert evidence.returncode == 0, evidence.stderr
    lines = evidence.stdout.splitlines()

    # Forced wheel install must originate in the sandbox, share host tiferet, and match host versions.
    assert str(installed_cli['site']) in lines[0]
    assert checkout not in lines[0]
    assert lines[1] == expected_tiferet
    assert 'site-packages/tiferet/' in lines[2]
    assert lines[3] == expected_stocks
    assert installed_cli['script'].is_file()

# ** test: installed_console
@pytest.mark.parametrize('explicit', [True, False])
def test_installed_console_outside_checkout(installed_cli, cli_config, tmp_path, explicit):
    '''
    Exercise the configured CLI bootstrap contract.

    :param installed_cli: The offline noneditable installed console environment.
    :type installed_cli: dict
    :param cli_config: The selected reference configuration path.
    :type cli_config: Path
    :param tmp_path: The isolated temporary data directory.
    :type tmp_path: Path
    :param explicit: Whether to select configuration through --config.
    :type explicit: bool
    :return: None; assertions enforce the contract.
    :rtype: None
    '''

    cwd = tmp_path / 'outside'
    cwd.mkdir()
    arguments = [str(installed_cli['script'])]
    if explicit:
        arguments += ['--config', str(cli_config)]
    else:
        (cwd / 'config.yml').write_bytes(cli_config.read_bytes())
    arguments += ['exchanges', 'list']
    before = {path.name: path.read_bytes() for path in cwd.iterdir()}
    result = subprocess.run(arguments, cwd=cwd, env=installed_cli['env'], capture_output=True, text=True, timeout=20)
    assert result.returncode == 0, result.stdout + result.stderr
    assert 'NYSE_ARCA' in result.stdout
    assert {path.name: path.read_bytes() for path in cwd.iterdir()} == before
