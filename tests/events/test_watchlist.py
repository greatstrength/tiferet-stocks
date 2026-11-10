"""Tiferet Stocks Watchlist Event Tests"""

# *** imports

# ** core
from datetime import datetime
from unittest import mock

# ** infra
import pytest
from pydantic import ValidationError
from tiferet import TiferetError, use_tester
from tiferet.events import DomainEvent

# ** app
from tiferet_stocks.events import (
    WatchlistEvent,
    GetWatchlist,
    ListWatchlists,
    CreateWatchlist,
    UpdateWatchlist,
    DeleteWatchlist,
    AddWatchlistSymbol,
    RemoveWatchlistSymbol,
    MoveWatchlistSymbol,
)
from tiferet_stocks.interfaces import WatchlistService
from tiferet_stocks.mappers import WatchlistAggregate

# *** constants

# ** constant: watchlist_dependencies
WATCHLIST_DEPENDENCIES = {
    'watchlist_service': {
        'module_path': 'tiferet_stocks.interfaces',
        'class_name': 'WatchlistService',
    },
}

# *** fixtures

# ** fixture: service
@pytest.fixture
def service() -> mock.Mock:
    '''
    Provide a shared object so hidden mutation cannot hide behind repository copies.
    '''

    service = mock.Mock(spec=WatchlistService)
    watchlist = WatchlistAggregate(id='one', name='One', symbol_ids=['SPY', 'QQQ'])
    watchlist.upsert(at='2026-11-06T14:00:00-07:00')
    service.get.return_value = watchlist
    service.list.return_value = [watchlist]
    return service

# *** tests

# ** test: rejected_changes_precheck_before_aggregate
@pytest.mark.parametrize('event, data, missing, code', [
    (GetWatchlist, {'id': 'missing'}, True, 'WATCHLIST_NOT_FOUND'),
    (CreateWatchlist, {'id': 'one', 'name': 'New'}, False, 'WATCHLIST_EXISTS'),
    (CreateWatchlist, {'id': 'new', 'name': 'New', 'symbol_ids': ['SPY', 'SPY']}, True, 'WATCHLIST_SYMBOL_EXISTS'),
    (UpdateWatchlist, {'id': 'missing', 'name': 'New'}, True, 'WATCHLIST_NOT_FOUND'),
    (DeleteWatchlist, {'id': 'missing'}, True, 'WATCHLIST_NOT_FOUND'),
    (AddWatchlistSymbol, {'id': 'missing', 'symbol_id': 'XLK'}, True, 'WATCHLIST_NOT_FOUND'),
    (RemoveWatchlistSymbol, {'id': 'missing', 'symbol_id': 'SPY'}, True, 'WATCHLIST_NOT_FOUND'),
    (MoveWatchlistSymbol, {'id': 'missing', 'symbol_id': 'SPY'}, True, 'WATCHLIST_NOT_FOUND'),
    (AddWatchlistSymbol, {'id': 'one', 'symbol_id': 'SPY'}, False, 'WATCHLIST_SYMBOL_EXISTS'),
    (AddWatchlistSymbol, {'id': 'one', 'symbol_id': 'XLK', 'index': -2}, False, 'WATCHLIST_INDEX_OUT_OF_RANGE'),
    (RemoveWatchlistSymbol, {'id': 'one', 'symbol_id': 'XLK'}, False, 'WATCHLIST_SYMBOL_NOT_FOUND'),
    (MoveWatchlistSymbol, {'id': 'one', 'symbol_id': 'XLK'}, False, 'WATCHLIST_SYMBOL_NOT_FOUND'),
    (MoveWatchlistSymbol, {'id': 'one', 'symbol_id': 'SPY', 'to_index': -2}, False, 'WATCHLIST_INDEX_OUT_OF_RANGE'),
])
def test_rejected_changes_precheck_before_aggregate(service: mock.Mock,
                                                   event: type,
                                                   data: dict,
                                                   missing: bool,
                                                   code: str) -> None:
    '''
    Reject domain outcomes before aggregate construction, mutation or save.

    :param service: The mock storage boundary.
    :type service: mock.Mock
    :param event: The event type under test.
    :type event: type
    :param data: The invalid request.
    :type data: dict
    :param missing: Whether the service returns no existing watchlist.
    :type missing: bool
    :param code: The expected catalogued error id.
    :type code: str
    '''

    original = service.get.return_value
    original_data = original.model_dump()
    if missing:
        service.get.return_value = None

    with mock.patch('tiferet_stocks.events.watchlist.WatchlistAggregate') as aggregate:
        aggregate.side_effect = AssertionError('aggregate constructed before precheck')
        aggregate.model_validate.side_effect = AssertionError('aggregate copied before precheck')
        with pytest.raises(TiferetError) as raised:
            DomainEvent.handle(event, dependencies={'watchlist_service': service}, **data)

    assert raised.value.error_code == code
    aggregate.assert_not_called()
    aggregate.model_validate.assert_not_called()
    service.save.assert_not_called()
    service.delete.assert_not_called()
    assert original.model_dump() == original_data

# ** test: changes_stamp_private_copy
@pytest.mark.parametrize('event, data, expected_ids', [
    (UpdateWatchlist, {'id': 'one', 'name': 'Renamed'}, ['SPY', 'QQQ']),
    (AddWatchlistSymbol, {'id': 'one', 'symbol_id': 'XLK'}, ['SPY', 'QQQ', 'XLK']),
    (RemoveWatchlistSymbol, {'id': 'one', 'symbol_id': 'SPY'}, ['QQQ']),
    (MoveWatchlistSymbol, {'id': 'one', 'symbol_id': 'SPY'}, ['QQQ', 'SPY']),
])
@pytest.mark.parametrize('at', [None, '2026-11-06T15:00:00-07:00'])
def test_changes_stamp_private_copy(service: mock.Mock,
                                    event: type,
                                    data: dict,
                                    expected_ids: list,
                                    at: str | None) -> None:
    '''
    Successful changes save a stamped copy without mutating service-held state.

    :param service: The mock storage boundary.
    :type service: mock.Mock
    :param event: The change event type.
    :type event: type
    :param data: The valid request.
    :type data: dict
    :param expected_ids: The resulting ordered ids.
    :type expected_ids: list
    :param at: An optional timestamp override.
    :type at: str | None
    '''

    original = service.get.return_value
    original_data = original.model_dump()
    clock_time = '2026-11-06T22:00:00+00:00'

    with mock.patch.object(WatchlistEvent, 'now', return_value=clock_time) as clock:
        result = DomainEvent.handle(event, dependencies={'watchlist_service': service}, at=at, **data)

    assert result.symbol_ids == expected_ids
    assert result.created_at == original.created_at
    assert result.updated_at == (at if at is not None else clock_time)
    assert clock.call_count == (1 if at is None else 0)
    assert result is not original
    assert original.model_dump() == original_data
    service.save.assert_called_once_with(result)

# ** test: invalid_stamp_does_not_leak_changes
@pytest.mark.parametrize('event, data', [
    (UpdateWatchlist, {'id': 'one', 'name': 'Changed', 'description': 'Changed'}),
    (AddWatchlistSymbol, {'id': 'one', 'symbol_id': 'XLK'}),
    (RemoveWatchlistSymbol, {'id': 'one', 'symbol_id': 'SPY'}),
    (MoveWatchlistSymbol, {'id': 'one', 'symbol_id': 'SPY'}),
])
def test_invalid_stamp_does_not_leak_changes(service: mock.Mock, event: type, data: dict) -> None:
    '''
    Failed timestamps leave both storage and shared service objects unchanged.

    :param service: The mock storage boundary.
    :type service: mock.Mock
    :param event: The change event type.
    :type event: type
    :param data: The otherwise valid request.
    :type data: dict
    '''

    original = service.get.return_value.model_dump()

    with pytest.raises(ValidationError):
        DomainEvent.handle(event, dependencies={'watchlist_service': service}, at='invalid', **data)

    service.save.assert_not_called()
    assert service.get.return_value.model_dump() == original

# ** test: create_uses_clock_or_override
@pytest.mark.parametrize('at', [None, '2026-11-06T15:00:00-07:00'])
def test_create_uses_clock_or_override(service: mock.Mock, at: str | None) -> None:
    '''
    New watchlists stamp both fields from the clock or explicit override.

    :param service: The mock storage boundary.
    :type service: mock.Mock
    :param at: An optional explicit timestamp.
    :type at: str | None
    '''

    service.get.return_value = None
    clock_time = '2026-11-06T21:00:00+00:00'
    with mock.patch.object(WatchlistEvent, 'now', return_value=clock_time) as clock:
        result = DomainEvent.handle(CreateWatchlist, dependencies={'watchlist_service': service}, id='new', name='New', at=at)

    assert result.created_at == (at if at is not None else clock_time)
    assert result.updated_at == result.created_at
    assert result.symbol_ids == []
    assert clock.call_count == (1 if at is None else 0)
    service.save.assert_called_once_with(result)

# ** test: read_and_delete_do_not_stamp
@pytest.mark.parametrize('event, data', [
    (GetWatchlist, {'id': 'one'}),
    (ListWatchlists, {}),
    (DeleteWatchlist, {'id': 'one'}),
])
def test_read_and_delete_do_not_stamp(service: mock.Mock, event: type, data: dict) -> None:
    '''
    Reads and deletion neither invoke the clock nor modify timestamps.

    :param service: The mock storage boundary.
    :type service: mock.Mock
    :param event: The event type.
    :type event: type
    :param data: The request parameters.
    :type data: dict
    '''

    original = service.get.return_value.model_dump()
    with mock.patch.object(WatchlistEvent, 'now', side_effect=AssertionError('clock used')):
        with mock.patch.object(WatchlistAggregate, 'upsert', side_effect=AssertionError('upsert used')):
            result = DomainEvent.handle(event, dependencies={'watchlist_service': service}, **data)

    assert result is not None
    assert service.get.return_value.model_dump() == original
    service.save.assert_not_called()
    assert service.delete.call_count == (1 if event is DeleteWatchlist else 0)

# ** test: default_clock_has_offset
def test_default_clock_has_offset(service: mock.Mock) -> None:
    '''
    The real event clock returns a valid offset-bearing ISO timestamp.

    :param service: The mock storage boundary.
    :type service: mock.Mock
    '''

    timestamp = WatchlistEvent(service).now()

    assert datetime.fromisoformat(timestamp).utcoffset() is not None

# *** testers

# ** tester: test_get_watchlist
@use_tester(
    type='domain_event',
    target_cls=GetWatchlist,
    dependencies=WATCHLIST_DEPENDENCIES,
    sample_kwargs={'id': 'one'},
    required_params=['id'],
)
class TestGetWatchlist:
    '''
    Bind GetWatchlist to the released event tester and service contract.
    '''

    # * test: missing_required_params
    def test_missing_required_params(self, test_ctx, session):
        '''
        Require each declared input before an event may reach the repository.

        :param test_ctx: The bound event assertion context.
        :type test_ctx: DomainEventTesterContext
        :param session: The released test session.
        :type session: TestSessionContext
        :return: None.
        :rtype: None
        '''

        # The nonempty contract exercises every required parameter through handle.
        test_ctx.assert_missing_required_params()

# ** tester: test_list_watchlists
@use_tester(
    type='domain_event',
    target_cls=ListWatchlists,
    dependencies=WATCHLIST_DEPENDENCIES,
    sample_kwargs={},
    required_params=[],
)
class TestListWatchlists:
    '''
    Bind ListWatchlists to the released event tester and service contract.
    '''

    # * test: list_with_injected_service
    def test_list_with_injected_service(self, test_ctx, session):
        '''
        Execute the parameter-free event with the tester's real spec dependency.

        :param test_ctx: The bound event assertion context.
        :type test_ctx: DomainEventTesterContext
        :param session: The released test session.
        :type session: TestSessionContext
        :return: None.
        :rtype: None
        '''

        # Build the declared service spec and supply an ordered, populated answer.
        dependencies = test_ctx.mock_dependencies()
        service = dependencies['watchlist_service']
        watchlist = WatchlistAggregate(id='one', name='One', symbol_ids=['SPY', 'QQQ'])
        service.list.return_value = [watchlist]

        # Exercise handle rather than the empty required-parameter assertion.
        result = test_ctx.handle(dependencies=dependencies)

        # Lock actual delegation and read-only behavior of the injected service.
        assert result == [watchlist]
        service.list.assert_called_once_with()
        service.get.assert_not_called()
        service.save.assert_not_called()
        service.delete.assert_not_called()

# ** tester: test_create_watchlist
@use_tester(
    type='domain_event',
    target_cls=CreateWatchlist,
    dependencies=WATCHLIST_DEPENDENCIES,
    sample_kwargs={'id': 'new', 'name': 'New', 'symbol_ids': ['SPY', 'QQQ']},
    required_params=['id', 'name'],
)
class TestCreateWatchlist:
    '''
    Bind CreateWatchlist to the released event tester and service contract.
    '''

    # * test: missing_required_params
    def test_missing_required_params(self, test_ctx, session):
        '''
        Require each declared input before an event may reach the repository.

        :param test_ctx: The bound event assertion context.
        :type test_ctx: DomainEventTesterContext
        :param session: The released test session.
        :type session: TestSessionContext
        :return: None.
        :rtype: None
        '''

        # The nonempty contract exercises every required parameter through handle.
        test_ctx.assert_missing_required_params()

# ** tester: test_update_watchlist
@use_tester(
    type='domain_event',
    target_cls=UpdateWatchlist,
    dependencies=WATCHLIST_DEPENDENCIES,
    sample_kwargs={'id': 'one', 'name': 'Renamed'},
    required_params=['id'],
)
class TestUpdateWatchlist:
    '''
    Bind UpdateWatchlist to the released event tester and service contract.
    '''

    # * test: missing_required_params
    def test_missing_required_params(self, test_ctx, session):
        '''
        Require each declared input before an event may reach the repository.

        :param test_ctx: The bound event assertion context.
        :type test_ctx: DomainEventTesterContext
        :param session: The released test session.
        :type session: TestSessionContext
        :return: None.
        :rtype: None
        '''

        # The nonempty contract exercises every required parameter through handle.
        test_ctx.assert_missing_required_params()

# ** tester: test_delete_watchlist
@use_tester(
    type='domain_event',
    target_cls=DeleteWatchlist,
    dependencies=WATCHLIST_DEPENDENCIES,
    sample_kwargs={'id': 'one'},
    required_params=['id'],
)
class TestDeleteWatchlist:
    '''
    Bind DeleteWatchlist to the released event tester and service contract.
    '''

    # * test: missing_required_params
    def test_missing_required_params(self, test_ctx, session):
        '''
        Require each declared input before an event may reach the repository.

        :param test_ctx: The bound event assertion context.
        :type test_ctx: DomainEventTesterContext
        :param session: The released test session.
        :type session: TestSessionContext
        :return: None.
        :rtype: None
        '''

        # The nonempty contract exercises every required parameter through handle.
        test_ctx.assert_missing_required_params()

# ** tester: test_add_watchlist_symbol
@use_tester(
    type='domain_event',
    target_cls=AddWatchlistSymbol,
    dependencies=WATCHLIST_DEPENDENCIES,
    sample_kwargs={'id': 'one', 'symbol_id': 'XLK'},
    required_params=['id', 'symbol_id'],
)
class TestAddWatchlistSymbol:
    '''
    Bind AddWatchlistSymbol to the released event tester and service contract.
    '''

    # * test: missing_required_params
    def test_missing_required_params(self, test_ctx, session):
        '''
        Require each declared input before an event may reach the repository.

        :param test_ctx: The bound event assertion context.
        :type test_ctx: DomainEventTesterContext
        :param session: The released test session.
        :type session: TestSessionContext
        :return: None.
        :rtype: None
        '''

        # The nonempty contract exercises every required parameter through handle.
        test_ctx.assert_missing_required_params()

# ** tester: test_remove_watchlist_symbol
@use_tester(
    type='domain_event',
    target_cls=RemoveWatchlistSymbol,
    dependencies=WATCHLIST_DEPENDENCIES,
    sample_kwargs={'id': 'one', 'symbol_id': 'SPY'},
    required_params=['id', 'symbol_id'],
)
class TestRemoveWatchlistSymbol:
    '''
    Bind RemoveWatchlistSymbol to the released event tester and service contract.
    '''

    # * test: missing_required_params
    def test_missing_required_params(self, test_ctx, session):
        '''
        Require each declared input before an event may reach the repository.

        :param test_ctx: The bound event assertion context.
        :type test_ctx: DomainEventTesterContext
        :param session: The released test session.
        :type session: TestSessionContext
        :return: None.
        :rtype: None
        '''

        # The nonempty contract exercises every required parameter through handle.
        test_ctx.assert_missing_required_params()

# ** tester: test_move_watchlist_symbol
@use_tester(
    type='domain_event',
    target_cls=MoveWatchlistSymbol,
    dependencies=WATCHLIST_DEPENDENCIES,
    sample_kwargs={'id': 'one', 'symbol_id': 'SPY'},
    required_params=['id', 'symbol_id'],
)
class TestMoveWatchlistSymbol:
    '''
    Bind MoveWatchlistSymbol to the released event tester and service contract.
    '''

    # * test: missing_required_params
    def test_missing_required_params(self, test_ctx, session):
        '''
        Require each declared input before an event may reach the repository.

        :param test_ctx: The bound event assertion context.
        :type test_ctx: DomainEventTesterContext
        :param session: The released test session.
        :type session: TestSessionContext
        :return: None.
        :rtype: None
        '''

        # The nonempty contract exercises every required parameter through handle.
        test_ctx.assert_missing_required_params()
