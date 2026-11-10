"""Executable Watchlist Acceptance and Write-Boundary Probe"""

# *** imports

# ** core
import ast
import inspect
import io
import json
import os
from pathlib import Path
import sys
import textwrap
from unittest import mock

# ** infra
import yaml
from tiferet import App, TiferetAPIError

# ** app
from tiferet_stocks.events import WatchlistEvent
import tiferet_stocks.events.watchlist as watchlist_events
from tiferet_stocks.mappers import WatchlistAggregate

# *** functions

# ** function: run_probe
def run_probe(directory: Path, extension: str, mutant: str = 'none') -> dict:
    '''
    Run real features with a runtime audit boundary and optional bounded mutant.

    :param directory: The isolated working directory.
    :type directory: Path
    :param extension: The YAML or JSON storage extension.
    :type extension: str
    :param mutant: The in-process mutation, or none.
    :type mutant: str
    :return: The completed acceptance and write-attribution counts.
    :rtype: dict
    '''

    # Prepare isolated configuration before installing the process-local audit hook.
    root = Path(__file__).resolve().parents[1]
    package = str(root / 'tiferet_stocks') + os.sep
    repository = str(root / 'tiferet_stocks' / 'repos' / 'watchlist.py')
    config = yaml.safe_load((root / 'config.yml').read_text())
    storage = directory / 'new' / f'watchlists.{extension}'
    config['services']['watchlist_service']['params']['watchlist_config'] = str(storage)
    config['services']['price_service'] = {
        'module_path': 'tiferet_stocks.repos.static',
        'class_name': 'StaticPriceRepository',
        'params': {'fixture_path': str(root / 'tests' / 'repos' / 'fixtures' / 'static_prices.yml')},
    }
    payload = (root / 'tests' / 'repos' / 'payloads' / 'spy.json').read_bytes()
    for code, error in config['errors'].items():
        if code.startswith('WATCHLIST_'):
            error['message'][0]['text'] = 'Acceptance: ' + error['message'][0]['text']
    (directory / 'config.yml').write_text(yaml.safe_dump(config, sort_keys=False))
    os.chdir(directory)
    writes = []

    # Attribute writes to the innermost production stocks frame, not to test helpers.
    def audit(event: str, args: tuple) -> None:
        '''
        Reject production writes outside the watchlist repository.

        :param event: The Python runtime audit event.
        :type event: str
        :param args: The event arguments.
        :type args: tuple
        :return: None.
        :rtype: None
        '''

        is_write = event in {'os.mkdir', 'os.remove', 'os.rmdir', 'os.rename', 'os.link', 'os.symlink', 'os.truncate', 'os.chmod', 'os.chown', 'os.utime'}
        if event == 'open':
            mode, flags = args[1], args[2]
            is_write = (isinstance(mode, str) and any(flag in mode for flag in 'wax+')) or bool(flags & (os.O_WRONLY | os.O_RDWR | os.O_CREAT | os.O_TRUNC | os.O_APPEND))
        if not is_write:
            return

        # Core loader frames are allowed only when their nearest stocks caller is the repository.
        frame = sys._getframe(1)
        while frame is not None:
            source = frame.f_code.co_filename
            if source.startswith(package):
                if source != repository:
                    raise AssertionError(f'WRITE_BOUNDARY: {event} from {source}')
                writes.append({'event': event, 'source': source})
                return
            frame = frame.f_back

    # The hook lives only in this subprocess; no persistent interpreter is changed.
    sys.addaudithook(audit)
    app = App('stocks_client', app_config=str(directory / 'config.yml'))
    # Include every pre-existing read feature so non-watchlist modules are audited too.
    with mock.patch('urllib.request.urlopen') as opener:
        response = mock.MagicMock()
        response.__enter__.side_effect = lambda: io.BytesIO(payload)
        opener.return_value = response
        assert app.run('symbols.get', data={'id': 'SPY'}).symbols['SPY'].id == 'SPY'
        assert app.run('symbols.resolve', data={'ids': ['SPY']}).symbols['SPY'].id == 'SPY'
    assert app.run('quotes.get', data={'symbols': ['AAPL']}).quotes['AAPL'].source == 'static'
    assert 'NASDAQ' in app.run('exchanges.list')

    first = '2026-11-06T14:00:00-07:00'
    second = '2026-11-06T15:00:00-07:00'

    # Mutants are local monkeypatches; production source and earlier commits stay immutable.
    if mutant == 'wrong_index':
        original_move = WatchlistAggregate.move_symbol
        WatchlistAggregate.move_symbol = lambda self, symbol_id, to_index=-1: original_move(self, symbol_id, to_index=-1)
    elif mutant == 'drop_precheck':
        WatchlistEvent.verify = lambda self, **kwargs: None
    elif mutant == 'reset_created':
        original_upsert = WatchlistAggregate.upsert

        def reset_created(self, at: str) -> None:
            '''
            Deliberately reset creation time to prove the acceptance check is live.

            :param at: The change timestamp.
            :type at: str
            :return: None.
            :rtype: None
            '''

            original_upsert(self, at=at)
            self.created_at = at

        WatchlistAggregate.upsert = reset_created
    elif mutant == 'extra_write':
        namespace = {**vars(watchlist_events), 'Path': Path, 'target': str(directory / 'rogue.txt')}
        method = ast.parse(textwrap.dedent(inspect.getsource(WatchlistEvent.now)))
        method.body[0].body.insert(1, ast.parse("Path(target).write_text('unexpected')").body[0])
        ast.fix_missing_locations(method)
        exec(compile(method, str(root / 'tiferet_stocks' / 'events' / 'watchlist.py'), 'exec'), namespace)
        WatchlistEvent.now = namespace['now']
    elif mutant != 'none':
        raise ValueError(f'Unknown mutant: {mutant}')

    # Missing reads create no file or directory; a real feature creates the first file.
    assert app.run('watchlists.list') == []
    assert not storage.parent.exists()
    app.run('watchlists.create', data={'id': 'keeper', 'name': 'Keeper', 'at': first})
    keeper_bytes = app.run('watchlists.get', data={'id': 'keeper'}).model_dump()
    assert storage.exists()
    app.run('watchlists.create', data={'id': 'clock', 'name': 'Clock'})
    assert app.run('watchlists.get', data={'id': 'clock'}).created_at is not None

    # Each case starts from the same ordered baseline and asserts a literal final order.
    cases = [
        ('add', {}, ['SPY', 'QQQ', 'XLK', 'NEW']),
        ('add', {'index': -1}, ['SPY', 'QQQ', 'XLK', 'NEW']),
        ('add', {'index': 0}, ['NEW', 'SPY', 'QQQ', 'XLK']),
        ('add', {'index': 1}, ['SPY', 'NEW', 'QQQ', 'XLK']),
        ('add', {'index': 3}, ['SPY', 'QQQ', 'XLK', 'NEW']),
        ('add', {'index': 99}, ['SPY', 'QQQ', 'XLK', 'NEW']),
        ('move', {}, ['QQQ', 'XLK', 'SPY']),
        ('move', {'to_index': -1}, ['QQQ', 'XLK', 'SPY']),
        ('move', {'to_index': 0}, ['SPY', 'QQQ', 'XLK']),
        ('move', {'to_index': 1}, ['QQQ', 'SPY', 'XLK']),
        ('move', {'to_index': 2}, ['QQQ', 'XLK', 'SPY']),
        ('move', {'to_index': 3}, ['QQQ', 'XLK', 'SPY']),
        ('move', {'to_index': 99}, ['QQQ', 'XLK', 'SPY']),
        ('move', {'symbol_id': 'XLK', 'to_index': 1}, ['SPY', 'XLK', 'QQQ']),
    ]
    for number, (operation, options, expected) in enumerate(cases):
        id = f'case{number}'
        app.run('watchlists.create', data={'id': id, 'name': id, 'symbol_ids': ['SPY', 'QQQ', 'XLK'], 'at': first})
        data = {'id': id, 'symbol_id': 'NEW' if operation == 'add' else 'SPY', 'at': second, **options}
        result = app.run(f'watchlists.{operation}', data=data)
        assert result.symbol_ids == expected, f'ORDER: {operation} {options}'
        assert result.created_at == first, 'CREATION_TIME_RESET'
        assert result.updated_at == second

        # Reads must preserve exact bytes as well as deterministic timestamps.
        before = storage.read_bytes()
        mtime = storage.stat().st_mtime_ns
        assert app.run('watchlists.get', data={'id': id}) == result
        app.run('watchlists.list')
        assert storage.read_bytes() == before
        assert storage.stat().st_mtime_ns == mtime

    # Verify every catalogued outcome and unchanged bytes under both file formats.
    rejected = [
        ('create', {'id': 'keeper', 'name': 'Taken'}, 'WATCHLIST_EXISTS', 'Watchlist already exists: keeper.'),
        ('create', {'id': 'dup', 'name': 'Dup', 'symbol_ids': ['SPY', 'SPY']}, 'WATCHLIST_SYMBOL_EXISTS', 'Symbol already exists in watchlist dup: SPY.'),
        ('get', {'id': 'absent'}, 'WATCHLIST_NOT_FOUND', 'Watchlist not found: absent.'),
        ('add', {'id': 'case0', 'symbol_id': 'SPY'}, 'WATCHLIST_SYMBOL_EXISTS', 'Symbol already exists in watchlist case0: SPY.'),
        ('add', {'id': 'keeper', 'symbol_id': 'NEW', 'index': -2}, 'WATCHLIST_INDEX_OUT_OF_RANGE', 'Watchlist index must be -1 or greater: -2.'),
        ('move', {'id': 'case0', 'symbol_id': 'SPY', 'to_index': -2}, 'WATCHLIST_INDEX_OUT_OF_RANGE', 'Watchlist index must be -1 or greater: -2.'),
        ('remove', {'id': 'keeper', 'symbol_id': 'ABSENT'}, 'WATCHLIST_SYMBOL_NOT_FOUND', 'Symbol not found in watchlist keeper: ABSENT.'),
        ('move', {'id': 'keeper', 'symbol_id': 'ABSENT'}, 'WATCHLIST_SYMBOL_NOT_FOUND', 'Symbol not found in watchlist keeper: ABSENT.'),
    ]
    for operation, data, code, message in rejected:
        before = storage.read_bytes()
        mtime = storage.stat().st_mtime_ns
        try:
            app.run(f'watchlists.{operation}', data=data)
        except TiferetAPIError as error:
            assert error.error_code == code, f'PRECHECK_CODE: {error.error_code}'
            assert error.message == 'Acceptance: ' + message, 'CONFIGURED_MESSAGE'
        else:
            raise AssertionError(f'PRECHECK_MISSING: {operation}')
        assert storage.read_bytes() == before
        assert storage.stat().st_mtime_ns == mtime

    # Deletion preserves another watchlist including its original timestamp.
    app.run('watchlists.delete', data={'id': 'case0'})
    assert app.run('watchlists.get', data={'id': 'keeper'}).model_dump() == keeper_bytes
    assert writes and all(item['source'] == repository for item in writes)
    assert any(item['event'] == 'open' for item in writes)
    return {'format': extension, 'ordering_cases': len(cases), 'rejected_cases': len(rejected), 'audited_writes': len(writes)}

if __name__ == '__main__':
    print(json.dumps(run_probe(Path(sys.argv[1]), sys.argv[2], mutant=sys.argv[3]), sort_keys=True))
