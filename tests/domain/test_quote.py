"""Tiferet Stocks Quote Domain Tests"""

# *** imports

# ** infra
import pytest
from pydantic import ValidationError
from tiferet import use_tester

# ** app
from tiferet_stocks.domain import (
    FAILURE_REASONS,
    SYMBOL_MISMATCH,
    derive_change_pct,
    Quote,
    QuoteFailure,
    QuoteSet,
)

# *** tests

# ** test: failure_reasons_constant
def test_failure_reasons_constant() -> None:
    '''
    Test that FAILURE_REASONS names every v1 failure reason, including symbol_mismatch.
    '''

    assert FAILURE_REASONS == ['not_found', 'http_error', 'timeout', 'bad_payload', 'symbol_mismatch']

# ** test: quote_failure_symbol_mismatch
def test_quote_failure_symbol_mismatch() -> None:
    '''
    Test that a quote failure carries a symbol_mismatch reason with its detail.
    '''

    failure = QuoteFailure(
        symbol_id='AAPL',
        reason=SYMBOL_MISMATCH,
        detail='expected exchange NYSE, actual exchange NASDAQ',
    )

    assert failure.reason == 'symbol_mismatch'
    assert failure.attempts == 1

# ** test: quote_failure_rejects_unknown_reason
def test_quote_failure_rejects_unknown_reason() -> None:
    '''
    Test that a quote failure only accepts a known reason and a non-negative attempt count.
    '''

    with pytest.raises(ValidationError):
        QuoteFailure(symbol_id='AAPL', reason='unknown')
    with pytest.raises(ValidationError):
        QuoteFailure(symbol_id='AAPL', reason='timeout', attempts=-1)

# ** test: derive_change_pct
@pytest.mark.parametrize('price, previous_close, expected', [
    (110.0, 100.0, 10.0),
    (99.0, 100.0, -1.0),
    (346.28, 343.91, 0.6891),
    (100.0, None, None),
    (100.0, 0, None),
])
def test_derive_change_pct(price: float, previous_close: float, expected: float) -> None:
    '''
    Test that the change is a percent of the previous close, rounded to 4 places, and empty without one.

    :param price: The latest price.
    :type price: float
    :param previous_close: The previous close.
    :type previous_close: float
    :param expected: The expected percent change.
    :type expected: float
    '''

    assert derive_change_pct(price, previous_close) == expected

# ** test: quote_numeric_fields
def test_quote_numeric_fields() -> None:
    '''
    Test that price, previous_close and change_pct stay floats despite coerce_numbers_to_str on DomainObject.
    '''

    quote = Quote(symbol_id='SPY', price=680, previous_close=675.5, change_pct=0.6662, source='static')

    assert isinstance(quote.price, float)
    assert isinstance(quote.previous_close, float)
    assert isinstance(quote.change_pct, float)

# ** test: quote_requires_price_and_source
def test_quote_requires_price_and_source() -> None:
    '''
    Test that a quote needs a price and a source.
    '''

    with pytest.raises(ValidationError):
        Quote(symbol_id='SPY', source='static')
    with pytest.raises(ValidationError):
        Quote(symbol_id='SPY', price=680.0)

# ** test: quote_set_defaults
def test_quote_set_defaults() -> None:
    '''
    Test that an empty quote set has no quotes, symbols, warnings or failures.
    '''

    quote_set = QuoteSet()

    assert quote_set.quotes == {}
    assert quote_set.symbols == {}
    assert quote_set.warnings == []
    assert quote_set.failures == []
    assert quote_set.fetched_at is None

# *** testers

# ** tester: test_quote
@use_tester(
    type='domain',
    target_cls=Quote,
    sample_data={'symbol_id': 'AAPL', 'price': 251.5, 'previous_close': 250.0, 'change_pct': 0.6, 'market_time': '2026-10-26T20:00:00+00:00', 'currency': 'USD', 'source': 'yahoo_chart'},
    equality_fields=['symbol_id', 'price', 'previous_close', 'change_pct', 'market_time', 'currency', 'source'],
)
class TestQuote:
    '''
    Bound domain tester for Quote.
    '''

    # * test: new
    def test_new(self, test_ctx, session):
        '''
        Construct a quote from sample data.
        '''

        test_ctx.assert_new()
