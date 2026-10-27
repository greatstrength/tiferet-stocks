"""Tiferet Stocks Symbol Interfaces"""

# *** imports

# ** core
from abc import abstractmethod
from typing import List

# ** infra
from tiferet.interfaces import Service

# ** app
from ..domain import SymbolLookup

# *** interfaces

# ** interface: symbol_lookup_service
class SymbolLookupService(Service):
    '''
    Service interface for looking up symbols from a market data provider.
    '''

    # * method: lookup
    @abstractmethod
    def lookup(self, ids: List[str]) -> SymbolLookup:
        '''
        Look up each requested symbol id with the provider.

        :param ids: The requested symbol ids (tickers).
        :type ids: List[str]
        :return: The symbols by requested id, with warnings and failures.
        :rtype: SymbolLookup
        '''
        # Not implemented.
        raise NotImplementedError('lookup method is required for SymbolLookupService.')
