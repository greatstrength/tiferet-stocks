"""Tiferet Stocks Quote Domain Models"""

# *** imports

# ** core
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
