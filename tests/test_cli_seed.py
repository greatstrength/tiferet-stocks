"""Stocks CLI bootstrap cache, catalog handler and no-config tests."""

# *** imports

# ** core
import json
from pathlib import Path
import subprocess
from unittest import mock

# ** infra
import pytest
import yaml
from tiferet import assets as core_assets
from tiferet.blueprints import core
from tiferet.domain import CliCommand
from tiferet.interfaces.core import ServiceError
from tiferet.utils.file import FILE_NOT_FOUND_ID

# ** app
from tiferet_stocks import assets as a
from tiferet_stocks.blueprints.cli import (
    build_cache,
    get_app_session,
    get_parent_args_handler,
    get_stocks_cli_commands,
    list_commands_handler,
    main,
)
from tests.repos.yahoo_recorded import recorded_yahoo

# *** constants

# ** constant: reference_config
REFERENCE_CONFIG = yaml.safe_load((Path(__file__).resolve().parents[1] / 'config.yml').read_text())

# *** functions

# ** function: configured
def configured(records: list = None, error: Exception = None):
    '''
    Build a get_dependency stand-in whose app-flagged CLI events return records or raise an error.

    :param records: The records the configured CLI service lists.
    :type records: list
    :param error: The error the configured CLI service raises.
    :type error: Exception
    :return: The get_dependency stand-in and the list of requested (event_id, flag) pairs.
    :rtype: tuple
    '''

    requested = []
    def get_dependency(event_id, flag=None):
        requested.append((event_id, flag))
        event = mock.Mock()
        event.execute.side_effect = error
        event.execute.return_value = records
        return event
    return get_dependency, requested

# *** fixtures

# ** fixture: no_config
@pytest.fixture
def no_config(tmp_path, monkeypatch):
    '''
    Run from an empty directory with no config.yml.

    :param tmp_path: The isolated temporary directory.
    :type tmp_path: Path
    :param monkeypatch: The scoped working-directory adapter.
    :type monkeypatch: pytest.MonkeyPatch
    :return: The empty working directory.
    :rtype: Path
    '''

    monkeypatch.chdir(tmp_path)
    return tmp_path

# *** tests

# ** test: cache_seeds_stocks_commands
def test_cache_seeds_stocks_commands_under_stocks_prefix() -> None:
    '''
    Seed the thirteen stocks commands under the stocks prefix, leaving the core CLI prefix to core.
    '''

    cache = build_cache()
    commands = get_stocks_cli_commands(cache)

    assert len(commands) == 13
    assert all(isinstance(command, CliCommand) for command in commands)
    assert {command.id for command in commands} == set(a.feature.STOCKS_DEFAULT_FEATURES)
    assert not any(command.id in a.feature.STOCKS_DEFAULT_FEATURES for command in cache.get_by_prefix('cli', 'commands').values())

# ** test: cache_seeds_features_sessions_services_errors
def test_cache_seeds_features_sessions_services_errors() -> None:
    '''
    Seed every stocks feature, both sessions, every service and the stocks error catalog.
    '''

    cache = build_cache()

    assert set(a.feature.STOCKS_DEFAULT_FEATURES) <= set(cache.get_by_prefix('app', 'features'))
    assert set(a.app.STOCKS_DEFAULT_SERVICES) <= set(cache.get_by_prefix('app', 'services'))
    assert set(a.app.STOCKS_DEFAULT_APP_SESSIONS) <= set(cache.get_by_prefix('app', 'sessions'))
    assert set(a.error.DEFAULT_ERRORS) <= set(cache.get_by_prefix('app', 'errors'))
    assert set(core_assets.app.CORE_DEFAULT_CONSTANTS) <= set(cache.get_by_prefix(*core_assets.app.APP_CONSTANT_CACHE_PREFIX))

# ** test: assets_match_reference_config
def test_assets_match_reference_config() -> None:
    '''
    Keep the reference config.yml (programmatic App use) equal to the packaged assets it mirrors.
    '''

    assert 'cli' not in REFERENCE_CONFIG

    # Services, in the same dependency order.
    assert list(REFERENCE_CONFIG['services']) == list(a.app.STOCKS_DEFAULT_SERVICES)
    for service_id, service in REFERENCE_CONFIG['services'].items():
        asset = a.app.STOCKS_DEFAULT_SERVICES[service_id]
        assert (service['module_path'], service['class_name']) == (asset['module_path'], asset['class_name'])
        assert service.get('params', {}) == asset.get('parameters', {})

    # Features, by id.
    configured_features = {f'{group}.{key}': feature for group, features in REFERENCE_CONFIG['features'].items() for key, feature in features.items()}
    assert set(configured_features) == set(a.feature.STOCKS_DEFAULT_FEATURES)
    for feature_id, feature in configured_features.items():
        asset = a.feature.STOCKS_DEFAULT_FEATURES[feature_id]
        assert (feature['name'], feature['description'], feature['steps']) == (asset['name'], asset['description'], asset['steps'])

    # Sessions and errors.
    for session_id, session in REFERENCE_CONFIG['sessions'].items():
        asset = a.app.STOCKS_DEFAULT_APP_SESSIONS[session_id]
        assert (session['name'], session['description']) == (asset['name'], asset['description'])
    assert set(REFERENCE_CONFIG['errors']) == set(a.error.DEFAULT_ERRORS)
    symbols = yaml.safe_load((Path(__file__).resolve().parents[1] / 'data' / 'symbols.yml').read_text())
    assert symbols['aliases'] == [{'provider': a.YAHOO_CHART_PROVIDER_ID, 'provider_ticker': ticker, **alias} for ticker, alias in a.YAHOO_DEFAULT_SYMBOL_ALIASES.items()]
    for error_id, error in REFERENCE_CONFIG['errors'].items():
        assert error['message'] == a.error.DEFAULT_ERRORS[error_id]['message']

# ** test: list_commands_cache_only
def test_list_commands_without_config_is_the_cached_set() -> None:
    '''
    A missing app config file means nothing is configured; the cached commands are the full set.
    '''

    cache = build_cache()
    get_dependency, requested = configured(error=ServiceError(FILE_NOT_FOUND_ID))

    commands = list_commands_handler(cache, get_dependency)()

    assert [command.id for command in commands] == [command.id for command in get_stocks_cli_commands(cache)]
    assert requested == [(core_assets.app.LIST_COMMANDS_EVT_ID, 'app')]
    assert get_parent_args_handler(get_dependency)() == []

# ** test: list_commands_cache_plus_config
def test_list_commands_appends_configured_commands() -> None:
    '''
    Configured commands with new ids follow the cached ones.
    '''

    cache = build_cache()
    extra = mock.Mock(spec=CliCommand, id='extra.run', group_key='extra', key='run')
    get_dependency, _ = configured(records=[extra])

    commands = list_commands_handler(cache, get_dependency)()

    assert len(commands) == 14
    assert commands[-1] is extra
    assert commands[:13] == get_stocks_cli_commands(cache)

# ** test: list_commands_later_definition_wins
def test_list_commands_later_definition_wins() -> None:
    '''
    The later definition of a command id wins, across the cache and within the config, keeping the first position.
    '''

    cache = build_cache()
    cached = get_stocks_cli_commands(cache)
    override = mock.Mock(spec=CliCommand, id='exchanges.list', group_key='exchanges', key='list')
    first = mock.Mock(spec=CliCommand, id='extra.run', group_key='extra', key='run')
    last = mock.Mock(spec=CliCommand, id='extra.again', group_key='extra', key='run')
    get_dependency, _ = configured(records=[first, override, last])

    commands = list_commands_handler(cache, get_dependency)()

    assert [command.id for command in commands] == [command.id for command in cached] + ['extra.again']
    assert commands[[command.id for command in cached].index('exchanges.list')] is override
    assert commands[-1] is last

# ** test: configured_command_overrides_stocks_command
def test_configured_command_overrides_stocks_command(no_config, capsys) -> None:
    '''
    A config.yml command with a stocks command id replaces it before argparse, so no Python version sees a conflicting subparser.
    '''

    (no_config / 'config.yml').write_text(yaml.safe_dump({'cli': {'cmds': {'exchanges': {'list': {
        'group_key': 'exchanges',
        'key': 'list',
        'name': 'Exchanges List',
        'description': 'List the exchanges, as configured.',
    }}}}}))

    with pytest.raises(SystemExit) as exited:
        main(argv=['exchanges', '--help'])
    assert exited.value.code == 0
    assert 'List the exchanges, as configured.' in capsys.readouterr().out

    main(argv=['exchanges', 'list'])
    assert 'NYSE_ARCA' in capsys.readouterr().out

# ** test: configured_repeated_command
def test_configured_repeated_command_resolves_last_wins(no_config, capsys) -> None:
    '''
    Two config.yml entries under different YAML keys that declare the same group key and key resolve to the later one before argparse.
    '''

    def command(description: str) -> dict:
        return {'group_key': 'exchanges', 'key': 'list', 'name': 'Exchanges List', 'description': description}
    (no_config / 'config.yml').write_text(yaml.safe_dump({'cli': {'cmds': {
        'exchanges': {'list': command('The first configured definition.')},
        'more': {'listing': command('The later configured definition.')},
    }}}, sort_keys=False))

    with pytest.raises(SystemExit) as exited:
        main(argv=['exchanges', '--help'])
    assert exited.value.code == 0
    out = capsys.readouterr().out
    assert 'The later configured definition.' in out
    assert 'The first configured definition.' not in out

    main(argv=['exchanges', 'list'])
    assert 'NYSE_ARCA' in capsys.readouterr().out

# ** test: session_cli_service_reads_separate_cli_config
def test_session_cli_service_reads_separate_cli_config(no_config, capsys) -> None:
    '''
    A stocks_cli session cli_service pointed at a separate CLI file reads its commands from there, over the cached stocks commands.
    '''

    (no_config / 'commands.yml').write_text(yaml.safe_dump({'cli': {'cmds': {'exchanges': {'list': {
        'group_key': 'exchanges',
        'key': 'list',
        'name': 'Exchanges List',
        'description': 'List the exchanges, from the separate CLI file.',
    }}}}}))
    (no_config / 'config.yml').write_text(yaml.safe_dump({'sessions': {'stocks_cli': {'name': 'Mine', 'services': {'cli_service': {
        'module_path': 'tiferet.repos.cli',
        'class_name': 'CliConfigRepository',
        'params': {'cli_config': str(no_config / 'commands.yml')},
    }}}}}))

    with pytest.raises(SystemExit) as exited:
        main(argv=['exchanges', '--help'])
    assert exited.value.code == 0
    assert 'List the exchanges, from the separate CLI file.' in capsys.readouterr().out

    main(argv=['exchanges', 'list'])
    assert 'NYSE_ARCA' in capsys.readouterr().out

# ** test: list_commands_other_faults
def test_list_commands_propagates_other_faults() -> None:
    '''
    Only a missing file reads as nothing configured; other faults reach the caller.
    '''

    cache = build_cache()
    get_dependency, _ = configured(error=ServiceError('CONFIG_PARSE_FAILED'))

    with pytest.raises(ServiceError):
        list_commands_handler(cache, get_dependency)()

# ** test: app_session_fallback
def test_app_session_prefers_config_then_cache(tmp_path) -> None:
    '''
    Use the config session and its service attributes when declared, else the cached default.
    '''

    cache = build_cache()
    missing = str(tmp_path / 'missing.yml')

    # No file: the cached session, unless the file was explicitly required.
    assert get_app_session(cache, missing).services == []
    with pytest.raises(ServiceError) as raised:
        get_app_session(cache, missing, required=True)
    assert raised.value.error_code == FILE_NOT_FOUND_ID

    # A file without the stocks session: the cached session.
    other = tmp_path / 'other.yml'
    other.write_text(yaml.safe_dump({'sessions': {'elsewhere': {'name': 'Elsewhere'}}}))
    assert get_app_session(cache, str(other)).name == 'Stocks CLI'

    # A declared session wins over the cached one and carries its service attributes.
    declared = tmp_path / 'declared.yml'
    declared.write_text(yaml.safe_dump({'sessions': {'stocks_cli': {'name': 'Mine', 'services': {'price_service': {'module_path': 'tiferet_stocks.repos.static', 'class_name': 'StaticPriceRepository'}}}}}))
    session = get_app_session(cache, str(declared))
    assert session.name == 'Mine'
    assert [service.service_id for service in session.services] == ['price_service']

# ** test: config_session_service_override
def test_config_session_service_overrides_cached_service(tmp_path, monkeypatch, capsys) -> None:
    '''
    A config.yml stocks_cli session service replaces the cached service of the same id; the cached features and other services still run.
    '''

    monkeypatch.chdir(tmp_path)
    fixture = Path(__file__).resolve().parent / 'repos' / 'fixtures' / 'static_prices.yml'
    (tmp_path / 'config.yml').write_text(yaml.safe_dump({'sessions': {'stocks_cli': {'name': 'Mine', 'services': {
        'price_service': {'module_path': 'tiferet_stocks.repos.static', 'class_name': 'StaticPriceRepository', 'params': {'fixture_path': str(fixture)}},
    }}}}))

    with mock.patch('urllib.request.urlopen', side_effect=AssertionError('network')):
        main(argv=['quotes', 'get', 'SPY'])
    out = capsys.readouterr().out
    assert 'SPY' in out and 'static' in out

    main(argv=['watchlists', 'list'])
    assert not (tmp_path / 'data').exists()

# ** test: top_level_service_overrides_cached_service
def test_top_level_service_overrides_cached_service(tmp_path, monkeypatch, capsys) -> None:
    '''
    A config.yml top-level service replaces the cached service of the same id when no session declares it.
    '''

    monkeypatch.chdir(tmp_path)
    fixture = Path(__file__).resolve().parent / 'repos' / 'fixtures' / 'static_prices.yml'
    (tmp_path / 'config.yml').write_text(yaml.safe_dump({'services': {
        'price_service': {'module_path': 'tiferet_stocks.repos.static', 'class_name': 'StaticPriceRepository', 'params': {'fixture_path': str(fixture)}},
    }}))

    with mock.patch('urllib.request.urlopen', side_effect=AssertionError('network')):
        main(argv=['quotes', 'get', 'SPY'])
    out = capsys.readouterr().out
    assert 'SPY' in out and 'static' in out

# ** test: top_level_symbol_alias_service
def test_top_level_symbol_alias_service_reads_another_file(no_config, capsys) -> None:
    '''
    A config.yml top-level symbol_alias_service registration, outside any session, pointing symbol_config at another file makes the CLI use that file's aliases.
    '''

    (no_config / 'aliases.yml').write_text(yaml.safe_dump({'aliases': [{'provider': a.YAHOO_CHART_PROVIDER_ID, 'provider_ticker': 'BRKB.X', 'canonical_id': 'BRK.B'}]}))
    (no_config / 'config.yml').write_text(yaml.safe_dump({'services': {a.SYMBOL_ALIAS_SERVICE_ID: {
        'module_path': 'tiferet_stocks.repos.symbol',
        'class_name': 'SymbolAliasRepository',
        'params': {'symbol_config': str(no_config / 'aliases.yml')},
    }}}))

    requested = []
    with mock.patch('urllib.request.urlopen', side_effect=recorded_yahoo(requested)):
        with pytest.raises(SystemExit):
            main(argv=['quotes', 'get', 'BRK.B'])

    # The other file sends BRK.B as BRKB.X, never the default BRK-B; the default data/symbols.yml is never created.
    assert requested == ['cookie', 'crumb', 'quote:BRKB.X']
    assert 'QUOTES_UNAVAILABLE' in capsys.readouterr().err
    assert not (no_config / 'data').exists()

# ** test: session_service_beats_top_level_service
def test_session_service_beats_top_level_service(tmp_path, monkeypatch, capsys) -> None:
    '''
    Services layer cache, then top-level, then session: a session service wins over a top-level service with the same id.
    '''

    monkeypatch.chdir(tmp_path)
    (tmp_path / 'top.yml').write_text(yaml.safe_dump({'prices': {'SPY': {'price': 111.0}}}))
    (tmp_path / 'session.yml').write_text(yaml.safe_dump({'prices': {'SPY': {'price': 222.0}}}))
    def static(path: str) -> dict:
        return {'module_path': 'tiferet_stocks.repos.static', 'class_name': 'StaticPriceRepository', 'params': {'fixture_path': path}}
    (tmp_path / 'config.yml').write_text(yaml.safe_dump({
        'services': {'price_service': static(str(tmp_path / 'top.yml'))},
        'sessions': {'stocks_cli': {'name': 'Mine', 'services': {'price_service': static(str(tmp_path / 'session.yml'))}}},
    }))

    with mock.patch('urllib.request.urlopen', side_effect=AssertionError('network')):
        main(argv=['quotes', 'get', 'SPY'])
    out = capsys.readouterr().out
    assert '222' in out
    assert '111' not in out

# ** test: symbols_stay_out_of_app_sessions
def test_symbols_stay_out_of_app_sessions(tmp_path) -> None:
    '''
    Symbols and aliases are domain concerns: no packaged, reference or resolved app session carries a symbol or alias key, constant or service.
    '''

    def assert_no_symbols(session: dict) -> None:
        text = json.dumps(session).lower()
        assert 'symbol' not in text and 'alias' not in text

    # The packaged sessions and the reference config sessions.
    for session in a.app.STOCKS_DEFAULT_APP_SESSIONS.values():
        assert_no_symbols(session)
    for session in REFERENCE_CONFIG['sessions'].values():
        assert_no_symbols(session)

    # The session the CLI resolves from the cache, and from the reference config.
    cache = build_cache()
    for config_path in (str(tmp_path / 'missing.yml'), str(Path(__file__).resolve().parents[1] / 'config.yml')):
        assert_no_symbols(get_app_session(cache, config_path).model_dump(mode='json'))

    # The alias service is registered with the services, outside every session.
    assert a.SYMBOL_ALIAS_SERVICE_ID in a.app.STOCKS_DEFAULT_SERVICES
    assert a.SYMBOL_ALIAS_SERVICE_ID in REFERENCE_CONFIG['services']

# ** test: yahoo_default_symbol_aliases
def test_yahoo_default_symbol_aliases_carry_no_provider() -> None:
    '''
    Build the Yahoo default aliases through the asset helper, keyed by provider ticker; the provider is designated by the constant, not the data.
    '''

    assert a.create_default_symbol_alias_data('BRK.B') == {'canonical_id': 'BRK.B'}
    assert a.YAHOO_DEFAULT_SYMBOL_ALIASES == {'BRK-B': {'canonical_id': 'BRK.B'}}

# ** test: alias_service_configured_only
def test_alias_service_returns_configured_aliases_only(no_config) -> None:
    '''
    The container's alias service carries no Yahoo defaults; with no symbols file it returns nothing, and the events add the defaults.
    '''

    cache = build_cache()
    container = core.build_app_service_container(cache, app_instance=core.get_app_session(a.STOCKS_CLI_SESSION_ID, cache=cache))
    service = container.get_dependency(a.SYMBOL_ALIAS_SERVICE_ID)

    assert service.get_aliases(a.YAHOO_CHART_PROVIDER_ID) == []
    assert not Path(service.config_file).exists()

# ** test: configured_alias_wins
def test_configured_symbols_file_alias_beats_yahoo_default(no_config, capsys) -> None:
    '''
    A data/symbols.yml alias for a provider ticker replaces the cached Yahoo default for that ticker.
    '''

    (no_config / 'data').mkdir()
    (no_config / 'data' / 'symbols.yml').write_text(yaml.safe_dump({'aliases': [{'provider': a.YAHOO_CHART_PROVIDER_ID, 'provider_ticker': 'BRK-B', 'canonical_id': 'BRKB.X'}]}))

    requested = []
    with mock.patch('urllib.request.urlopen', side_effect=recorded_yahoo(requested)):
        main(argv=['quotes', 'get', 'BRKB.X', 'BRK.B'])

    # BRKB.X now maps to BRK-B; BRK.B has no alias left and is sent as is.
    assert requested == ['cookie', 'crumb', 'quote:BRK-B,BRK.B']
    rows = {line.split()[0]: line.split()[1] for line in capsys.readouterr().out.splitlines() if line.split() and line.split()[0] in ('BRKB.X', 'BRK.B')}
    assert rows == {'BRKB.X': 'ok', 'BRK.B': 'failed'}

# ** test: later_row_overwrites
def test_symbols_file_later_row_overwrites(no_config) -> None:
    '''
    A data/symbols.yml with two yahoo_chart rows for BRK.B (X1, then X2) overwrites: BRK.B is requested as X2.
    '''

    (no_config / 'data').mkdir()
    (no_config / 'data' / 'symbols.yml').write_text(yaml.safe_dump({'aliases': [
        {'provider': a.YAHOO_CHART_PROVIDER_ID, 'provider_ticker': 'X1', 'canonical_id': 'BRK.B'},
        {'provider': a.YAHOO_CHART_PROVIDER_ID, 'provider_ticker': 'X2', 'canonical_id': 'BRK.B'},
    ]}))

    requested = []
    with mock.patch('urllib.request.urlopen', side_effect=recorded_yahoo(requested)):
        with pytest.raises(SystemExit):
            main(argv=['quotes', 'get', 'BRK.B'])
    assert requested == ['cookie', 'crumb', 'quote:X2']

# ** test: shared_ticker_rejected
def test_symbols_file_shared_ticker_fails(no_config, capsys) -> None:
    '''
    A data/symbols.yml mapping BRK-B to BRK.B, then BRK-B to BRKX, exits 1 with the catalogued ALIAS_TICKER_EXISTS message naming the ticker, the provider and both symbols, before any request and with no traceback.
    '''

    (no_config / 'data').mkdir()
    (no_config / 'data' / 'symbols.yml').write_text(yaml.safe_dump({'aliases': [
        {'provider': a.YAHOO_CHART_PROVIDER_ID, 'provider_ticker': 'BRK-B', 'canonical_id': 'BRK.B'},
        {'provider': a.YAHOO_CHART_PROVIDER_ID, 'provider_ticker': 'BRK-B', 'canonical_id': 'BRKX'},
    ]}))

    with mock.patch('urllib.request.urlopen', side_effect=AssertionError('network')):
        with pytest.raises(SystemExit) as exited:
            main(argv=['quotes', 'get', 'BRK.B', 'BRKX'])
    assert exited.value.code == 1
    err = capsys.readouterr().err
    assert 'ALIAS_TICKER_EXISTS' in err
    assert 'Ticker BRK-B is a yahoo_chart alias for more than one symbol: BRK.B and BRKX.' in err
    assert 'Traceback' not in err

# ** test: configured_ticker_replaces_default
def test_configured_symbols_file_ticker_replaces_yahoo_default(no_config, capsys) -> None:
    '''
    A data/symbols.yml alias sending BRK.B under another Yahoo ticker replaces the Yahoo default, so BRK-B is never requested.
    '''

    (no_config / 'data').mkdir()
    (no_config / 'data' / 'symbols.yml').write_text(yaml.safe_dump({'aliases': [{'provider': a.YAHOO_CHART_PROVIDER_ID, 'provider_ticker': 'BRKB.X', 'canonical_id': 'BRK.B'}]}))

    requested = []
    with mock.patch('urllib.request.urlopen', side_effect=recorded_yahoo(requested)):
        with pytest.raises(SystemExit):
            main(argv=['quotes', 'get', 'BRK.B'])

    assert requested == ['cookie', 'crumb', 'quote:BRKB.X']

# ** test: no_config_help
def test_no_config_help(no_config, capsys) -> None:
    '''
    Print the full stocks help with no config.yml.
    '''

    with pytest.raises(SystemExit) as exited:
        main(argv=['--help'])

    assert exited.value.code == 0
    out = capsys.readouterr().out
    for group in ('quotes', 'symbols', 'exchanges', 'watchlists'):
        assert group in out
    assert list(no_config.iterdir()) == []

# ** test: no_config_commands
def test_no_config_exchanges_and_watchlist_create(no_config, capsys) -> None:
    '''
    Run real commands with no config.yml; watchlists add fails on a missing watchlist unless --create.
    '''

    main(argv=['exchanges', 'list'])
    assert 'NYSE_ARCA' in capsys.readouterr().out

    with pytest.raises(SystemExit) as exited:
        main(argv=['watchlists', 'add', 'tech', 'AAPL'])
    assert exited.value.code == 1
    assert 'WATCHLIST_NOT_FOUND' in capsys.readouterr().err
    assert not (no_config / 'data').exists()

    main(argv=['watchlists', 'add', 'tech', 'AAPL', '--create'])
    main(argv=['watchlists', 'add', 'tech', 'MSFT', '--index', '0'])
    capsys.readouterr()
    stored = yaml.safe_load((no_config / 'data' / 'watchlists.yml').read_text())
    assert 'tech' in json.dumps(stored)
    main(argv=['watchlists', 'get', 'tech'])
    out = capsys.readouterr().out
    assert out.index('MSFT') < out.index('AAPL')

# ** test: no_config_quotes
def test_no_config_quotes_use_cached_yahoo_provider(no_config, capsys) -> None:
    '''
    Quote through the cached Yahoo provider with no config.yml, from recorded responses.
    '''

    requested = []
    with mock.patch('urllib.request.urlopen', side_effect=recorded_yahoo(requested)):
        main(argv=['quotes', 'get', 'AAPL', 'SPY', 'BRK.B'])

    # The cached default alias sends BRK-B to Yahoo and answers under BRK.B, with no symbols file.
    assert requested == ['cookie', 'crumb', 'quote:AAPL,SPY,BRK-B']
    rows = {line.split()[0]: line.split()[1] for line in capsys.readouterr().out.splitlines() if line.split() and line.split()[0] in ('AAPL', 'SPY', 'BRK.B')}
    assert rows == {'AAPL': 'ok', 'SPY': 'ok', 'BRK.B': 'ok'}
    assert not (no_config / 'data').exists()

# ** test: no_config_symbols_canonical
def test_no_config_symbols_report_canonical_ids_only(no_config, capsys) -> None:
    '''
    With no config, symbols get BRK-B answers as BRK.B, and symbols resolve BRK.B BRK-B reports BRK.B alone, with no failure rows.
    '''

    requested = []
    with mock.patch('urllib.request.urlopen', side_effect=recorded_yahoo(requested)):
        main(argv=['symbols', 'get', 'BRK-B'])
        got = capsys.readouterr().out
        main(argv=['symbols', 'resolve', 'BRK.B', 'BRK-B'])
        resolved = capsys.readouterr().out

    for out in (got, resolved):
        rows = [line.split()[:2] for line in out.splitlines() if line.split() and line.split()[0] in ('BRK.B', 'BRK-B')]
        assert rows == [['BRK.B', 'ok']]
    assert 'symbol_mismatch' not in got + resolved

# ** test: no_config_explicit_missing
def test_explicit_missing_config_fails(no_config) -> None:
    '''
    An explicit --config that does not exist is still a fault.
    '''

    with pytest.raises(ServiceError) as raised:
        main(argv=['--config', 'nope.yml', 'exchanges', 'list'])
    assert raised.value.error_code == FILE_NOT_FOUND_ID

# ** test: installed_no_config
def test_installed_console_with_no_config(installed_cli, tmp_path) -> None:
    '''
    Run the installed wheel's console script from a directory with no config.yml.

    :param installed_cli: The offline noneditable installed console environment.
    :type installed_cli: dict
    :param tmp_path: The isolated temporary directory.
    :type tmp_path: Path
    '''

    cwd = tmp_path / 'fresh'
    cwd.mkdir()
    def run(*argv):
        return subprocess.run([str(installed_cli['script']), *argv], cwd=cwd, env=installed_cli['env'], capture_output=True, text=True, timeout=30)

    helped = run('--help')
    assert helped.returncode == 0, helped.stderr
    assert 'watchlists' in helped.stdout
    listed = run('exchanges', 'list')
    assert listed.returncode == 0, listed.stderr
    assert 'NASDAQ' in listed.stdout
    # A shared provider ticker in the symbols file is a clean catalogued exit 1, not a traceback.
    (cwd / 'data').mkdir()
    (cwd / 'data' / 'symbols.yml').write_text(yaml.safe_dump({'aliases': [
        {'provider': a.YAHOO_CHART_PROVIDER_ID, 'provider_ticker': 'BRK-B', 'canonical_id': 'BRK.B'},
        {'provider': a.YAHOO_CHART_PROVIDER_ID, 'provider_ticker': 'BRK-B', 'canonical_id': 'BRKX'},
    ]}))
    shared = run('quotes', 'get', 'BRK.B', 'BRKX')
    assert shared.returncode == 1
    assert 'Ticker BRK-B is a yahoo_chart alias for more than one symbol: BRK.B and BRKX.' in shared.stderr
    assert 'Traceback' not in shared.stderr + shared.stdout
    (cwd / 'data' / 'symbols.yml').unlink()
    (cwd / 'data').rmdir()
    rejected = run('watchlists', 'add', 'tech', 'AAPL')
    assert rejected.returncode == 1
    assert 'WATCHLIST_NOT_FOUND' in rejected.stderr
    created = run('watchlists', 'add', 'tech', 'AAPL', '--create')
    assert created.returncode == 0, created.stderr
    assert (cwd / 'data' / 'watchlists.yml').is_file()
    assert not (cwd / 'config.yml').exists()
