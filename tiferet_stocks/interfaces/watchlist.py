"""Tiferet Stocks Watchlist Interfaces"""

# *** imports

# ** core
from abc import abstractmethod
from typing import List

# ** infra
from tiferet.interfaces import Service

# ** app
from tiferet_stocks.domain import Watchlist

# *** interfaces

# ** interface: watchlist_service
class WatchlistService(Service):
    '''
    Keeps watchlists independently of their backing file format.
    Ordering and change rules belong to the aggregate, not this contract.
    '''

    # * method: get
    @abstractmethod
    def get(self, id: str) -> Watchlist | None:
        '''
        Read one watchlist without changing stored data.

        :param id: The watchlist key.
        :type id: str
        :return: The watchlist, or None when missing.
        :rtype: Watchlist | None
        '''

        # Require an implementation from the configured repository.
        raise NotImplementedError('get method is required for WatchlistService.')

    # * method: list
    @abstractmethod
    def list(self) -> List[Watchlist]:
        '''
        Read all watchlists without changing stored data.

        :return: The stored watchlists.
        :rtype: List[Watchlist]
        '''

        # Require an implementation from the configured repository.
        raise NotImplementedError('list method is required for WatchlistService.')

    # * method: save
    @abstractmethod
    def save(self, watchlist: Watchlist) -> None:
        '''
        Create or replace one watchlist while preserving other documents.

        :param watchlist: The watchlist to persist.
        :type watchlist: Watchlist
        :return: None.
        :rtype: None
        '''

        # Require an implementation from the configured repository.
        raise NotImplementedError('save method is required for WatchlistService.')

    # * method: delete
    @abstractmethod
    def delete(self, id: str) -> None:
        '''
        Delete one watchlist; an absent key is an idempotent no-op.

        :param id: The watchlist key.
        :type id: str
        :return: None.
        :rtype: None
        '''

        # Require an implementation from the configured repository.
        raise NotImplementedError('delete method is required for WatchlistService.')
