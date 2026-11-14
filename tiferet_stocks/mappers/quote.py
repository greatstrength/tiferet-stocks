"""Tiferet Stocks Quote Mappers"""

# *** imports

# ** core
from typing import ClassVar

# ** infra
from tiferet.mappers import Aggregate

# ** app
from ..domain import QuoteList

# *** mappers

# ** mapper: quote_list_aggregate
class QuoteListAggregate(QuoteList, Aggregate):
    '''
    An aggregate representation of a quote list, as returned by the price providers.
    '''

    # * attribute: _SETTABLE_ATTRIBUTES
    _SETTABLE_ATTRIBUTES: ClassVar[set] = set()
