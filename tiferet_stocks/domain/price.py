"""Tiferet Stocks Price Domain Models"""

# *** imports

# ** core
from typing import Dict, List

# ** infra
from pydantic import Field
from tiferet.domain import DomainObject

# ** app
from .quote import Quote, QuoteFailure
from .symbol import Symbol, SymbolWarning

# *** models

# ** model: quote_set
class QuoteSet(DomainObject):
    '''
    The answer to one quote request: every requested id appears once, as a quote or as a failure.
    '''

    # * attribute: quotes
    quotes: Dict[str, Quote] = Field(default_factory=dict, description='The quotes by requested symbol id.')

    # * attribute: symbols
    symbols: Dict[str, Symbol] = Field(default_factory=dict, description='The symbols filled from the same provider response, by requested symbol id.')

    # * attribute: warnings
    warnings: List[SymbolWarning] = Field(default_factory=list, description='Soft warnings about symbol details.')

    # * attribute: failures
    failures: List[QuoteFailure] = Field(default_factory=list, description='The requested ids that produced no quote, with their reasons.')

    # * attribute: fetched_at
    fetched_at: str | None = Field(default=None, description='When the quotes were fetched, as an ISO 8601 UTC timestamp.')
