"""Tiferet Stocks History Mappers"""

# *** imports

# ** core
from typing import ClassVar

# ** infra
from tiferet.mappers import Aggregate

# ** app
from ..domain import PriceHistory

# *** mappers

# ** mapper: price_history_aggregate
class PriceHistoryAggregate(PriceHistory, Aggregate):
    '''
    An aggregate representation of a price history, as returned by the price providers.
    '''

    # * attribute: _SETTABLE_ATTRIBUTES
    _SETTABLE_ATTRIBUTES: ClassVar[set] = set()
