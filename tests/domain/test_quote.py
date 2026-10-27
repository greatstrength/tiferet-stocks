"""Tiferet Stocks Quote Domain Tests"""

# *** imports

# ** infra
import pytest
from pydantic import ValidationError

# ** app
from tiferet_stocks.domain import (
    FAILURE_REASONS,
    SYMBOL_MISMATCH,
    QuoteFailure,
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
