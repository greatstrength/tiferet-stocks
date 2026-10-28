"""Tiferet Stocks Quotations Mappers"""

# *** imports

# ** core
from typing import ClassVar

# ** infra
from tiferet.mappers import Aggregate

# ** app
from ..domain import Quotations

# *** mappers

# ** mapper: quotations_aggregate
class QuotationsAggregate(Quotations, Aggregate):
    '''
    An aggregate representation of quotations, as returned by the price providers.
    '''

    # * attribute: _SETTABLE_ATTRIBUTES
    _SETTABLE_ATTRIBUTES: ClassVar[set] = set()
