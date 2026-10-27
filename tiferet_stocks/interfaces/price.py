"""Tiferet Stocks Price Interfaces"""

# *** imports

# ** core
from abc import abstractmethod
from typing import List

# ** infra
from tiferet.interfaces import Service

# ** app
from ..mappers import PriceHistory, Quotations

# *** interfaces

# ** interface: price_service
class PriceService(Service):
    '''
    Service interface for reading prices from a market data provider.
    '''

    # * method: get_quotes
    @abstractmethod
    def get_quotes(self, symbols: List[str]) -> Quotations:
        '''
        Get the latest quote for each requested symbol id.

        :param symbols: The requested symbol ids (tickers).
        :type symbols: List[str]
        :return: The quotes by requested id, with symbols, warnings and failures.
        :rtype: Quotations
        '''
        # Not implemented.
        raise NotImplementedError('get_quotes method is required for PriceService.')

    # * method: get_history
    @abstractmethod
    def get_history(self, symbol: str, start: str, end: str) -> PriceHistory:
        '''
        Get the daily bars for one symbol between two ISO dates, inclusive, oldest first.

        :param symbol: The requested symbol id (ticker).
        :type symbol: str
        :param start: The first day, as an ISO 8601 date (inclusive).
        :type start: str
        :param end: The last day, as an ISO 8601 date (inclusive).
        :type end: str
        :return: The bars within the range, or the failure when the provider produced none.
        :rtype: PriceHistory
        '''

        # Not implemented.
        raise NotImplementedError('get_history method is required for PriceService.')
