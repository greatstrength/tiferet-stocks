"""Tiferet Stocks Watchlist Mappers"""

# *** imports

# ** core
from typing import Any, ClassVar, Dict

# ** infra
from tiferet.domain import ModelError
from tiferet.mappers import Aggregate, TransferObject

# ** app
from tiferet_stocks.domain.watchlist import Watchlist

# *** mappers

# ** mapper: watchlist_aggregate
class WatchlistAggregate(Watchlist, Aggregate):
    '''
    Applies predictable edits to the user's ordered symbol choices.
    Dedicated mutators own ordering and timestamps; only labels are settable.
    '''

    # * attribute: _SETTABLE_ATTRIBUTES
    _SETTABLE_ATTRIBUTES: ClassVar[set] = {'name', 'description'}

    # * method: add_symbol
    def add_symbol(self, symbol_id: str, index: int = -1) -> None:
        '''
        Insert a symbol, with -1 and positions beyond the end appending.

        :param symbol_id: The ticker to add.
        :type symbol_id: str
        :param index: The zero-based insertion position, or -1 for the end.
        :type index: int
        :return: None.
        :rtype: None
        '''

        # Keep model guards as backstops; events precheck catalogued outcomes.
        if symbol_id in self.symbol_ids:
            ModelError.raise_error('WATCHLIST_SYMBOL_EXISTS', message=f'Symbol already exists: {symbol_id}.', model=self)
        if index < -1:
            ModelError.raise_error('WATCHLIST_INDEX_OUT_OF_RANGE', message=f'Invalid watchlist index: {index}.', model=self)

        # Copy and reassign so field validation runs before state changes.
        symbols = list(self.symbol_ids)
        symbols.insert(len(symbols) if index == -1 else index, symbol_id)
        self.symbol_ids = symbols

    # * method: remove_symbol
    def remove_symbol(self, symbol_id: str) -> None:
        '''
        Remove one existing symbol without changing the remaining order.

        :param symbol_id: The ticker to remove.
        :type symbol_id: str
        :return: None.
        :rtype: None
        '''

        # Reject absent symbols before copying or changing state.
        if symbol_id not in self.symbol_ids:
            ModelError.raise_error('WATCHLIST_SYMBOL_NOT_FOUND', message=f'Symbol not found: {symbol_id}.', model=self)

        # Copy and reassign rather than mutating the list in place.
        symbols = list(self.symbol_ids)
        symbols.remove(symbol_id)
        self.symbol_ids = symbols

    # * method: move_symbol
    def move_symbol(self, symbol_id: str, to_index: int = -1) -> None:
        '''
        Move a symbol so it occupies the requested final position.

        :param symbol_id: The existing ticker to move.
        :type symbol_id: str
        :param to_index: The final zero-based position, or -1 for the end.
        :type to_index: int
        :return: None.
        :rtype: None
        '''

        # Reject invalid requests without removing the existing symbol.
        if symbol_id not in self.symbol_ids:
            ModelError.raise_error('WATCHLIST_SYMBOL_NOT_FOUND', message=f'Symbol not found: {symbol_id}.', model=self)
        if to_index < -1:
            ModelError.raise_error('WATCHLIST_INDEX_OUT_OF_RANGE', message=f'Invalid watchlist index: {to_index}.', model=self)

        # Insert after removal, so the index names the final position.
        symbols = list(self.symbol_ids)
        symbols.remove(symbol_id)
        symbols.insert(len(symbols) if to_index == -1 else to_index, symbol_id)
        self.symbol_ids = symbols

    # * method: upsert
    def upsert(self, at: str) -> None:
        '''
        Stamp a change, preserving an existing creation timestamp.

        :param at: The change timestamp in ISO 8601 with a UTC offset.
        :type at: str
        :return: None.
        :rtype: None
        '''

        # Validate both proposed values before assigning either timestamp.
        stamped = Watchlist.model_validate({
            **self.model_dump(),
            'created_at': self.created_at or at,
            'updated_at': at,
        })

        # Apply the validated values through ordinary assignment validation.
        self.created_at = stamped.created_at
        self.updated_at = stamped.updated_at

# ** mapper: watchlist_config_object
class WatchlistConfigObject(Watchlist, TransferObject):
    '''
    Carries watchlist data between configuration documents and aggregates.
    The document key owns identity, so stored bodies omit the id.
    '''

    # * attribute: _ROLES
    _ROLES: ClassVar[Dict[str, Dict[str, Any]]] = {
        'to_model': {},
        'to_data': {
            'exclude': {'id'},
        },
    }

    # * method: map
    def map(self, **overrides) -> WatchlistAggregate:
        '''
        Map the configuration data to a watchlist aggregate.

        :param overrides: Additional field overrides.
        :type overrides: dict
        :return: The mapped watchlist aggregate.
        :rtype: WatchlistAggregate
        '''

        # Delegate role serialization and override precedence to the framework.
        return super().map(WatchlistAggregate, **overrides)
