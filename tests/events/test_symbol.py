"""Tiferet Stocks Symbol Event Tests"""

# *** imports

# ** core
import inspect
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
    SymbolLookup,
    SymbolWarning,
)
from tiferet_stocks.events import (
    GetSymbol,
    ListExchanges,
    ResolveSymbols,
    SymbolLookupEvent,
)
from tiferet_stocks.interfaces import SymbolLookupService

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

# *** tests

# ** test: get_symbol
def test_get_symbol(symbol_lookup_service: mock.Mock) -> None:
    '''
    Test that GetSymbol returns the symbol when the expected exchange matches.

    :param symbol_lookup_service: The mock symbol lookup service.
    :type symbol_lookup_service: mock.Mock
    '''

    lookup = DomainEvent.handle(GetSymbol, dependencies={'symbol_lookup_service': symbol_lookup_service}, id='AAPL', exchange='NASDAQ')

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

    lookup = DomainEvent.handle(GetSymbol, dependencies={'symbol_lookup_service': symbol_lookup_service}, id='AAPL', exchange='NYSE')

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

    symbol_lookup_service.lookup.return_value = SymbolLookup(symbols={'BRK.B': Symbol(id='BRK-B', exchange='NYSE')})

    lookup = DomainEvent.handle(GetSymbol, dependencies={'symbol_lookup_service': symbol_lookup_service}, id='BRK.B')

    assert lookup.symbols == {}
    assert lookup.failures[0].reason == 'symbol_mismatch'
    assert lookup.failures[0].detail == 'expected ticker BRK.B, actual ticker BRK-B'

# ** test: get_symbol_ticker_case_insensitive
def test_get_symbol_ticker_case_insensitive(symbol_lookup_service: mock.Mock) -> None:
    '''
    Test that the ticker check ignores case.

    :param symbol_lookup_service: The mock symbol lookup service.
    :type symbol_lookup_service: mock.Mock
    '''

    symbol_lookup_service.lookup.return_value = SymbolLookup(symbols={'aapl': Symbol(id='AAPL', exchange='NASDAQ')})

    lookup = DomainEvent.handle(GetSymbol, dependencies={'symbol_lookup_service': symbol_lookup_service}, id='aapl')

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
        DomainEvent.handle(GetSymbol, dependencies={'symbol_lookup_service': symbol_lookup_service}, id=None)

# ** test: resolve_symbols
def test_resolve_symbols(symbol_lookup_service: mock.Mock) -> None:
    '''
    Test that ResolveSymbols keeps matches, passes provider failures through, and reports unresolved ids.

    :param symbol_lookup_service: The mock symbol lookup service.
    :type symbol_lookup_service: mock.Mock
    '''

    lookup = DomainEvent.handle(
        ResolveSymbols,
        dependencies={'symbol_lookup_service': symbol_lookup_service},
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
        DomainEvent.handle(ResolveSymbols, dependencies={'symbol_lookup_service': symbol_lookup_service}, ids=None)

# ** test: symbol_events_depend_only_on_lookup
def test_symbol_events_depend_only_on_lookup() -> None:
    '''
    Test that symbol events take only the symbol lookup service: no watchlist service and no file writes.
    '''

    params = list(inspect.signature(SymbolLookupEvent.__init__).parameters)

    assert params == ['self', 'symbol_lookup_service']
    assert GetSymbol.__init__ is SymbolLookupEvent.__init__
    assert ResolveSymbols.__init__ is SymbolLookupEvent.__init__

# ** test: resolve_symbols_single_string
def test_resolve_symbols_single_string(symbol_lookup_service: mock.Mock) -> None:
    '''
    Test that a single id passed as a string is looked up as one id, not per character.

    :param symbol_lookup_service: The mock symbol lookup service.
    :type symbol_lookup_service: mock.Mock
    '''

    lookup = DomainEvent.handle(ResolveSymbols, dependencies={'symbol_lookup_service': symbol_lookup_service}, ids='AAPL')

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
        DomainEvent.handle(ResolveSymbols, dependencies={'symbol_lookup_service': symbol_lookup_service}, ids=['AAPL', 'SPY'])

    patched_open.assert_not_called()

# ** test: list_exchanges
def test_list_exchanges() -> None:
    '''
    Test that ListExchanges returns a copy of EXCHANGES with no dependency.
    '''

    exchanges = DomainEvent.handle(ListExchanges)

    assert exchanges == EXCHANGES
    assert exchanges is not EXCHANGES

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
