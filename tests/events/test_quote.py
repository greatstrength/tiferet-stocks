"""Tiferet Stocks Quote Event Tests"""

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
from tiferet_stocks.domain import Quote, QuoteFailure, QuoteList, Symbol, SymbolAlias, SymbolWarning
from tiferet_stocks.events import GetQuotes
from tiferet_stocks.interfaces import PriceService, SymbolAliasService

# *** fixtures

# ** fixture: price_service
@pytest.fixture
def price_service() -> mock.Mock:
    '''
    A mock price service.
    '''

    return mock.Mock(spec=PriceService)

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

# ** test: get_quotes_partial_failure
def test_get_quotes_partial_failure(price_service: mock.Mock) -> None:
    '''
    Test that a partial failure returns the quotations with its failures and does not raise.

    :param price_service: The mock price service.
    :type price_service: mock.Mock
    '''

    price_service.get_quotes.return_value = QuoteList(
        quotes=[Quote(symbol_id='AAPL', price=251.5, source='static')],
        failures=[QuoteFailure(symbol_id='NOPE', reason='not_found')],
    )

    quotations = DomainEvent.handle(GetQuotes, dependencies={'price_service': price_service, 'symbol_alias_service': alias_service()}, symbols=['AAPL', 'NOPE'])

    assert [quote.symbol_id for quote in quotations.quotes] == ['AAPL']
    assert quotations.failures[0].symbol_id == 'NOPE'
    price_service.get_quotes.assert_called_once_with(['AAPL', 'NOPE'])

# ** test: get_quotes_all_failed
def test_get_quotes_all_failed(price_service: mock.Mock) -> None:
    '''
    Test that QUOTES_UNAVAILABLE is raised only when every symbol fails.

    :param price_service: The mock price service.
    :type price_service: mock.Mock
    '''

    price_service.get_quotes.return_value = QuoteList(
        failures=[
            QuoteFailure(symbol_id='NOPE', reason='not_found'),
            QuoteFailure(symbol_id='GONE', reason='timeout', attempts=2),
        ],
    )

    with pytest.raises(TiferetError) as exc_info:
        DomainEvent.handle(GetQuotes, dependencies={'price_service': price_service, 'symbol_alias_service': alias_service()}, symbols=['NOPE', 'GONE'])

    assert exc_info.value.error_code == 'QUOTES_UNAVAILABLE'
    assert exc_info.value.kwargs['symbols'] == 'NOPE, GONE'
    assert [f['reason'] for f in exc_info.value.kwargs['failures']] == ['not_found', 'timeout']

# ** test: get_quotes_single_string
def test_get_quotes_single_string(price_service: mock.Mock) -> None:
    '''
    Test that a single symbol passed as a string is requested as one id.

    :param price_service: The mock price service.
    :type price_service: mock.Mock
    '''

    price_service.get_quotes.return_value = QuoteList(quotes=[Quote(symbol_id='SPY', price=680.0, source='static')])

    DomainEvent.handle(GetQuotes, dependencies={'price_service': price_service, 'symbol_alias_service': alias_service()}, symbols='SPY')

    price_service.get_quotes.assert_called_once_with(['SPY'])

# ** test: get_quotes_depends_only_on_price_service
def test_get_quotes_depends_only_on_price_service(price_service: mock.Mock) -> None:
    '''
    Test that GetQuotes takes no watchlist service and opens no file.

    :param price_service: The mock price service.
    :type price_service: mock.Mock
    '''

    price_service.get_quotes.return_value = QuoteList(quotes=[Quote(symbol_id='SPY', price=680.0, source='static')])

    with mock.patch('builtins.open') as patched_open:
        DomainEvent.handle(GetQuotes, dependencies={'price_service': price_service, 'symbol_alias_service': alias_service()}, symbols=['SPY'])

    assert list(inspect.signature(GetQuotes.__init__).parameters) == ['self', 'price_service', 'symbol_alias_service']
    patched_open.assert_not_called()

# ** test: get_quotes_empty_symbols
def test_get_quotes_empty_symbols(price_service: mock.Mock) -> None:
    '''
    Test that an empty symbol list returns empty quotations without calling the provider.

    :param price_service: The mock price service.
    :type price_service: mock.Mock
    '''

    quotations = DomainEvent.handle(GetQuotes, dependencies={'price_service': price_service, 'symbol_alias_service': alias_service()}, symbols=[])

    assert quotations.quotes == [] and quotations.failures == []
    price_service.get_quotes.assert_not_called()

# ** test: get_quotes_brk_b_alias
def test_get_quotes_brk_b_alias(price_service: mock.Mock) -> None:
    '''
    Test that a canonical BRK.B request is quoted as BRK-B and every part of the answer is re-keyed to BRK.B.

    :param price_service: The mock price service.
    :type price_service: mock.Mock
    '''

    price_service.get_quotes.return_value = QuoteList(
        quotes=[Quote(symbol_id='BRK-B', price=589.83, source='yahoo_chart'), Quote(symbol_id='AAPL', price=251.5, source='yahoo_chart')],
        symbols={'BRK-B': Symbol(id='BRK-B', exchange='NYSE', asset_type='equity')},
        warnings=[SymbolWarning(symbol_id='BRK-B', reason='unmapped_asset_type', detail='TEST')],
        failures=[QuoteFailure(symbol_id='NOPE', reason='not_found')],
        fetched_at='2026-11-12T21:00:00+00:00',
    )

    quotations = DomainEvent.handle(
        GetQuotes,
        dependencies={'price_service': price_service, 'symbol_alias_service': alias_service(brk_aliases())},
        symbols=['BRK.B', 'AAPL', 'NOPE'],
    )

    price_service.get_quotes.assert_called_once_with(['BRK-B', 'AAPL', 'NOPE'])
    assert [quote.symbol_id for quote in quotations.quotes] == ['BRK.B', 'AAPL']
    assert quotations.get_quote('BRK.B').symbol_id == 'BRK.B'
    assert quotations.get_quote('AAPL').symbol_id == 'AAPL'
    assert quotations.symbols['BRK.B'].id == 'BRK.B'
    assert quotations.symbols['BRK.B'].aliases == list(brk_aliases().values())
    assert quotations.warnings[0].symbol_id == 'BRK.B'
    assert [failure.symbol_id for failure in quotations.failures] == ['NOPE']
    assert quotations.fetched_at == '2026-11-12T21:00:00+00:00'

# ** test: get_quotes_brk_b_alias_all_failed
def test_get_quotes_brk_b_alias_all_failed(price_service: mock.Mock) -> None:
    '''
    Test that QUOTES_UNAVAILABLE is unchanged for an aliased symbol and its failures name the canonical id.

    :param price_service: The mock price service.
    :type price_service: mock.Mock
    '''

    price_service.get_quotes.return_value = QuoteList(failures=[QuoteFailure(symbol_id='BRK-B', reason='not_found', detail='HTTP 404')])

    with pytest.raises(TiferetError) as exc_info:
        DomainEvent.handle(
            GetQuotes,
            dependencies={'price_service': price_service, 'symbol_alias_service': alias_service(brk_aliases())},
            symbols=['BRK.B'],
        )

    assert exc_info.value.error_code == 'QUOTES_UNAVAILABLE'
    assert exc_info.value.kwargs['symbols'] == 'BRK.B'
    assert [f['symbol_id'] for f in exc_info.value.kwargs['failures']] == ['BRK.B']

# ** test: get_quotes_empty_symbols_reads_no_aliases
def test_get_quotes_empty_symbols_reads_no_aliases(price_service: mock.Mock) -> None:
    '''
    Test that an empty request returns before the alias and price services are called.

    :param price_service: The mock price service.
    :type price_service: mock.Mock
    '''

    aliases = alias_service(brk_aliases())

    quotations = DomainEvent.handle(GetQuotes, dependencies={'price_service': price_service, 'symbol_alias_service': aliases}, symbols=[])

    assert quotations == QuoteList()
    aliases.get_aliases.assert_not_called()
    price_service.get_quotes.assert_not_called()

# ** test: get_quotes_yahoo_default_alias
def test_get_quotes_yahoo_default_alias_with_nothing_configured(price_service: mock.Mock) -> None:
    '''
    Test that BRK.B is quoted as BRK-B through the Yahoo default alias when no alias is configured.

    :param price_service: The mock price service.
    :type price_service: mock.Mock
    '''

    price_service.get_quotes.return_value = QuoteList(quotes=[Quote(symbol_id='BRK-B', price=589.83, source='yahoo_chart')])

    quotations = DomainEvent.handle(GetQuotes, dependencies={'price_service': price_service, 'symbol_alias_service': alias_service()}, symbols=['BRK.B'])

    price_service.get_quotes.assert_called_once_with(['BRK-B'])
    assert [quote.symbol_id for quote in quotations.quotes] == ['BRK.B']

# ** test: get_quotes_configured_ticker
def test_get_quotes_configured_ticker_replaces_default(price_service: mock.Mock) -> None:
    '''
    Test that a configured alias sending BRK.B under another ticker replaces the Yahoo default, so BRK-B is never sent.

    :param price_service: The mock price service.
    :type price_service: mock.Mock
    '''

    configured = {'BRKB.X': SymbolAlias(provider='yahoo_chart', provider_ticker='BRKB.X', canonical_id='BRK.B')}
    price_service.get_quotes.return_value = QuoteList(quotes=[Quote(symbol_id='BRKB.X', price=589.83, source='yahoo_chart')])

    quotations = DomainEvent.handle(GetQuotes, dependencies={'price_service': price_service, 'symbol_alias_service': alias_service(configured)}, symbols=['BRK.B'])

    price_service.get_quotes.assert_called_once_with(['BRKB.X'])
    assert [quote.symbol_id for quote in quotations.quotes] == ['BRK.B']

# ** test: get_quotes_raw_ticker_with_configured_ticker
def test_get_quotes_raw_default_ticker_passes_through_when_configured_elsewhere(price_service: mock.Mock) -> None:
    '''
    Test that with BRK.B configured as BRKB.X a raw BRK-B request is sent and answered as BRK-B, not re-keyed to BRK.B.

    :param price_service: The mock price service.
    :type price_service: mock.Mock
    '''

    configured = {'BRKB.X': SymbolAlias(provider='yahoo_chart', provider_ticker='BRKB.X', canonical_id='BRK.B')}
    price_service.get_quotes.return_value = QuoteList(
        quotes=[Quote(symbol_id='BRKB.X', price=589.83, source='yahoo_chart'), Quote(symbol_id='BRK-B', price=589.83, source='yahoo_chart')],
    )

    quotations = DomainEvent.handle(GetQuotes, dependencies={'price_service': price_service, 'symbol_alias_service': alias_service(configured)}, symbols=['BRK.B', 'BRK-B'])

    price_service.get_quotes.assert_called_once_with(['BRKB.X', 'BRK-B'])
    assert [quote.symbol_id for quote in quotations.quotes] == ['BRK.B', 'BRK-B']

# ** test: get_quotes_later_configured_alias
def test_get_quotes_later_configured_alias_wins(price_service: mock.Mock) -> None:
    '''
    Test that with X1 then X2 configured for BRK.B, BRK.B is sent as X2 and a raw X1 request stays X1.

    :param price_service: The mock price service.
    :type price_service: mock.Mock
    '''

    configured = {
        'X1': SymbolAlias(provider='yahoo_chart', provider_ticker='X1', canonical_id='BRK.B'),
        'X2': SymbolAlias(provider='yahoo_chart', provider_ticker='X2', canonical_id='BRK.B'),
    }
    price_service.get_quotes.return_value = QuoteList(
        quotes=[Quote(symbol_id='X2', price=589.83, source='yahoo_chart'), Quote(symbol_id='X1', price=1.0, source='yahoo_chart')],
    )

    quotations = DomainEvent.handle(GetQuotes, dependencies={'price_service': price_service, 'symbol_alias_service': alias_service(configured)}, symbols=['BRK.B', 'X1'])

    price_service.get_quotes.assert_called_once_with(['X2', 'X1'])
    assert [quote.symbol_id for quote in quotations.quotes] == ['BRK.B', 'X1']

# ** test: get_quotes_reports_canonical_ids_only
def test_get_quotes_reports_canonical_library_ids_only(price_service: mock.Mock) -> None:
    '''
    Test that with no configured aliases a request for BRK.B, its Yahoo ticker BRK-B and AAPL reports exactly BRK.B and AAPL:
    output carries canonical library ids only, and BRK-B falls away with no failure.

    :param price_service: The mock price service.
    :type price_service: mock.Mock
    '''

    price_service.get_quotes.return_value = QuoteList(
        quotes=[Quote(symbol_id='BRK-B', price=589.83, source='yahoo_chart'), Quote(symbol_id='AAPL', price=251.5, source='yahoo_chart')],
    )

    quotations = DomainEvent.handle(GetQuotes, dependencies={'price_service': price_service, 'symbol_alias_service': alias_service()}, symbols=['BRK.B', 'BRK-B', 'AAPL'])

    price_service.get_quotes.assert_called_once_with(['BRK-B', 'BRK-B', 'AAPL'])
    assert [quote.symbol_id for quote in quotations.quotes] == ['BRK.B', 'AAPL']
    assert quotations.failures == []

# ** test: get_quotes_unavailable_names_canonical_ids
def test_get_quotes_unavailable_names_aliased_ticker_by_canonical_id(price_service: mock.Mock) -> None:
    '''
    Test that QUOTES_UNAVAILABLE names a requested provider ticker that is an alias by its canonical id, and keeps a raw passthrough id as given.

    :param price_service: The mock price service.
    :type price_service: mock.Mock
    '''

    price_service.get_quotes.return_value = QuoteList(failures=[
        QuoteFailure(symbol_id='BRK-B', reason='not_found'),
        QuoteFailure(symbol_id='ZZZZQ', reason='not_found'),
    ])

    with pytest.raises(TiferetError) as exc_info:
        DomainEvent.handle(GetQuotes, dependencies={'price_service': price_service, 'symbol_alias_service': alias_service()}, symbols=['BRK-B', 'BRK.B', 'ZZZZQ'])

    assert exc_info.value.error_code == 'QUOTES_UNAVAILABLE'
    assert exc_info.value.kwargs['symbols'] == 'BRK.B, ZZZZQ'

# ** test: get_quotes_unavailable_raw_passthrough
def test_get_quotes_unavailable_keeps_raw_passthrough_id(price_service: mock.Mock) -> None:
    '''
    Test that with BRK.B configured as BRKB.X a raw BRK-B is no alias, passes through and is named as given.

    :param price_service: The mock price service.
    :type price_service: mock.Mock
    '''

    configured = {'BRKB.X': SymbolAlias(provider='yahoo_chart', provider_ticker='BRKB.X', canonical_id='BRK.B')}
    price_service.get_quotes.return_value = QuoteList(failures=[QuoteFailure(symbol_id='BRK-B', reason='not_found')])

    with pytest.raises(TiferetError) as exc_info:
        DomainEvent.handle(GetQuotes, dependencies={'price_service': price_service, 'symbol_alias_service': alias_service(configured)}, symbols=['BRK-B'])

    assert exc_info.value.kwargs['symbols'] == 'BRK-B'

# *** testers

# ** tester: test_get_quotes_event
@use_tester(
    type='domain_event',
    target_cls=GetQuotes,
    dependencies={
        'price_service': {
            'module_path': 'tiferet_stocks.interfaces',
            'class_name': 'PriceService',
        },
        'symbol_alias_service': {
            'module_path': 'tiferet_stocks.interfaces',
            'class_name': 'SymbolAliasService',
        },
    },
    sample_kwargs={'symbols': ['AAPL']},
    required_params=['symbols'],
)
class TestGetQuotesEvent:
    '''
    Bound domain event tester for GetQuotes.
    '''

    # * test: missing_required_params
    def test_missing_required_params(self, test_ctx, session):
        '''
        Require symbols.
        '''

        test_ctx.assert_missing_required_params()
