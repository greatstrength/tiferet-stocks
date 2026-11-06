"""Tiferet Stocks History Domain Models"""

# *** imports

# ** core
from typing import List

# ** infra
from pydantic import Field
from tiferet.domain import DomainObject

# ** app
from .quote import PriceBar, QuoteFailure

# *** models

# ** model: price_history
class PriceHistory(DomainObject):
    '''
    The answer to one history request: the daily bars for one symbol and date range, or the failure.
    '''

    # * attribute: symbol_id
    symbol_id: str = Field(..., description='The requested symbol id (ticker).')

    # * attribute: start
    start: str = Field(..., description='The first requested day, as an ISO 8601 date (inclusive).')

    # * attribute: end
    end: str = Field(..., description='The last requested day, as an ISO 8601 date (inclusive).')

    # * attribute: bars
    bars: List[PriceBar] = Field(default_factory=list, description='The daily bars within the range, oldest first.')

    # * attribute: failure
    failure: QuoteFailure | None = Field(default=None, description='Why the provider produced no history, when it failed.')
