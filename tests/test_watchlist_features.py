"""Tiferet Stocks Watchlist Feature Integration Tests"""

# *** imports

# ** core
from pathlib import Path
from unittest import mock

# ** infra
import pytest
import yaml
from tiferet import App, TiferetAPIError

# ** app
from tiferet_stocks import assets as a
from tiferet_stocks.events import WatchlistEvent

# *** fixtures

# ** fixture: watchlist_app
@pytest.fixture
def watchlist_app(tmp_path: Path, monkeypatch):
    '''
    Use the real reference feature wiring in an isolated working directory.

    :param tmp_path: The temporary directory.
    :type tmp_path: Path
    :param monkeypatch: The scoped working-directory fixture.
    :type monkeypatch: pytest.MonkeyPatch
    :return: The app and configured storage path.
    :rtype: tuple
    '''

    root = Path(__file__).resolve().parents[1]
    config = yaml.safe_load((root / 'config.yml').read_text())
    for code, error in config['errors'].items():
        if code.startswith('WATCHLIST_'):
            error['message'][0]['text'] = 'Configured: ' + error['message'][0]['text']
    (tmp_path / 'config.yml').write_text(yaml.safe_dump(config, sort_keys=False))
    monkeypatch.chdir(tmp_path)

    return App('stocks_client', app_config=str(tmp_path / 'config.yml')), tmp_path / 'data' / 'watchlists.yml'

# *** tests

# ** test_int: first_create_and_all_features
def test_first_create_and_all_features(watchlist_app) -> None:
    '''
    Exercise every feature, first-save creation, stamping and read invariance.

    :param watchlist_app: The app and storage path.
    :type watchlist_app: tuple
    '''

    app, path = watchlist_app
    first = '2026-11-06T14:00:00-07:00'
    second = '2026-11-06T15:00:00-07:00'
    assert app.run('watchlists.list') == []
    assert not path.exists()
    assert not path.parent.exists()

    created = app.run('watchlists.create', data={'id': 'one', 'name': 'One', 'symbol_ids': ['SPY', 'QQQ'], 'at': first})
    assert path.exists()
    assert created.created_at == first
    assert created.updated_at == first
    app.run('watchlists.create', data={'id': 'two', 'name': 'Two', 'at': first})

    updated = app.run('watchlists.update', data={'id': 'one', 'name': 'Renamed', 'description': 'Example', 'at': second})
    assert updated.name == 'Renamed'
    assert updated.description == 'Example'
    assert updated.created_at == first
    assert updated.updated_at == second

    added = app.run('watchlists.add', data={'id': 'one', 'symbol_id': 'UNLOOKED_UP', 'at': second})
    assert added.symbol_ids == ['SPY', 'QQQ', 'UNLOOKED_UP']
    moved = app.run('watchlists.move', data={'id': 'one', 'symbol_id': 'UNLOOKED_UP', 'to_index': 0, 'at': second})
    assert moved.symbol_ids == ['UNLOOKED_UP', 'SPY', 'QQQ']
    removed = app.run('watchlists.remove', data={'id': 'one', 'symbol_id': 'SPY', 'at': second})
    assert removed.symbol_ids == ['UNLOOKED_UP', 'QQQ']
    assert removed.created_at == first
    assert removed.updated_at == second

    original = path.read_bytes()
    mtime = path.stat().st_mtime_ns
    with mock.patch.object(WatchlistEvent, 'now', side_effect=AssertionError('read clock used')):
        assert app.run('watchlists.get', data={'id': 'one'}) == removed
        assert len(app.run('watchlists.list')) == 2
    assert path.read_bytes() == original
    assert path.stat().st_mtime_ns == mtime

    with mock.patch.object(WatchlistEvent, 'now', side_effect=AssertionError('delete clock used')):
        assert app.run('watchlists.delete', data={'id': 'one'}) == 'one'
    assert [item.id for item in app.run('watchlists.list')] == ['two']
    assert app.run('watchlists.get', data={'id': 'two'}).created_at == first

# ** test_int: catalogued_messages_and_no_write_on_error
@pytest.mark.parametrize('feature, data, code, message', [
    ('watchlists.get', {'id': 'absent'}, 'WATCHLIST_NOT_FOUND', 'Watchlist not found: absent.'),
    ('watchlists.create', {'id': 'one', 'name': 'Taken'}, 'WATCHLIST_EXISTS', 'Watchlist already exists: one.'),
    ('watchlists.create', {'id': 'new', 'name': 'New', 'symbol_ids': ['SPY', 'SPY']}, 'WATCHLIST_SYMBOL_EXISTS', 'Symbol already exists in watchlist new: SPY.'),
    ('watchlists.add', {'id': 'one', 'symbol_id': 'SPY'}, 'WATCHLIST_SYMBOL_EXISTS', 'Symbol already exists in watchlist one: SPY.'),
    ('watchlists.remove', {'id': 'one', 'symbol_id': 'QQQ'}, 'WATCHLIST_SYMBOL_NOT_FOUND', 'Symbol not found in watchlist one: QQQ.'),
    ('watchlists.move', {'id': 'one', 'symbol_id': 'QQQ'}, 'WATCHLIST_SYMBOL_NOT_FOUND', 'Symbol not found in watchlist one: QQQ.'),
    ('watchlists.add', {'id': 'one', 'symbol_id': 'QQQ', 'index': -2}, 'WATCHLIST_INDEX_OUT_OF_RANGE', 'Watchlist index must be -1 or greater: -2.'),
    ('watchlists.move', {'id': 'one', 'symbol_id': 'SPY', 'to_index': -2}, 'WATCHLIST_INDEX_OUT_OF_RANGE', 'Watchlist index must be -1 or greater: -2.'),
])
def test_catalogued_messages_and_no_write_on_error(watchlist_app,
                                                   feature: str,
                                                   data: dict,
                                                   code: str,
                                                   message: str) -> None:
    '''
    Resolve configured catalog messages through real feature execution.

    :param watchlist_app: The app and storage path.
    :type watchlist_app: tuple
    :param feature: The feature id.
    :type feature: str
    :param data: The rejected request.
    :type data: dict
    :param code: The expected error id.
    :type code: str
    :param message: The default message before the configured prefix.
    :type message: str
    '''

    app, path = watchlist_app
    app.run('watchlists.create', data={'id': 'one', 'name': 'One', 'symbol_ids': ['SPY'], 'at': '2026-11-06T14:00:00-07:00'})
    original = path.read_bytes()
    mtime = path.stat().st_mtime_ns

    with pytest.raises(TiferetAPIError) as raised:
        app.run(feature, data=data)

    assert raised.value.error_code == code
    assert raised.value.message == 'Configured: ' + message
    assert path.read_bytes() == original
    assert path.stat().st_mtime_ns == mtime

# ** test_int: duplicate_initial_ids_do_not_create_file
def test_duplicate_initial_ids_do_not_create_file(watchlist_app) -> None:
    '''
    Initial duplicates fail through the error catalog before first-save creation.

    :param watchlist_app: The app and storage path.
    :type watchlist_app: tuple
    '''

    app, path = watchlist_app
    with pytest.raises(TiferetAPIError) as raised:
        app.run('watchlists.create', data={'id': 'new', 'name': 'New', 'symbol_ids': ['SPY', 'SPY']})

    assert raised.value.error_code == 'WATCHLIST_SYMBOL_EXISTS'
    assert raised.value.message == 'Configured: Symbol already exists in watchlist new: SPY.'
    assert not path.exists()
    assert not path.parent.exists()

# ** test_int: default_error_catalog_matches_assets
def test_default_error_catalog_matches_assets() -> None:
    '''
    Keep all five watchlist catalog entries equal to their exported defaults.
    '''

    root = Path(__file__).resolve().parents[1]
    config = yaml.safe_load((root / 'config.yml').read_text())
    errors = {code: data for code, data in a.DEFAULT_ERRORS.items() if code.startswith('WATCHLIST_')}

    assert len(errors) == 5
    assert 'UNSUPPORTED_CONFIG_FILE_TYPE' not in config['errors']
    for code, data in errors.items():
        assert config['errors'][code] == data
