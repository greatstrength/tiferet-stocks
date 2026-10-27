"""Tiferet Stocks Price Interfaces"""

# *** imports

# ** core
from abc import abstractmethod
from typing import List

# ** infra
from tiferet.interfaces import Service

# ** app
from ..domain import QuoteSet

# *** interfaces

# ** interface: price_service
class PriceService(Service):
    '''
    Service interface for reading prices from a market data provider.
    '''

    # * method: get_quotes
    @abstractmethod
    def get_quotes(self, symbols: List[str]) -> QuoteSet:
        '''
        Get the latest quote for each requested symbol id.

        :param symbols: The requested symbol ids (tickers).
        :type symbols: List[str]
        :return: The quotes by requested id, with symbols, warnings and failures.
        :rtype: QuoteSet
        '''
        # Not implemented.
        raise NotImplementedError('get_quotes method is required for PriceService.')
