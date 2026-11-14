"""Tiferet Stocks Symbol Event Tests"""

# *** imports

# ** core
import inspect
from typing import Dict
from unittest import mock

# ** infra
import pytest
from tiferet import TiferetError, use_tester
from tiferet.events import DomainEvent

# ** app
from tiferet_stocks.domain import (
    EXCHANGES,
    QuoteFailure,
    Symbol,
    SymbolAlias,
    SymbolLookup,
    SymbolWarning,
)
from tiferet_stocks.events import (
    GetSymbol,
    ListExchanges,
    ResolveSymbols,
    SymbolAliasEvent,
    SymbolLookupEvent,
)
from tiferet_stocks.interfaces import SymbolAliasService, SymbolLookupService

# *** fixtures

# ** fixture: symbol_lookup_service
@pytest.fixture
def symbol_lookup_service() -> mock.Mock:
    '''
    A mock symbol lookup service returning AAPL, SPY and a provider failure.
    '''

    service = mock.Mock(spec=SymbolLookupService)
    service.lookup.return_value = SymbolLookup(
        symbols={
            'AAPL': Symbol(id='AAPL', exchange='NASDAQ', asset_type='equity'),
            'SPY': Symbol(id='SPY', exchange='NYSE_ARCA', asset_type='etf'),
        },
        warnings=[SymbolWarning(symbol_id='OTHER', reason='unmapped_exchange', detail='PNK')],
        failures=[QuoteFailure(symbol_id='ZZZZQ', reason='not_found')],
    )
    return service

# *** functions

# ** function: alias_service
def alias_service(aliases: Dict[str, SymbolAlias] = None) -> mock.Mock:
    '''
    A mock symbol alias service returning the given yahoo_chart aliases, or an empty map.

    :param aliases: The aliases keyed by provider ticker.
    :type aliases: Dict[str, SymbolAlias]
    :return: The mock symbol alias service.
    :rtype: mock.Mock
    '''

    # Return data only, as the configured repository does.
    service = mock.Mock(spec=SymbolAliasService)
    service.get_aliases.return_value = aliases or {}
    return service

# ** function: brk_aliases
def brk_aliases() -> Dict[str, SymbolAlias]:
    '''
    The yahoo_chart alias map for BRK.B, keyed by provider ticker.

    :return: The alias map.
    :rtype: Dict[str, SymbolAlias]
    '''

    # Build and return the map.
    return {'BRK-B': SymbolAlias(provider='yahoo_chart', provider_ticker='BRK-B', canonical_id='BRK.B')}

# *** tests

# ** test: get_symbol
def test_get_symbol(symbol_lookup_service: mock.Mock) -> None:
    '''
    Test that GetSymbol returns the symbol when the expected exchange matches.

    :param symbol_lookup_service: The mock symbol lookup service.
    :type symbol_lookup_service: mock.Mock
    '''

    lookup = DomainEvent.handle(GetSymbol, dependencies={'symbol_lookup_service': symbol_lookup_service, 'symbol_alias_service': alias_service()}, id='AAPL', exchange='NASDAQ')

    assert lookup.symbols['AAPL'].exchange == 'NASDAQ'
    assert lookup.failures == []
    assert lookup.warnings == []
    symbol_lookup_service.lookup.assert_called_once_with(['AAPL'])

# ** test: get_symbol_exchange_mismatch
def test_get_symbol_exchange_mismatch(symbol_lookup_service: mock.Mock) -> None:
    '''
    Test that an expected exchange mismatch is a symbol_mismatch failure and the symbol is excluded.

    :param symbol_lookup_service: The mock symbol lookup service.
    :type symbol_lookup_service: mock.Mock
    '''

    lookup = DomainEvent.handle(GetSymbol, dependencies={'symbol_lookup_service': symbol_lookup_service, 'symbol_alias_service': alias_service()}, id='AAPL', exchange='NYSE')

    assert lookup.symbols == {}
    assert lookup.failures[0].reason == 'symbol_mismatch'
    assert lookup.failures[0].detail == 'expected exchange NYSE, actual exchange NASDAQ'

# ** test: get_symbol_ticker_mismatch
def test_get_symbol_ticker_mismatch(symbol_lookup_service: mock.Mock) -> None:
    '''
    Test that a result for a different ticker is a symbol_mismatch failure.

    :param symbol_lookup_service: The mock symbol lookup service.
    :type symbol_lookup_service: mock.Mock
    '''

    symbol_lookup_service.lookup.return_value = SymbolLookup(symbols={'BF.B': Symbol(id='BF-B', exchange='NYSE')})

    lookup = DomainEvent.handle(GetSymbol, dependencies={'symbol_lookup_service': symbol_lookup_service, 'symbol_alias_service': alias_service()}, id='BF.B')

    assert lookup.symbols == {}
    assert lookup.failures[0].reason == 'symbol_mismatch'
    assert lookup.failures[0].detail == 'expected ticker BF.B, actual ticker BF-B'

# ** test: get_symbol_ticker_case_insensitive
def test_get_symbol_ticker_case_insensitive(symbol_lookup_service: mock.Mock) -> None:
    '''
    Test that the ticker check ignores case.

    :param symbol_lookup_service: The mock symbol lookup service.
    :type symbol_lookup_service: mock.Mock
    '''

    symbol_lookup_service.lookup.return_value = SymbolLookup(symbols={'aapl': Symbol(id='AAPL', exchange='NASDAQ')})

    lookup = DomainEvent.handle(GetSymbol, dependencies={'symbol_lookup_service': symbol_lookup_service, 'symbol_alias_service': alias_service()}, id='aapl')

    assert lookup.symbols['aapl'].id == 'AAPL'
    assert lookup.failures == []

# ** test: get_symbol_requires_id
def test_get_symbol_requires_id(symbol_lookup_service: mock.Mock) -> None:
    '''
    Test that GetSymbol requires an id.

    :param symbol_lookup_service: The mock symbol lookup service.
    :type symbol_lookup_service: mock.Mock
    '''

    with pytest.raises(TiferetError):
        DomainEvent.handle(GetSymbol, dependencies={'symbol_lookup_service': symbol_lookup_service, 'symbol_alias_service': alias_service()}, id=None)

# ** test: resolve_symbols
def test_resolve_symbols(symbol_lookup_service: mock.Mock) -> None:
    '''
    Test that ResolveSymbols keeps matches, passes provider failures through, and reports unresolved ids.

    :param symbol_lookup_service: The mock symbol lookup service.
    :type symbol_lookup_service: mock.Mock
    '''

    lookup = DomainEvent.handle(
        ResolveSymbols,
        dependencies={'symbol_lookup_service': symbol_lookup_service, 'symbol_alias_service': alias_service()},
        ids=['AAPL', 'SPY', 'ZZZZQ', 'MISSING', 'AAPL'],
        exchanges={'SPY': 'NYSE'},
    )

    assert list(lookup.symbols) == ['AAPL']
    assert [(f.symbol_id, f.reason) for f in lookup.failures] == [
        ('ZZZZQ', 'not_found'),
        ('SPY', 'symbol_mismatch'),
        ('MISSING', 'not_found'),
    ]
    assert lookup.warnings == []
    symbol_lookup_service.lookup.assert_called_once_with(['AAPL', 'SPY', 'ZZZZQ', 'MISSING'])

# ** test: resolve_symbols_requires_ids
def test_resolve_symbols_requires_ids(symbol_lookup_service: mock.Mock) -> None:
    '''
    Test that ResolveSymbols requires ids.

    :param symbol_lookup_service: The mock symbol lookup service.
    :type symbol_lookup_service: mock.Mock
    '''

    with pytest.raises(TiferetError):
        DomainEvent.handle(ResolveSymbols, dependencies={'symbol_lookup_service': symbol_lookup_service, 'symbol_alias_service': alias_service()}, ids=None)

# ** test: symbol_events_depend_only_on_lookup
def test_symbol_events_depend_only_on_lookup() -> None:
    '''
    Test that symbol events take only the symbol lookup service: no watchlist service and no file writes.
    '''

    params = list(inspect.signature(SymbolLookupEvent.__init__).parameters)

    assert params == ['self', 'symbol_lookup_service', 'symbol_alias_service']
    assert GetSymbol.__init__ is SymbolLookupEvent.__init__
    assert ResolveSymbols.__init__ is SymbolLookupEvent.__init__

# ** test: resolve_symbols_single_string
def test_resolve_symbols_single_string(symbol_lookup_service: mock.Mock) -> None:
    '''
    Test that a single id passed as a string is looked up as one id, not per character.

    :param symbol_lookup_service: The mock symbol lookup service.
    :type symbol_lookup_service: mock.Mock
    '''

    lookup = DomainEvent.handle(ResolveSymbols, dependencies={'symbol_lookup_service': symbol_lookup_service, 'symbol_alias_service': alias_service()}, ids='AAPL')

    assert list(lookup.symbols) == ['AAPL']
    symbol_lookup_service.lookup.assert_called_once_with(['AAPL'])

# ** test: resolve_symbols_writes_no_file
def test_resolve_symbols_writes_no_file(symbol_lookup_service: mock.Mock) -> None:
    '''
    Test that resolving symbols opens no file.

    :param symbol_lookup_service: The mock symbol lookup service.
    :type symbol_lookup_service: mock.Mock
    '''

    with mock.patch('builtins.open') as patched_open:
        DomainEvent.handle(ResolveSymbols, dependencies={'symbol_lookup_service': symbol_lookup_service, 'symbol_alias_service': alias_service()}, ids=['AAPL', 'SPY'])

    patched_open.assert_not_called()

# ** test: list_exchanges
def test_list_exchanges() -> None:
    '''
    Test that ListExchanges returns a copy of EXCHANGES with no dependency.
    '''

    exchanges = DomainEvent.handle(ListExchanges)

    assert exchanges == EXCHANGES
    assert exchanges is not EXCHANGES

# ** test: get_symbol_brk_b_alias
def test_get_symbol_brk_b_alias(symbol_lookup_service: mock.Mock) -> None:
    '''
    Test that a canonical BRK.B request is looked up as BRK-B and the alias is applied before the mismatch check.

    :param symbol_lookup_service: The mock symbol lookup service.
    :type symbol_lookup_service: mock.Mock
    '''

    symbol_lookup_service.lookup.return_value = SymbolLookup(
        symbols={'BRK-B': Symbol(id='BRK-B', exchange='NYSE', asset_type='equity')},
        warnings=[SymbolWarning(symbol_id='BRK-B', reason='unmapped_asset_type', detail='TEST')],
    )
    aliases = alias_service(brk_aliases())

    lookup = DomainEvent.handle(
        GetSymbol,
        dependencies={'symbol_lookup_service': symbol_lookup_service, 'symbol_alias_service': aliases},
        id='BRK.B',
        exchange='NYSE',
    )

    aliases.get_aliases.assert_called_once_with('yahoo_chart')
    symbol_lookup_service.lookup.assert_called_once_with(['BRK-B'])
    assert list(lookup.symbols) == ['BRK.B']
    assert lookup.symbols['BRK.B'].id == 'BRK.B'
    assert lookup.symbols['BRK.B'].aliases == list(brk_aliases().values())
    assert lookup.warnings[0].symbol_id == 'BRK.B'
    assert lookup.failures == []

# ** test: resolve_symbols_brk_b_alias
def test_resolve_symbols_brk_b_alias(symbol_lookup_service: mock.Mock) -> None:
    '''
    Test that ResolveSymbols applies the alias for BRK.B, leaves an unaliased control unchanged, and reports a miss as data.

    :param symbol_lookup_service: The mock symbol lookup service.
    :type symbol_lookup_service: mock.Mock
    '''

    symbol_lookup_service.lookup.return_value = SymbolLookup(
        symbols={
            'BRK-B': Symbol(id='BRK-B', exchange='NYSE', asset_type='equity'),
            'AAPL': Symbol(id='AAPL', exchange='NASDAQ', asset_type='equity'),
        },
        failures=[QuoteFailure(symbol_id='ZZZZQ', reason='not_found', detail='HTTP 404')],
    )

    lookup = DomainEvent.handle(
        ResolveSymbols,
        dependencies={'symbol_lookup_service': symbol_lookup_service, 'symbol_alias_service': alias_service(brk_aliases())},
        ids=['BRK.B', 'AAPL', 'ZZZZQ'],
    )

    symbol_lookup_service.lookup.assert_called_once_with(['BRK-B', 'AAPL', 'ZZZZQ'])
    assert list(lookup.symbols) == ['BRK.B', 'AAPL']
    assert lookup.symbols['AAPL'].aliases == []
    assert [(f.symbol_id, f.reason) for f in lookup.failures] == [('ZZZZQ', 'not_found')]

# ** test: resolve_symbols_brk_b_failure_rekeyed
def test_resolve_symbols_brk_b_failure_rekeyed(symbol_lookup_service: mock.Mock) -> None:
    '''
    Test that a provider failure for the provider ticker is reported under the canonical id.

    :param symbol_lookup_service: The mock symbol lookup service.
    :type symbol_lookup_service: mock.Mock
    '''

    symbol_lookup_service.lookup.return_value = SymbolLookup(failures=[QuoteFailure(symbol_id='BRK-B', reason='timeout', attempts=2)])

    lookup = DomainEvent.handle(
        ResolveSymbols,
        dependencies={'symbol_lookup_service': symbol_lookup_service, 'symbol_alias_service': alias_service(brk_aliases())},
        ids=['BRK.B'],
    )

    assert lookup.symbols == {}
    assert [(f.symbol_id, f.reason, f.attempts) for f in lookup.failures] == [('BRK.B', 'timeout', 2)]

# ** test: resolve_symbols_alias_for_other_ticker_mismatch
def test_resolve_symbols_alias_for_other_ticker_mismatch(symbol_lookup_service: mock.Mock) -> None:
    '''
    Test that a provider answer for an unexpected ticker is not aliased and stays a symbol_mismatch.

    :param symbol_lookup_service: The mock symbol lookup service.
    :type symbol_lookup_service: mock.Mock
    '''

    symbol_lookup_service.lookup.return_value = SymbolLookup(symbols={'BRK-B': Symbol(id='BRK-A', exchange='NYSE')})

    lookup = DomainEvent.handle(
        ResolveSymbols,
        dependencies={'symbol_lookup_service': symbol_lookup_service, 'symbol_alias_service': alias_service(brk_aliases())},
        ids=['BRK.B'],
    )

    assert lookup.symbols == {}
    assert lookup.failures[0].reason == 'symbol_mismatch'
    assert lookup.failures[0].detail == 'expected ticker BRK.B, actual ticker BRK-A'

# ** test: get_symbol_not_found
@pytest.mark.parametrize('failures', [
    [QuoteFailure(symbol_id='ZZZZQ', reason='not_found', detail='HTTP 404')],
    [],
])
def test_get_symbol_not_found(symbol_lookup_service: mock.Mock, failures: list) -> None:
    '''
    Test that GetSymbol raises SYMBOL_NOT_FOUND when the provider has no such ticker after the alias step.

    :param symbol_lookup_service: The mock symbol lookup service.
    :type symbol_lookup_service: mock.Mock
    :param failures: The provider failures for the lookup.
    :type failures: list
    '''

    symbol_lookup_service.lookup.return_value = SymbolLookup(failures=failures)

    with pytest.raises(TiferetError) as exc_info:
        DomainEvent.handle(
            GetSymbol,
            dependencies={'symbol_lookup_service': symbol_lookup_service, 'symbol_alias_service': alias_service(brk_aliases())},
            id='ZZZZQ',
        )

    assert exc_info.value.error_code == 'SYMBOL_NOT_FOUND'
    assert exc_info.value.kwargs['id'] == 'ZZZZQ'
    assert exc_info.value.kwargs['failure']['reason'] == 'not_found'

# ** test: get_symbol_other_failures_are_data
@pytest.mark.parametrize('reason', ['timeout', 'http_error', 'bad_payload'])
def test_get_symbol_other_failures_are_data(symbol_lookup_service: mock.Mock, reason: str) -> None:
    '''
    Test that GetSymbol still returns a provider failure that is not not_found as data.

    :param symbol_lookup_service: The mock symbol lookup service.
    :type symbol_lookup_service: mock.Mock
    :param reason: The provider failure reason.
    :type reason: str
    '''

    symbol_lookup_service.lookup.return_value = SymbolLookup(failures=[QuoteFailure(symbol_id='AAPL', reason=reason)])

    lookup = DomainEvent.handle(GetSymbol, dependencies={'symbol_lookup_service': symbol_lookup_service, 'symbol_alias_service': alias_service()}, id='AAPL')

    assert lookup.symbols == {}
    assert lookup.failures[0].reason == reason

# ** test: alias_event_yahoo_defaults
def test_alias_event_hydrates_yahoo_defaults_with_nothing_configured() -> None:
    '''
    Test that with no configured aliases the Yahoo defaults from the assets hydrate with the provider and the provider ticker from the group key.
    '''

    service = alias_service()

    aliases = SymbolAliasEvent(service).get_aliases('yahoo_chart')

    service.get_aliases.assert_called_once_with('yahoo_chart')
    assert aliases == brk_aliases()

# ** test: alias_event_other_provider
def test_alias_event_other_provider_gets_no_yahoo_defaults() -> None:
    '''
    Test that another provider gets only its configured aliases, never the Yahoo defaults.
    '''

    assert SymbolAliasEvent(alias_service()).get_aliases('static') == {}

# ** test: alias_event_configured_wins
@pytest.mark.parametrize('provider_ticker, canonical_id', [
    ('BRK-B', 'BRKB.X'),
    ('BRKB.X', 'BRK.B'),
])
def test_alias_event_configured_alias_wins(provider_ticker: str, canonical_id: str) -> None:
    '''
    Test that a configured alias covering a default's provider ticker or canonical id drops that default, and other configured aliases are kept.

    :param provider_ticker: The configured provider ticker.
    :type provider_ticker: str
    :param canonical_id: The configured canonical id.
    :type canonical_id: str
    '''

    configured = {
        provider_ticker: SymbolAlias(provider='yahoo_chart', provider_ticker=provider_ticker, canonical_id=canonical_id),
        'BF-B': SymbolAlias(provider='yahoo_chart', provider_ticker='BF-B', canonical_id='BF.B'),
    }

    assert SymbolAliasEvent(alias_service(configured)).get_aliases('yahoo_chart') == configured

# ** test: resolve_symbols_configured_ticker
def test_resolve_symbols_configured_ticker_replaces_default(symbol_lookup_service: mock.Mock) -> None:
    '''
    Test that a configured alias sending BRK.B under another ticker is the only ticker looked up.

    :param symbol_lookup_service: The mock symbol lookup service.
    :type symbol_lookup_service: mock.Mock
    '''

    configured = {'BRKB.X': SymbolAlias(provider='yahoo_chart', provider_ticker='BRKB.X', canonical_id='BRK.B')}
    symbol_lookup_service.lookup.return_value = SymbolLookup(symbols={'BRKB.X': Symbol(id='BRKB.X', exchange='NYSE')})

    lookup = DomainEvent.handle(ResolveSymbols, dependencies={'symbol_lookup_service': symbol_lookup_service, 'symbol_alias_service': alias_service(configured)}, ids=['BRK.B'])

    symbol_lookup_service.lookup.assert_called_once_with(['BRKB.X'])
    assert lookup.symbols['BRK.B'].id == 'BRK.B'

# ** test: resolve_symbols_raw_ticker_with_configured_ticker
def test_resolve_symbols_raw_default_ticker_passes_through_when_configured_elsewhere(symbol_lookup_service: mock.Mock) -> None:
    '''
    Test that with BRK.B configured as BRKB.X a raw BRK-B request resolves as BRK-B with no symbol_mismatch.

    :param symbol_lookup_service: The mock symbol lookup service.
    :type symbol_lookup_service: mock.Mock
    '''

    configured = {'BRKB.X': SymbolAlias(provider='yahoo_chart', provider_ticker='BRKB.X', canonical_id='BRK.B')}
    symbol_lookup_service.lookup.return_value = SymbolLookup(symbols={'BRK-B': Symbol(id='BRK-B', exchange='NYSE')})

    lookup = DomainEvent.handle(ResolveSymbols, dependencies={'symbol_lookup_service': symbol_lookup_service, 'symbol_alias_service': alias_service(configured)}, ids=['BRK-B'])

    symbol_lookup_service.lookup.assert_called_once_with(['BRK-B'])
    assert lookup.symbols['BRK-B'].id == 'BRK-B'
    assert lookup.failures == []

# ** test: get_symbol_raw_default_ticker
def test_get_symbol_raw_default_ticker_answers_canonical(symbol_lookup_service: mock.Mock) -> None:
    '''
    Test that with nothing configured a raw BRK-B request answers as the canonical BRK.B with no failure.

    :param symbol_lookup_service: The mock symbol lookup service.
    :type symbol_lookup_service: mock.Mock
    '''

    symbol_lookup_service.lookup.return_value = SymbolLookup(symbols={'BRK-B': Symbol(id='BRK-B', exchange='NYSE')})

    lookup = DomainEvent.handle(GetSymbol, dependencies={'symbol_lookup_service': symbol_lookup_service, 'symbol_alias_service': alias_service()}, id='BRK-B')

    symbol_lookup_service.lookup.assert_called_once_with(['BRK-B'])
    assert list(lookup.symbols) == ['BRK.B']
    assert lookup.symbols['BRK.B'].id == 'BRK.B'
    assert lookup.failures == []

# ** test: get_symbol_raw_default_ticker_not_found
def test_get_symbol_raw_default_ticker_not_found(symbol_lookup_service: mock.Mock) -> None:
    '''
    Test that a raw BRK-B request the provider does not know still raises SYMBOL_NOT_FOUND.

    :param symbol_lookup_service: The mock symbol lookup service.
    :type symbol_lookup_service: mock.Mock
    '''

    symbol_lookup_service.lookup.return_value = SymbolLookup(failures=[QuoteFailure(symbol_id='BRK-B', reason='not_found')])

    with pytest.raises(TiferetError) as exc_info:
        DomainEvent.handle(GetSymbol, dependencies={'symbol_lookup_service': symbol_lookup_service, 'symbol_alias_service': alias_service()}, id='BRK-B')

    assert exc_info.value.error_code == 'SYMBOL_NOT_FOUND'

# ** test: resolve_symbols_reports_canonical_ids_only
def test_resolve_symbols_reports_canonical_library_ids_only(symbol_lookup_service: mock.Mock) -> None:
    '''
    Test that resolving BRK.B beside its Yahoo ticker BRK-B reports BRK.B alone, and BRK-B falls away with no failure.

    :param symbol_lookup_service: The mock symbol lookup service.
    :type symbol_lookup_service: mock.Mock
    '''

    symbol_lookup_service.lookup.return_value = SymbolLookup(symbols={
        'BRK-B': Symbol(id='BRK-B', exchange='NYSE'),
        'AAPL': Symbol(id='AAPL', exchange='NASDAQ'),
    })

    lookup = DomainEvent.handle(ResolveSymbols, dependencies={'symbol_lookup_service': symbol_lookup_service, 'symbol_alias_service': alias_service()}, ids=['BRK.B', 'BRK-B', 'AAPL'], exchanges={'BRK-B': 'NYSE'})

    symbol_lookup_service.lookup.assert_called_once_with(['BRK-B', 'AAPL'])
    assert list(lookup.symbols) == ['BRK.B', 'AAPL']
    assert lookup.failures == []

# *** testers

# ** tester: test_get_symbol_event
@use_tester(
    type='domain_event',
    target_cls=GetSymbol,
    dependencies={
        'symbol_lookup_service': {
            'module_path': 'tiferet_stocks.interfaces',
            'class_name': 'SymbolLookupService',
        },
        'symbol_alias_service': {
            'module_path': 'tiferet_stocks.interfaces',
            'class_name': 'SymbolAliasService',
        },
    },
    sample_kwargs={'id': 'AAPL'},
    required_params=['id'],
)
class TestGetSymbolEvent:
    '''
    Bound domain event tester for GetSymbol.
    '''

    # * test: missing_required_params
    def test_missing_required_params(self, test_ctx, session):
        '''
        Require an id.
        '''

        test_ctx.assert_missing_required_params()

# ** tester: test_resolve_symbols_event
@use_tester(
    type='domain_event',
    target_cls=ResolveSymbols,
    dependencies={
        'symbol_lookup_service': {
            'module_path': 'tiferet_stocks.interfaces',
            'class_name': 'SymbolLookupService',
        },
        'symbol_alias_service': {
            'module_path': 'tiferet_stocks.interfaces',
            'class_name': 'SymbolAliasService',
        },
    },
    sample_kwargs={'ids': ['AAPL']},
    required_params=['ids'],
)
class TestResolveSymbolsEvent:
    '''
    Bound domain event tester for ResolveSymbols.
    '''

    # * test: missing_required_params
    def test_missing_required_params(self, test_ctx, session):
        '''
        Require ids.
        '''

        test_ctx.assert_missing_required_params()
