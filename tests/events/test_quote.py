"""Tiferet Stocks Quote Event Tests"""

# *** imports

# ** core
import inspect
from unittest import mock

# ** infra
import pytest
from tiferet import TiferetError, use_tester
from tiferet.events import DomainEvent

# ** app
from tiferet_stocks.domain import Quote, QuoteFailure, QuoteSet
from tiferet_stocks.events import GetQuotes
from tiferet_stocks.interfaces import PriceService

# *** fixtures

# ** fixture: price_service
@pytest.fixture
def price_service() -> mock.Mock:
    '''
    A mock price service.
    '''

    return mock.Mock(spec=PriceService)

# *** tests

# ** test: get_quotes_partial_failure
def test_get_quotes_partial_failure(price_service: mock.Mock) -> None:
    '''
    Test that a partial failure returns the quote set with its failures and does not raise.

    :param price_service: The mock price service.
    :type price_service: mock.Mock
    '''

    price_service.get_quotes.return_value = QuoteSet(
        quotes={'AAPL': Quote(symbol_id='AAPL', price=251.5, source='static')},
        failures=[QuoteFailure(symbol_id='NOPE', reason='not_found')],
    )

    quote_set = DomainEvent.handle(GetQuotes, dependencies={'price_service': price_service}, symbols=['AAPL', 'NOPE'])

    assert list(quote_set.quotes) == ['AAPL']
    assert quote_set.failures[0].symbol_id == 'NOPE'
    price_service.get_quotes.assert_called_once_with(['AAPL', 'NOPE'])

# ** test: get_quotes_all_failed
def test_get_quotes_all_failed(price_service: mock.Mock) -> None:
    '''
    Test that QUOTES_UNAVAILABLE is raised only when every symbol fails.

    :param price_service: The mock price service.
    :type price_service: mock.Mock
    '''

    price_service.get_quotes.return_value = QuoteSet(
        failures=[
            QuoteFailure(symbol_id='NOPE', reason='not_found'),
            QuoteFailure(symbol_id='GONE', reason='timeout', attempts=2),
        ],
    )

    with pytest.raises(TiferetError) as exc_info:
        DomainEvent.handle(GetQuotes, dependencies={'price_service': price_service}, symbols=['NOPE', 'GONE'])

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

    price_service.get_quotes.return_value = QuoteSet(quotes={'SPY': Quote(symbol_id='SPY', price=680.0, source='static')})

    DomainEvent.handle(GetQuotes, dependencies={'price_service': price_service}, symbols='SPY')

    price_service.get_quotes.assert_called_once_with(['SPY'])

# ** test: get_quotes_depends_only_on_price_service
def test_get_quotes_depends_only_on_price_service(price_service: mock.Mock) -> None:
    '''
    Test that GetQuotes takes no watchlist service and opens no file.

    :param price_service: The mock price service.
    :type price_service: mock.Mock
    '''

    price_service.get_quotes.return_value = QuoteSet(quotes={'SPY': Quote(symbol_id='SPY', price=680.0, source='static')})

    with mock.patch('builtins.open') as patched_open:
        DomainEvent.handle(GetQuotes, dependencies={'price_service': price_service}, symbols=['SPY'])

    assert list(inspect.signature(GetQuotes.__init__).parameters) == ['self', 'price_service']
    patched_open.assert_not_called()

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
