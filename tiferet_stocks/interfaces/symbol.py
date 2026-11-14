"""Tiferet Stocks Symbol Interfaces"""

# *** imports

# ** core
from abc import abstractmethod
from typing import Dict, List

# ** infra
from tiferet.interfaces import Service

# ** app
from ..domain import SymbolAlias
from ..mappers import SymbolLookup

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

# ** interface: symbol_alias_service
class SymbolAliasService(Service):
    '''
    Service interface for reading provider ticker aliases from symbol configuration.
    '''

    # * method: get_aliases
    @abstractmethod
    def get_aliases(self, provider: str) -> Dict[str, SymbolAlias]:
        '''
        Return the aliases for one provider, keyed by provider ticker.

        :param provider: The provider id, such as yahoo_chart.
        :type provider: str
        :return: The aliases for that provider, keyed by provider ticker.
        :rtype: Dict[str, SymbolAlias]
        '''

        # Not implemented.
        raise NotImplementedError('get_aliases method is required for SymbolAliasService.')
