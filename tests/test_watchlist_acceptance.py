"""Tiferet Stocks Watchlist Final Acceptance Tests"""

# *** imports

# ** core
import json
import os
from pathlib import Path
import subprocess
import sys

# ** infra
import pytest
import yaml

# ** app
from tiferet_stocks.repos.watchlist import WatchlistConfigRepository

# *** tests

# ** test: feature_format_parity_and_write_boundary
@pytest.mark.parametrize('extension', ['yml', 'json'])
def test_feature_format_parity_and_write_boundary(tmp_path: Path, extension: str) -> None:
    '''
    Exercise real features under a process-isolated production write audit hook.

    :param tmp_path: The isolated subprocess data directory.
    :type tmp_path: Path
    :param extension: The supported persistence format.
    :type extension: str
    '''

    root = Path(__file__).resolve().parents[1]
    result = subprocess.run(
        [sys.executable, '-m', 'tests.watchlist_acceptance_probe', str(tmp_path), extension, 'none'],
        cwd=root,
        env={**os.environ, 'PYTHONDONTWRITEBYTECODE': '1'},
        text=True,
        capture_output=True,
        timeout=30,
    )

    assert result.returncode == 0, result.stdout + result.stderr
    report = json.loads(result.stdout.splitlines()[-1])
    assert report['ordering_cases'] == 14
    assert report['rejected_cases'] == 8
    assert report['audited_writes'] > 0

# ** test: bounded_mutations_are_killed
@pytest.mark.parametrize('extension', ['yml', 'json'])
@pytest.mark.parametrize('mutant, evidence', [
    ('wrong_index', 'ORDER:'),
    ('drop_precheck', 'PRECHECK_MISSING:'),
    ('extra_write', 'WRITE_BOUNDARY:'),
    ('reset_created', 'CREATION_TIME_RESET'),
])
def test_bounded_mutations_are_killed(tmp_path: Path,
                                      extension: str,
                                      mutant: str,
                                      evidence: str) -> None:
    '''
    Prove ordering, catalogued prechecks, write provenance and audit times are live.

    :param tmp_path: The isolated subprocess data directory.
    :type tmp_path: Path
    :param extension: The supported persistence format.
    :type extension: str
    :param mutant: The deliberately wrong in-memory behavior.
    :type mutant: str
    :param evidence: The expected specific failure marker.
    :type evidence: str
    '''

    root = Path(__file__).resolve().parents[1]
    result = subprocess.run(
        [sys.executable, '-m', 'tests.watchlist_acceptance_probe', str(tmp_path), extension, mutant],
        cwd=root,
        env={**os.environ, 'PYTHONDONTWRITEBYTECODE': '1'},
        text=True,
        capture_output=True,
        timeout=30,
    )

    assert result.returncode != 0, f'Mutant survived: {mutant}'
    assert evidence in result.stdout + result.stderr, result.stdout + result.stderr
    assert not (tmp_path / 'rogue.txt').exists()

# ** test: documented_watchlists_round_trip
@pytest.mark.parametrize('extension', ['yml', 'json'])
def test_documented_watchlists_round_trip(tmp_path: Path, extension: str) -> None:
    '''
    Round-trip the actual documented YAML example as YAML and as JSON.

    :param tmp_path: The temporary storage directory.
    :type tmp_path: Path
    :param extension: The persisted document format.
    :type extension: str
    '''

    root = Path(__file__).resolve().parents[1]
    document = (root / 'docs' / 'watchlist-acceptance.md').read_text()
    example = document.split('```yaml\n', 1)[1].split('```', 1)[0]
    data = yaml.safe_load(example)
    path = tmp_path / f'watchlists.{extension}'
    path.write_text(json.dumps(data) if extension == 'json' else example)
    repo = WatchlistConfigRepository(watchlist_config=str(path))
    original = path.read_bytes()
    watchlist = repo.get('etfs')

    assert path.read_bytes() == original
    assert watchlist.symbol_ids == ['SPY', 'QQQ', 'XLK']
    repo.save(watchlist)
    assert yaml.safe_load(path.read_text()) == data
