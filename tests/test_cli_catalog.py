"""Tiferet Stocks CLI Catalog and Request Binding Tests"""

# *** imports

# ** core
import io
from pathlib import Path
from unittest import mock

# ** infra
import pytest
import yaml
from tiferet import App, TiferetAPIError
from tiferet.repos.cli import CliConfigRepository

# ** app
from tiferet_stocks import assets as a
from tiferet_stocks.blueprints.cli import bind_cli_request, parse_cli_args_handler

# *** fixtures

# ** fixture: parser
@pytest.fixture
def parser():
    '''
    Use the real declarative catalog and released core argument parser.

    :return: The bound parser callable.
    :rtype: Callable
    '''

    root = Path(__file__).resolve().parents[1]
    repo = CliConfigRepository(cli_config=str(root / 'config.yml'))
    return parse_cli_args_handler(list_commands=repo.list, get_parent_args=repo.get_parent_arguments)

# ** fixture: dispatch_context
@pytest.fixture
def dispatch_context(tmp_path: Path, monkeypatch):
    '''
    Use actual features with static prices/history and recorded symbol responses.

    :param tmp_path: The temporary configuration and storage directory.
    :type tmp_path: Path
    :param monkeypatch: The scoped working-directory fixture.
    :type monkeypatch: pytest.MonkeyPatch
    :return: The app, bound parser and watchlist storage path.
    :rtype: tuple
    '''

    root = Path(__file__).resolve().parents[1]
    config = yaml.safe_load((root / 'config.yml').read_text())
    config['services']['price_service'] = {
        'module_path': 'tiferet_stocks.repos.static',
        'class_name': 'StaticPriceRepository',
        'params': {
            'fixture_path': str(root / 'tests' / 'repos' / 'fixtures' / 'static_prices.yml'),
            'history_path': str(root / 'tests' / 'repos' / 'fixtures' / 'static_history.csv'),
        },
    }
    config_path = tmp_path / 'config.yml'
    config_path.write_text(yaml.safe_dump(config, sort_keys=False))
    monkeypatch.chdir(tmp_path)
    repo = CliConfigRepository(cli_config=str(config_path))
    parse = parse_cli_args_handler(list_commands=repo.list, get_parent_args=repo.get_parent_arguments)
    app = App('stocks_client', app_config=str(config_path))
    app.run('watchlists.create', data={'id': 'etfs', 'name': 'ETFs', 'symbol_ids': ['SPY', 'QQQ'], 'at': '2026-11-06T14:00:00-07:00'})
    payload = (root / 'tests' / 'repos' / 'payloads' / 'spy.json').read_bytes()

    # Recorded responses never reach an external network endpoint.
    with mock.patch('urllib.request.urlopen') as opener:
        response = mock.MagicMock()
        response.__enter__.side_effect = lambda: io.BytesIO(payload)
        opener.return_value = response
        yield app, parse, tmp_path / 'data' / 'watchlists.yml'

# *** tests

# ** test: catalog_has_exactly_thirteen_feature_ids
def test_catalog_has_exactly_thirteen_feature_ids() -> None:
    '''
    Keep every public command id equal to its existing feature id.
    '''

    root = Path(__file__).resolve().parents[1]
    repo = CliConfigRepository(cli_config=str(root / 'config.yml'))
    expected = {
        a.QUOTES_GET_CLI_CMD_ID,
        a.QUOTES_HISTORY_CLI_CMD_ID,
        a.SYMBOLS_GET_CLI_CMD_ID,
        a.SYMBOLS_RESOLVE_CLI_CMD_ID,
        a.EXCHANGES_LIST_CLI_CMD_ID,
        a.WATCHLISTS_LIST_CLI_CMD_ID,
        a.WATCHLISTS_GET_CLI_CMD_ID,
        a.WATCHLISTS_CREATE_CLI_CMD_ID,
        a.WATCHLISTS_UPDATE_CLI_CMD_ID,
        a.WATCHLISTS_DELETE_CLI_CMD_ID,
        a.WATCHLISTS_ADD_CLI_CMD_ID,
        a.WATCHLISTS_REMOVE_CLI_CMD_ID,
        a.WATCHLISTS_MOVE_CLI_CMD_ID,
    }
    commands = repo.list()

    assert len(commands) == len(expected) == 13
    assert {command.id for command in commands} == expected
    config = yaml.safe_load((root / 'config.yml').read_text())
    for command in commands:
        assert command.id == f'{command.group_key}.{command.key}'
        assert command.key in config['features'][command.group_key]

# ** test: all_command_argument_contracts
@pytest.mark.parametrize('argv, feature_id, expected', [
    (['quotes', 'get', 'SPY', 'QQQ'], 'quotes.get', {'symbols': ['SPY', 'QQQ']}),
    (['quotes', 'history', 'SPY', '--start', '2026-10-19', '--end', '2026-10-23'], 'quotes.history', {'symbol': 'SPY', 'start': '2026-10-19', 'end': '2026-10-23'}),
    (['symbols', 'get', 'SPY'], 'symbols.get', {'id': 'SPY'}),
    (['symbols', 'resolve', 'SPY', 'QQQ', '--expected-exchanges', 'SPY=NYSE_ARCA', 'QQQ=NASDAQ'], 'symbols.resolve', {'ids': ['SPY', 'QQQ'], 'exchanges': {'SPY': 'NYSE_ARCA', 'QQQ': 'NASDAQ'}}),
    (['exchanges', 'list'], 'exchanges.list', {}),
    (['watchlists', 'list'], 'watchlists.list', {}),
    (['watchlists', 'get', 'etfs'], 'watchlists.get', {'id': 'etfs'}),
    (['watchlists', 'create', 'new', '--name', 'New', '--description', 'Example', '--symbol-ids', 'SPY', 'QQQ'], 'watchlists.create', {'id': 'new', 'name': 'New', 'description': 'Example', 'symbol_ids': ['SPY', 'QQQ']}),
    (['watchlists', 'update', 'etfs', '--name', 'Renamed'], 'watchlists.update', {'id': 'etfs', 'name': 'Renamed', 'description': None}),
    (['watchlists', 'delete', 'etfs'], 'watchlists.delete', {'id': 'etfs'}),
    (['watchlists', 'add', 'etfs', 'XLK'], 'watchlists.add', {'id': 'etfs', 'symbol_id': 'XLK', 'index': -1}),
    (['watchlists', 'remove', 'etfs', 'SPY'], 'watchlists.remove', {'id': 'etfs', 'symbol_id': 'SPY'}),
    (['watchlists', 'move', 'etfs', 'SPY'], 'watchlists.move', {'id': 'etfs', 'symbol_id': 'SPY', 'to_index': -1}),
])
def test_all_command_argument_contracts(parser,
                                        argv: list,
                                        feature_id: str,
                                        expected: dict) -> None:
    '''
    Parse public syntax into the unchanged feature request contract.

    :param parser: The real bound parser.
    :type parser: Callable
    :param argv: The public command tokens.
    :type argv: list
    :param feature_id: The expected dispatch id.
    :type feature_id: str
    :param expected: The typed feature argument subset.
    :type expected: dict
    '''

    resolved, headers, data = parser(argv=argv)

    assert resolved == feature_id
    assert headers == {'command_group': argv[0], 'command_key': argv[1]}
    assert {key: data[key] for key in expected} == expected
    assert 'expected_exchanges' not in data
    if feature_id == 'symbols.get':
        assert 'symbol' not in data
    if feature_id == 'symbols.resolve':
        assert 'symbols' not in data

# ** test: optional_resolve_exchanges
def test_optional_resolve_exchanges(parser) -> None:
    '''
    Omission preserves the existing event's optional exchanges contract.

    :param parser: The real bound parser.
    :type parser: Callable
    '''

    _, _, data = parser(argv=['symbols', 'resolve', 'SPY'])

    assert data['ids'] == ['SPY']
    assert data['exchanges'] is None

# ** test: binding_does_not_mutate_parser_data
def test_binding_does_not_mutate_parser_data() -> None:
    '''
    Consumer name translation leaves parser-owned dictionaries unchanged.
    '''

    data = {'symbol': 'SPY', 'group': 'symbols', 'command': 'get'}
    bound = bind_cli_request('symbols.get', data)

    assert data == {'symbol': 'SPY', 'group': 'symbols', 'command': 'get'}
    assert bound == {'id': 'SPY', 'group': 'symbols', 'command': 'get'}
    assert bound is not data

# ** test: negative_indices_reach_features_as_ints
@pytest.mark.parametrize('operation, flag, field', [('add', '--index', 'index'), ('move', '--to-index', 'to_index')])
@pytest.mark.parametrize('value', [-2, -1, 0, 99])
def test_negative_indices_reach_features_as_ints(parser,
                                                 operation: str,
                                                 flag: str,
                                                 field: str,
                                                 value: int) -> None:
    '''
    Parse negative indexes as values rather than options or string defaults.

    :param parser: The real bound parser.
    :type parser: Callable
    :param operation: The watchlist command.
    :type operation: str
    :param flag: The public index flag.
    :type flag: str
    :param field: The existing feature parameter name.
    :type field: str
    :param value: The requested integer value.
    :type value: int
    '''

    _, _, data = parser(argv=['watchlists', operation, 'etfs', 'SPY', flag, str(value)])

    assert data[field] == value
    assert isinstance(data[field], int)

# ** test: required_arguments_rejected_by_core
@pytest.mark.parametrize('argv', [
    ['quotes', 'get'],
    ['quotes', 'history', 'SPY', '--start', '2026-10-19'],
    ['quotes', 'history', 'SPY', '--end', '2026-10-23'],
    ['symbols', 'get'],
    ['symbols', 'resolve'],
    ['watchlists', 'create', 'new'],
    ['watchlists', 'add', 'etfs'],
    ['watchlists', 'move', 'etfs', 'SPY', '--to-index', 'not-an-int'],
])
def test_required_arguments_rejected_by_core(parser, argv: list) -> None:
    '''
    Delegate required-input and type failures to the existing argparse path.

    :param parser: The real bound parser.
    :type parser: Callable
    :param argv: Invalid or incomplete command tokens.
    :type argv: list
    '''

    with pytest.raises(SystemExit) as raised:
        parser(argv=argv)

    assert raised.value.code == 2

# ** test_int: all_commands_dispatch_existing_features
@pytest.mark.parametrize('argv, expected_id', [
    (['quotes', 'get', 'AAPL'], 'quotes.get'),
    (['quotes', 'history', 'AAPL', '--start', '2026-10-19', '--end', '2026-10-23'], 'quotes.history'),
    (['symbols', 'get', 'SPY'], 'symbols.get'),
    (['symbols', 'resolve', 'SPY', '--expected-exchanges', 'SPY=NYSE_ARCA'], 'symbols.resolve'),
    (['exchanges', 'list'], 'exchanges.list'),
    (['watchlists', 'list'], 'watchlists.list'),
    (['watchlists', 'get', 'etfs'], 'watchlists.get'),
    (['watchlists', 'create', 'new', '--name', 'New', '--symbol-ids', 'SPY'], 'watchlists.create'),
    (['watchlists', 'update', 'etfs', '--name', 'Renamed'], 'watchlists.update'),
    (['watchlists', 'delete', 'etfs'], 'watchlists.delete'),
    (['watchlists', 'add', 'etfs', 'XLK', '--index', '0'], 'watchlists.add'),
    (['watchlists', 'remove', 'etfs', 'SPY'], 'watchlists.remove'),
    (['watchlists', 'move', 'etfs', 'SPY', '--to-index', '-1'], 'watchlists.move'),
])
def test_all_commands_dispatch_existing_features(dispatch_context, argv: list, expected_id: str) -> None:
    '''
    Route parsed requests through real history, symbol, quote and watchlist events.

    :param dispatch_context: The real app, parser and storage path.
    :type dispatch_context: tuple
    :param argv: The public command tokens.
    :type argv: list
    :param expected_id: The unchanged feature id.
    :type expected_id: str
    '''

    app, parse, _ = dispatch_context
    feature_id, headers, data = parse(argv=argv)
    result = app.run(feature_id, headers=headers, data=data)

    assert feature_id == expected_id
    assert result is not None
    if feature_id == 'quotes.get':
        assert result.quotes['AAPL'].source == 'static'
    elif feature_id == 'quotes.history':
        assert [bar.date for bar in result] == ['2026-10-19', '2026-10-20', '2026-10-21', '2026-10-23']
    elif feature_id.startswith('symbols.'):
        assert result.symbols['SPY'].exchange == 'NYSE_ARCA'
    elif feature_id == 'exchanges.list':
        assert result == ['NYSE', 'NASDAQ', 'NYSE_ARCA', 'CBOE_BZX', 'NYSE_AMERICAN']
    elif feature_id == 'watchlists.list':
        assert [item.id for item in result] == ['etfs']
    elif feature_id == 'watchlists.delete':
        assert result == 'etfs'
    elif feature_id == 'watchlists.add':
        assert result.symbol_ids == ['XLK', 'SPY', 'QQQ']
    elif feature_id == 'watchlists.remove':
        assert result.symbol_ids == ['QQQ']
    elif feature_id == 'watchlists.move':
        assert result.symbol_ids == ['QQQ', 'SPY']
    elif feature_id == 'watchlists.create':
        assert result.id == 'new' and result.symbol_ids == ['SPY']
    elif feature_id == 'watchlists.update':
        assert result.name == 'Renamed'
    else:
        assert result.id == 'etfs'

# ** test_int: invalid_index_dispatch_preserves_bytes
@pytest.mark.parametrize('operation, flag, symbol', [('add', '--index', 'XLK'), ('move', '--to-index', 'SPY')])
def test_invalid_index_dispatch_preserves_bytes(dispatch_context,
                                                operation: str,
                                                flag: str,
                                                symbol: str) -> None:
    '''
    Keep -2 a catalogued feature rejection rather than a parser failure or write.

    :param dispatch_context: The real app, parser and storage path.
    :type dispatch_context: tuple
    :param operation: The watchlist command.
    :type operation: str
    :param flag: The public index flag.
    :type flag: str
    :param symbol: The ticker involved in the rejected change.
    :type symbol: str
    '''

    app, parse, path = dispatch_context
    before = path.read_bytes()
    feature_id, headers, data = parse(argv=['watchlists', operation, 'etfs', symbol, flag, '-2'])

    with pytest.raises(TiferetAPIError) as raised:
        app.run(feature_id, headers=headers, data=data)

    assert raised.value.error_code == 'WATCHLIST_INDEX_OUT_OF_RANGE'
    assert path.read_bytes() == before
