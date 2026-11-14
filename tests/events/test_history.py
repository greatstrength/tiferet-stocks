"""Tiferet Stocks History Event Tests"""

# *** imports

# ** core
import inspect
from datetime import date
from typing import Dict
from unittest import mock

# ** infra
import pytest
from tiferet import TiferetError, use_tester
from tiferet.events import DomainEvent

# ** app
from tiferet_stocks.domain import PriceBar, QuoteFailure, SymbolAlias
from tiferet_stocks.mappers import PriceHistoryAggregate
from tiferet_stocks.events import GetHistory
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

# ** function: run
def run(price_service: mock.Mock, aliases: Dict[str, SymbolAlias] = None, **kwargs) -> list:
    '''
    Run GetHistory with the mock price service and a mock alias service.

    :param price_service: The mock price service.
    :type price_service: mock.Mock
    :param aliases: The aliases the mock alias service returns, keyed by provider ticker.
    :type aliases: Dict[str, SymbolAlias]
    :param kwargs: The event parameters.
    :type kwargs: dict
    :return: The event result.
    :rtype: list
    '''

    # Handle the event with its dependencies.
    return DomainEvent.handle(GetHistory, dependencies={'price_service': price_service, 'symbol_alias_service': alias_service(aliases)}, **kwargs)

# *** tests

# ** test: get_history_bars
def test_get_history_bars(price_service: mock.Mock) -> None:
    '''
    Test that the bars from the provider are returned as they are.

    :param price_service: The mock price service.
    :type price_service: mock.Mock
    '''

    bar = PriceBar(symbol_id='AAPL', date='2026-10-19', open=1, high=2, low=1, close=2, volume=10)
    price_service.get_history.return_value = PriceHistoryAggregate(symbol_id='AAPL', start='2026-10-19', end='2026-10-23', bars=[bar])

    bars = run(price_service, symbol='AAPL', start='2026-10-19', end='2026-10-23')

    assert bars == [bar]
    price_service.get_history.assert_called_once_with('AAPL', '2026-10-19', '2026-10-23')

# ** test: get_history_empty_range
def test_get_history_empty_range(price_service: mock.Mock) -> None:
    '''
    Test that a valid range with no trading days returns an empty list and raises nothing.

    :param price_service: The mock price service.
    :type price_service: mock.Mock
    '''

    price_service.get_history.return_value = PriceHistoryAggregate(symbol_id='AAPL', start='2026-10-24', end='2026-10-25')

    assert run(price_service, symbol='AAPL', start='2026-10-24', end='2026-10-25') == []

# ** test: get_history_single_day
def test_get_history_single_day(price_service: mock.Mock) -> None:
    '''
    Test that a range of one day is valid.

    :param price_service: The mock price service.
    :type price_service: mock.Mock
    '''

    price_service.get_history.return_value = PriceHistoryAggregate(symbol_id='AAPL', start='2026-10-19', end='2026-10-19')

    assert run(price_service, symbol='AAPL', start='2026-10-19', end='2026-10-19') == []

# ** test: get_history_unavailable
@pytest.mark.parametrize('reason', ['not_found', 'http_error', 'timeout', 'bad_payload'])
def test_get_history_unavailable(price_service: mock.Mock, reason: str) -> None:
    '''
    Test that a provider failure for the symbol raises HISTORY_UNAVAILABLE with the reason.

    :param price_service: The mock price service.
    :type price_service: mock.Mock
    :param reason: The failure reason.
    :type reason: str
    '''

    failure = QuoteFailure(symbol_id='NOPE', reason=reason, attempts=2)
    price_service.get_history.return_value = PriceHistoryAggregate(symbol_id='NOPE', start='2026-10-19', end='2026-10-23', failure=failure)

    with pytest.raises(TiferetError) as exc_info:
        run(price_service, symbol='NOPE', start='2026-10-19', end='2026-10-23')

    assert exc_info.value.error_code == 'HISTORY_UNAVAILABLE'
    assert exc_info.value.kwargs['symbol'] == 'NOPE'
    assert exc_info.value.kwargs['reason'] == reason
    assert exc_info.value.kwargs['failure']['attempts'] == 2

# ** test: get_history_invalid_range
@pytest.mark.parametrize('start, end', [
    ('2026-10-23', '2026-10-19'),
    ('2026-13-01', '2026-10-19'),
    ('yesterday', '2026-10-19'),
    ('2026-10-19', '20261023'),
    (20261019, '2026-10-23'),
])
def test_get_history_invalid_range(price_service: mock.Mock, start: str, end: str) -> None:
    '''
    Test that a backwards range or a non-ISO date raises INVALID_HISTORY_RANGE before the provider is called.

    :param price_service: The mock price service.
    :type price_service: mock.Mock
    :param start: The start date.
    :type start: str
    :param end: The end date.
    :type end: str
    '''

    with pytest.raises(TiferetError) as exc_info:
        run(price_service, symbol='AAPL', start=start, end=end)

    assert exc_info.value.error_code == 'INVALID_HISTORY_RANGE'
    price_service.get_history.assert_not_called()

# ** test: get_history_date_objects
def test_get_history_date_objects(price_service: mock.Mock) -> None:
    '''
    Test that date objects passed to execute directly raise INVALID_HISTORY_RANGE rather than a TypeError.

    :param price_service: The mock price service.
    :type price_service: mock.Mock
    '''

    with pytest.raises(TiferetError) as exc_info:
        GetHistory(price_service=price_service, symbol_alias_service=alias_service()).execute(symbol='AAPL', start=date(2026, 10, 19), end=date(2026, 10, 23))

    assert exc_info.value.error_code == 'INVALID_HISTORY_RANGE'
    price_service.get_history.assert_not_called()

# ** test: get_history_depends_only_on_price_service
def test_get_history_depends_only_on_price_service(price_service: mock.Mock) -> None:
    '''
    Test that GetHistory takes no watchlist service and opens no file.

    :param price_service: The mock price service.
    :type price_service: mock.Mock
    '''

    price_service.get_history.return_value = PriceHistoryAggregate(symbol_id='AAPL', start='2026-10-19', end='2026-10-23')

    with mock.patch('builtins.open') as patched_open:
        run(price_service, symbol='AAPL', start='2026-10-19', end='2026-10-23')

    assert list(inspect.signature(GetHistory.__init__).parameters) == ['self', 'price_service', 'symbol_alias_service']
    patched_open.assert_not_called()

# ** test: get_history_brk_b_alias
def test_get_history_brk_b_alias(price_service: mock.Mock) -> None:
    '''
    Test that a canonical BRK.B request is fetched as BRK-B and its bars come back under BRK.B.

    :param price_service: The mock price service.
    :type price_service: mock.Mock
    '''

    bar = PriceBar(symbol_id='BRK-B', date='2026-10-20', open=1, high=2, low=1, close=2)
    price_service.get_history.return_value = PriceHistoryAggregate(symbol_id='BRK-B', start='2026-10-20', end='2026-10-20', bars=[bar])

    bars = run(price_service, aliases=brk_aliases(), symbol='BRK.B', start='2026-10-20', end='2026-10-20')

    price_service.get_history.assert_called_once_with('BRK-B', '2026-10-20', '2026-10-20')
    assert [b.symbol_id for b in bars] == ['BRK.B']
    assert bars[0].close == 2

# ** test: get_history_brk_b_alias_unavailable
def test_get_history_brk_b_alias_unavailable(price_service: mock.Mock) -> None:
    '''
    Test that HISTORY_UNAVAILABLE is unchanged for an aliased symbol and names the canonical id.

    :param price_service: The mock price service.
    :type price_service: mock.Mock
    '''

    failure = QuoteFailure(symbol_id='BRK-B', reason='not_found', detail='HTTP 404')
    price_service.get_history.return_value = PriceHistoryAggregate(symbol_id='BRK-B', start='2026-10-20', end='2026-10-20', failure=failure)

    with pytest.raises(TiferetError) as exc_info:
        run(price_service, aliases=brk_aliases(), symbol='BRK.B', start='2026-10-20', end='2026-10-20')

    assert exc_info.value.error_code == 'HISTORY_UNAVAILABLE'
    assert exc_info.value.kwargs['symbol'] == 'BRK.B'
    assert exc_info.value.kwargs['failure']['symbol_id'] == 'BRK.B'

# ** test: get_history_control_without_alias
def test_get_history_control_without_alias(price_service: mock.Mock) -> None:
    '''
    Test that a symbol with no alias is requested and returned unchanged when aliases are configured.

    :param price_service: The mock price service.
    :type price_service: mock.Mock
    '''

    bar = PriceBar(symbol_id='AAPL', date='2026-10-20', open=1, high=2, low=1, close=2)
    price_service.get_history.return_value = PriceHistoryAggregate(symbol_id='AAPL', start='2026-10-20', end='2026-10-20', bars=[bar])

    bars = run(price_service, aliases=brk_aliases(), symbol='AAPL', start='2026-10-20', end='2026-10-20')

    price_service.get_history.assert_called_once_with('AAPL', '2026-10-20', '2026-10-20')
    assert bars == [bar]

# ** test: get_history_configured_ticker
def test_get_history_configured_ticker_replaces_default(price_service: mock.Mock) -> None:
    '''
    Test that a configured alias fetching BRK.B under another ticker replaces the Yahoo default, so BRK-B is never sent.

    :param price_service: The mock price service.
    :type price_service: mock.Mock
    '''

    configured = {'BRKB.X': SymbolAlias(provider='yahoo_chart', provider_ticker='BRKB.X', canonical_id='BRK.B')}
    bar = PriceBar(symbol_id='BRKB.X', date='2026-10-20', open=1, high=2, low=1, close=2)
    price_service.get_history.return_value = PriceHistoryAggregate(symbol_id='BRKB.X', start='2026-10-20', end='2026-10-20', bars=[bar])

    bars = run(price_service, aliases=configured, symbol='BRK.B', start='2026-10-20', end='2026-10-20')

    price_service.get_history.assert_called_once_with('BRKB.X', '2026-10-20', '2026-10-20')
    assert [b.symbol_id for b in bars] == ['BRK.B']

# *** testers

# ** tester: test_get_history_event
@use_tester(
    type='domain_event',
    target_cls=GetHistory,
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
    sample_kwargs={'symbol': 'AAPL', 'start': '2026-10-19', 'end': '2026-10-23'},
    required_params=['symbol', 'start', 'end'],
)
class TestGetHistoryEvent:
    '''
    Bound domain event tester for GetHistory.
    '''

    # * test: missing_required_params
    def test_missing_required_params(self, test_ctx, session):
        '''
        Require symbol, start and end.
        '''

        test_ctx.assert_missing_required_params()
