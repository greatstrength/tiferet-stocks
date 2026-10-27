"""Tiferet Stocks Quote Domain Models"""

# *** imports

# ** core
import math
from typing import Literal

# ** infra
from pydantic import Field
from tiferet.domain import DomainObject

# *** constants

# ** constant: not_found
NOT_FOUND = 'not_found'

# ** constant: http_error
HTTP_ERROR = 'http_error'

# ** constant: timeout
TIMEOUT = 'timeout'

# ** constant: bad_payload
BAD_PAYLOAD = 'bad_payload'

# ** constant: symbol_mismatch
SYMBOL_MISMATCH = 'symbol_mismatch'

# ** constant: failure_reasons
FAILURE_REASONS = [
    NOT_FOUND,
    HTTP_ERROR,
    TIMEOUT,
    BAD_PAYLOAD,
    SYMBOL_MISMATCH,
]

# *** functions

# ** function: derive_change_pct
def derive_change_pct(price: float, previous_close: float | None) -> float | None:
    '''
    Derive the percent change of a price from the previous close.

    :param price: The latest price.
    :type price: float
    :param previous_close: The previous close, when known.
    :type previous_close: float | None
    :return: The percent change rounded to 4 decimal places, or None when the price or previous close is not a usable number.
    :rtype: float | None
    '''

    # No change can be derived without a finite price and a finite, positive previous close.
    if isinstance(price, bool) or not isinstance(price, (int, float)) or not math.isfinite(price):
        return None
    if isinstance(previous_close, bool) or not isinstance(previous_close, (int, float)):
        return None
    if not math.isfinite(previous_close) or previous_close <= 0:
        return None

    # Return the percent change from the previous close.
    return round((price - previous_close) / previous_close * 100, 4)

# *** models

# ** model: quote_failure
class QuoteFailure(DomainObject):
    '''
    A named reason a requested symbol produced no result.
    '''

    # * attribute: symbol_id
    symbol_id: str = Field(..., description='The requested symbol id (ticker).')

    # * attribute: reason
    reason: Literal[tuple(FAILURE_REASONS)] = Field(..., description='The failure reason.')

    # * attribute: detail
    detail: str | None = Field(default=None, description='Detail about the failure, such as a status code or the expected and actual values.')

    # * attribute: attempts
    attempts: int = Field(default=1, ge=0, description='The number of provider attempts made for the symbol.')

# ** model: quote
class Quote(DomainObject):
    '''
    The latest price for one symbol from one provider.
    '''

    # * attribute: symbol_id
    symbol_id: str = Field(..., description='The symbol id (ticker) the quote is for.')

    # * attribute: price
    price: float = Field(..., description='The latest price; declared float so it is never coerced to a string.')

    # * attribute: previous_close
    previous_close: float | None = Field(default=None, description='The previous close, when the provider returns it.')

    # * attribute: change_pct
    change_pct: float | None = Field(default=None, description='The percent change from the previous close, when it is known.')

    # * attribute: market_time
    market_time: str | None = Field(default=None, description='The market time of the price, as an ISO 8601 UTC timestamp.')

    # * attribute: currency
    currency: str | None = Field(default=None, description='The currency of the price.')

    # * attribute: source
    source: str = Field(..., description='The id of the provider that returned the quote.')
