"""Tiferet Stocks Quote List Domain Models"""

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

# ** model: quote_list
class QuoteList(DomainObject):
    '''
    The answer to one quote request: a list of quotes, with a failure for every requested id that produced none.
    '''

    # * attribute: quotes
    quotes: List[Quote] = Field(default_factory=list, description='The quotes in request order, one per requested id that produced a quote.')

    # * attribute: symbols
    symbols: Dict[str, Symbol] = Field(default_factory=dict, description='The symbols filled from the same provider response, by requested symbol id.')

    # * attribute: warnings
    warnings: List[SymbolWarning] = Field(default_factory=list, description='Soft warnings about symbol details.')

    # * attribute: failures
    failures: List[QuoteFailure] = Field(default_factory=list, description='The requested ids that produced no quote, with their reasons.')

    # * attribute: fetched_at
    fetched_at: str | None = Field(default=None, description='When the quotes were fetched, as an ISO 8601 UTC timestamp.')

    # * method: get_quote
    def get_quote(self, symbol_id: str) -> Quote | None:
        '''
        Get the quote for one requested symbol id.

        :param symbol_id: The requested symbol id (ticker).
        :type symbol_id: str
        :return: The quote, or None when the id produced no quote.
        :rtype: Quote | None
        '''

        # Walk the list by symbol id; the list holds at most one quote per id.
        return next((quote for quote in self.quotes if quote.symbol_id == symbol_id), None)
