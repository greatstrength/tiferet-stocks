"""Tiferet Stocks Watchlist Events"""

# *** imports

# ** core
from datetime import datetime, timezone
from typing import List

# ** infra
from tiferet.events import DomainEvent

# ** app
from tiferet_stocks import assets as a
from tiferet_stocks.domain import Watchlist
from tiferet_stocks.interfaces import WatchlistService
from tiferet_stocks.mappers import WatchlistAggregate

# *** events

# ** event: watchlist_event
class WatchlistEvent(DomainEvent):
    '''
    Gives watchlist operations one storage boundary and an overridable clock.
    User-facing rules are checked before aggregate mutation or persistence.
    '''

    # * attribute: watchlist_service
    watchlist_service: WatchlistService

    # * init
    def __init__(self, watchlist_service: WatchlistService) -> None:
        '''
        Receive the configured watchlist service.

        :param watchlist_service: The watchlist persistence contract.
        :type watchlist_service: WatchlistService
        '''

        # Store the only injected dependency; no symbol lookup is needed.
        self.watchlist_service = watchlist_service

    # * method: now
    def now(self) -> str:
        '''
        Read the event clock as an offset-bearing ISO timestamp.

        :return: The current timestamp.
        :rtype: str
        '''

        # Use an aware clock, independent of the process time zone.
        return datetime.now(timezone.utc).isoformat()

    # * method: require_watchlist
    def require_watchlist(self, id: str) -> Watchlist:
        '''
        Resolve an existing watchlist before attempting any change.

        :param id: The watchlist key.
        :type id: str
        :return: The existing watchlist.
        :rtype: Watchlist
        '''

        # Existence is derived from get, without widening the service contract.
        watchlist = self.watchlist_service.get(id)
        self.verify(expression=watchlist is not None, error_code=a.error.WATCHLIST_NOT_FOUND_ID, id=id)

        # Return the unmodified service result.
        return watchlist

    # * method: persist
    def persist(self, watchlist: WatchlistAggregate, at: str | None = None) -> WatchlistAggregate:
        '''
        Stamp a private working aggregate and save it only after validation.

        :param watchlist: A newly constructed or copied aggregate.
        :type watchlist: WatchlistAggregate
        :param at: An explicit timestamp overriding the event clock.
        :type at: str | None
        :return: The saved aggregate.
        :rtype: WatchlistAggregate
        '''

        # Validate the explicit override rather than falling back on falsey input.
        watchlist.upsert(at=at if at is not None else self.now())

        # Save only after timestamp and aggregate validation succeed.
        self.watchlist_service.save(watchlist)
        return watchlist

# ** event: get_watchlist
class GetWatchlist(WatchlistEvent):
    '''
    Answers with one watchlist without changing its order or timestamps.
    '''

    # * method: execute
    @DomainEvent.parameters_required(['id'])
    def execute(self, id: str, **kwargs) -> Watchlist:
        '''
        Read one existing watchlist.

        :param id: The watchlist key.
        :type id: str
        :param kwargs: Additional feature parameters.
        :type kwargs: dict
        :return: The requested watchlist.
        :rtype: Watchlist
        '''

        # Read and verify without stamping or saving.
        return self.require_watchlist(id)

# ** event: list_watchlists
class ListWatchlists(WatchlistEvent):
    '''
    Answers with stored watchlists without creating or changing storage.
    '''

    # * method: execute
    def execute(self, **kwargs) -> List[Watchlist]:
        '''
        Read every watchlist.

        :param kwargs: Additional feature parameters.
        :type kwargs: dict
        :return: The stored watchlists.
        :rtype: List[Watchlist]
        '''

        # Delegate the read without invoking the event clock.
        return self.watchlist_service.list()

# ** event: create_watchlist
class CreateWatchlist(WatchlistEvent):
    '''
    Creates a named set of ordered symbol choices without looking them up.
    '''

    # * method: execute
    @DomainEvent.parameters_required(['id', 'name'])
    def execute(self,
                id: str,
                name: str,
                description: str | None = None,
                symbol_ids: List[str] | None = None,
                at: str | None = None,
                **kwargs) -> WatchlistAggregate:
        '''
        Create a watchlist after checking identity and repeated initial ids.

        :param id: The new watchlist key.
        :type id: str
        :param name: The display name.
        :type name: str
        :param description: An optional description.
        :type description: str | None
        :param symbol_ids: Initial tickers in user-chosen order.
        :type symbol_ids: List[str] | None
        :param at: An optional timestamp override.
        :type at: str | None
        :param kwargs: Additional feature parameters.
        :type kwargs: dict
        :return: The created watchlist.
        :rtype: WatchlistAggregate
        '''

        # Reject a taken key before constructing or persisting an aggregate.
        self.verify(expression=self.watchlist_service.get(id) is None, error_code=a.error.WATCHLIST_EXISTS_ID, id=id)

        # Reject repeated initial ids through the error catalog, not model validation.
        symbols = list(symbol_ids) if symbol_ids is not None else []
        seen = set()
        for symbol_id in symbols:
            self.verify(expression=symbol_id not in seen, error_code=a.error.WATCHLIST_SYMBOL_EXISTS_ID, id=id, symbol_id=symbol_id)
            seen.add(symbol_id)

        # Construct a fresh aggregate and stamp only this new instance.
        watchlist = WatchlistAggregate(id=id, name=name, description=description, symbol_ids=symbols)
        return self.persist(watchlist, at=at)

# ** event: update_watchlist
class UpdateWatchlist(WatchlistEvent):
    '''
    Changes watchlist labels without changing its identity or symbol choices.
    '''

    # * method: execute
    @DomainEvent.parameters_required(['id'])
    def execute(self,
                id: str,
                name: str | None = None,
                description: str | None = None,
                at: str | None = None,
                **kwargs) -> WatchlistAggregate:
        '''
        Update supplied labels and stamp the change.

        :param id: The existing watchlist key.
        :type id: str
        :param name: The replacement name, when supplied.
        :type name: str | None
        :param description: The replacement description, when supplied.
        :type description: str | None
        :param at: An optional timestamp override.
        :type at: str | None
        :param kwargs: Additional feature parameters.
        :type kwargs: dict
        :return: The updated watchlist.
        :rtype: WatchlistAggregate
        '''

        # Copy the service result so failed updates cannot mutate shared objects.
        existing = self.require_watchlist(id)
        watchlist = WatchlistAggregate.model_validate(existing.model_dump())

        # Apply only supplied labels through the aggregate allow-list.
        if name is not None:
            watchlist.set_attribute('name', name)
        if description is not None:
            watchlist.set_attribute('description', description)

        # Stamp and persist the private copy after all label changes succeed.
        return self.persist(watchlist, at=at)

# ** event: delete_watchlist
class DeleteWatchlist(WatchlistEvent):
    '''
    Removes one existing watchlist while leaving the others alone.
    '''

    # * method: execute
    @DomainEvent.parameters_required(['id'])
    def execute(self, id: str, **kwargs) -> str:
        '''
        Delete a known watchlist without invoking the clock or upsert.

        :param id: The watchlist key.
        :type id: str
        :param kwargs: Additional feature parameters.
        :type kwargs: dict
        :return: The deleted watchlist key.
        :rtype: str
        '''

        # Verify existence before the repository's idempotent delete.
        self.require_watchlist(id)
        self.watchlist_service.delete(id)

        # Return the identifier rather than an empty success response.
        return id

# ** event: add_watchlist_symbol
class AddWatchlistSymbol(WatchlistEvent):
    '''
    Applies one ordered-symbol change without fetching market data.
    '''

    # * method: execute
    @DomainEvent.parameters_required(['id', 'symbol_id'])
    def execute(self,
                id: str,
                symbol_id: str,
                index: int = -1,
                at: str | None = None,
                **kwargs) -> WatchlistAggregate:
        '''
        Check the change before calling the aggregate and saving a copy.

        :param id: The existing watchlist key.
        :type id: str
        :param symbol_id: The ticker to change.
        :type symbol_id: str
        :param index: The final zero-based position, or -1 for the end.
        :type index: int
        :param at: An optional timestamp override.
        :type at: str | None
        :param kwargs: Additional feature parameters.
        :type kwargs: dict
        :return: The changed watchlist.
        :rtype: WatchlistAggregate
        '''

        # Precheck catalogued outcomes against the unchanged service result.
        existing = self.require_watchlist(id)
        self.verify(expression=symbol_id not in existing.symbol_ids, error_code=a.error.WATCHLIST_SYMBOL_EXISTS_ID, id=id, symbol_id=symbol_id)
        self.verify(expression=index >= -1, error_code=a.error.WATCHLIST_INDEX_OUT_OF_RANGE_ID, id=id, index=index)

        # Work on a private copy so a later validation failure cannot leak edits.
        watchlist = WatchlistAggregate.model_validate(existing.model_dump())
        watchlist.add_symbol(symbol_id, index=index)

        # Validate the stamp and persist only the completed change.
        return self.persist(watchlist, at=at)

# ** event: remove_watchlist_symbol
class RemoveWatchlistSymbol(WatchlistEvent):
    '''
    Applies one ordered-symbol change without fetching market data.
    '''

    # * method: execute
    @DomainEvent.parameters_required(['id', 'symbol_id'])
    def execute(self,
                id: str,
                symbol_id: str,
                at: str | None = None,
                **kwargs) -> WatchlistAggregate:
        '''
        Check the change before calling the aggregate and saving a copy.

        :param id: The existing watchlist key.
        :type id: str
        :param symbol_id: The ticker to change.
        :type symbol_id: str
        :param at: An optional timestamp override.
        :type at: str | None
        :param kwargs: Additional feature parameters.
        :type kwargs: dict
        :return: The changed watchlist.
        :rtype: WatchlistAggregate
        '''

        # Precheck catalogued outcomes against the unchanged service result.
        existing = self.require_watchlist(id)
        self.verify(expression=symbol_id in existing.symbol_ids, error_code=a.error.WATCHLIST_SYMBOL_NOT_FOUND_ID, id=id, symbol_id=symbol_id)

        # Work on a private copy so a later validation failure cannot leak edits.
        watchlist = WatchlistAggregate.model_validate(existing.model_dump())
        watchlist.remove_symbol(symbol_id)

        # Validate the stamp and persist only the completed change.
        return self.persist(watchlist, at=at)

# ** event: move_watchlist_symbol
class MoveWatchlistSymbol(WatchlistEvent):
    '''
    Applies one ordered-symbol change without fetching market data.
    '''

    # * method: execute
    @DomainEvent.parameters_required(['id', 'symbol_id'])
    def execute(self,
                id: str,
                symbol_id: str,
                to_index: int = -1,
                at: str | None = None,
                **kwargs) -> WatchlistAggregate:
        '''
        Check the change before calling the aggregate and saving a copy.

        :param id: The existing watchlist key.
        :type id: str
        :param symbol_id: The ticker to change.
        :type symbol_id: str
        :param to_index: The final zero-based position, or -1 for the end.
        :type to_index: int
        :param at: An optional timestamp override.
        :type at: str | None
        :param kwargs: Additional feature parameters.
        :type kwargs: dict
        :return: The changed watchlist.
        :rtype: WatchlistAggregate
        '''

        # Precheck catalogued outcomes against the unchanged service result.
        existing = self.require_watchlist(id)
        self.verify(expression=symbol_id in existing.symbol_ids, error_code=a.error.WATCHLIST_SYMBOL_NOT_FOUND_ID, id=id, symbol_id=symbol_id)
        self.verify(expression=to_index >= -1, error_code=a.error.WATCHLIST_INDEX_OUT_OF_RANGE_ID, id=id, index=to_index)

        # Work on a private copy so a later validation failure cannot leak edits.
        watchlist = WatchlistAggregate.model_validate(existing.model_dump())
        watchlist.move_symbol(symbol_id, to_index=to_index)

        # Validate the stamp and persist only the completed change.
        return self.persist(watchlist, at=at)
