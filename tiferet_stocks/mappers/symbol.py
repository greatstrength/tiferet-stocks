"""Tiferet Stocks Symbol Mappers"""

# *** imports

# ** core
from typing import Any, ClassVar, Dict

# ** infra
from tiferet.mappers import Aggregate, TransferObject

# ** app
from ..domain import Symbol

# *** mappers

# ** mapper: symbol_aggregate
class SymbolAggregate(Symbol, Aggregate):
    '''
    An aggregate representation of a symbol.
    '''

    # * attribute: _SETTABLE_ATTRIBUTES
    _SETTABLE_ATTRIBUTES: ClassVar[set] = set()

# ** mapper: symbol_yahoo_object
class SymbolYahooObject(Symbol, TransferObject):
    '''
    A Yahoo chart representation of a symbol, built from already-translated exchange ids and asset types.
    '''

    # * attribute: _ROLES
    _ROLES: ClassVar[Dict[str, Dict[str, Any]]] = {
        'to_model': {},
        'to_data': {},
    }

    # * method: map
    def map(self, **overrides) -> SymbolAggregate:
        '''
        Maps the Yahoo symbol data to a symbol aggregate.

        :param overrides: Additional keyword arguments.
        :type overrides: dict
        :return: A new symbol aggregate.
        :rtype: SymbolAggregate
        '''

        # Map to the symbol aggregate.
        return super().map(SymbolAggregate, **overrides)
