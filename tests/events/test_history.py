"""Tiferet Stocks History Event Tests"""

# *** imports

# ** core
import inspect
from unittest import mock

# ** infra
import pytest
from tiferet import TiferetError, use_tester
from tiferet.events import DomainEvent

# ** app
from tiferet_stocks.domain import PriceBar, PriceHistory, QuoteFailure
from tiferet_stocks.mappers import PriceHistoryAggregate
from tiferet_stocks.events import GetHistory
from tiferet_stocks.interfaces import PriceService

# *** fixtures

# ** fixture: price_service
@pytest.fixture
def price_service() -> mock.Mock:
    '''
    A mock price service.
    '''

    return mock.Mock(spec=PriceService)

# *** functions

# ** function: run
def run(price_service: mock.Mock, **kwargs) -> list:
    '''
    Run GetHistory with the mock price service.

    :param price_service: The mock price service.
    :type price_service: mock.Mock
    :param kwargs: The event parameters.
    :type kwargs: dict
    :return: The event result.
    :rtype: list
    '''

    # Handle the event with its one dependency.
    return DomainEvent.handle(GetHistory, dependencies={'price_service': price_service}, **kwargs)

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

    assert list(inspect.signature(GetHistory.__init__).parameters) == ['self', 'price_service']
    patched_open.assert_not_called()

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
