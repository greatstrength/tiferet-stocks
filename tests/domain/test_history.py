"""Tiferet Stocks History Domain Tests"""

# *** imports

# ** infra
import pytest
from pydantic import ValidationError
from tiferet import use_tester

# ** app
from tiferet_stocks.domain import PriceBar, PriceHistory, QuoteFailure

# *** tests

# ** test: price_bar_numeric_fields
def test_price_bar_numeric_fields() -> None:
    '''
    Test that bar prices stay floats and volume stays an int despite coerce_numbers_to_str on DomainObject.
    '''

    bar = PriceBar(symbol_id='AAPL', date='2026-10-19', open=341, high=344, low=340, close=342.94, adj_close=342, volume=34573200)

    assert all(isinstance(value, float) for value in (bar.open, bar.high, bar.low, bar.close, bar.adj_close))
    assert isinstance(bar.volume, int)

# ** test: price_bar_optional_fields
def test_price_bar_optional_fields() -> None:
    '''
    Test that adj_close and volume are optional.
    '''

    bar = PriceBar(symbol_id='AAPL', date='2026-10-19', open=1.0, high=1.0, low=1.0, close=1.0)

    assert (bar.adj_close, bar.volume) == (None, None)

# ** test: price_bar_requires_prices
@pytest.mark.parametrize('missing', ['symbol_id', 'date', 'open', 'high', 'low', 'close'])
def test_price_bar_requires_prices(missing: str) -> None:
    '''
    Test that the symbol, date and the four prices are required.

    :param missing: The field left out.
    :type missing: str
    '''

    data = {'symbol_id': 'AAPL', 'date': '2026-10-19', 'open': 1.0, 'high': 1.0, 'low': 1.0, 'close': 1.0}
    data.pop(missing)

    with pytest.raises(ValidationError):
        PriceBar(**data)

# ** test: price_history_defaults
def test_price_history_defaults() -> None:
    '''
    Test that an empty history has no bars and no failure, and can carry a failure.
    '''

    history = PriceHistory(symbol_id='AAPL', start='2026-10-19', end='2026-10-23')

    assert (history.bars, history.failure) == ([], None)
    failed = PriceHistory(symbol_id='NOPE', start='2026-10-19', end='2026-10-23', failure=QuoteFailure(symbol_id='NOPE', reason='not_found'))
    assert failed.failure.reason == 'not_found'

# *** testers

# ** tester: test_price_bar
@use_tester(
    type='domain',
    target_cls=PriceBar,
    sample_data={'symbol_id': 'AAPL', 'date': '2026-10-19', 'open': 341.0, 'high': 344.0, 'low': 340.0, 'close': 342.94, 'adj_close': 342.94, 'volume': 34573200},
    equality_fields=['symbol_id', 'date', 'open', 'high', 'low', 'close', 'adj_close', 'volume'],
)
class TestPriceBar:
    '''
    Bound domain tester for PriceBar.
    '''

    # * test: new
    def test_new(self, test_ctx, session):
        '''
        Construct a bar from sample data.
        '''

        test_ctx.assert_new()

# ** tester: test_price_history
@use_tester(
    type='domain',
    target_cls=PriceHistory,
    sample_data={'symbol_id': 'AAPL', 'start': '2026-10-19', 'end': '2026-10-23'},
    equality_fields=['symbol_id', 'start', 'end', 'bars', 'failure'],
)
class TestPriceHistory:
    '''
    Bound domain tester for PriceHistory.
    '''

    # * test: new
    def test_new(self, test_ctx, session):
        '''
        Construct a history from sample data.
        '''

        test_ctx.assert_new()
