"""Tiferet Stocks Watchlist Mapper Tests"""

# *** imports

# ** infra
import pytest
from pydantic import ValidationError
from tiferet.domain import ModelError

# ** app
from tiferet_stocks.mappers import WatchlistAggregate, WatchlistConfigObject

# *** tests

# ** test: add_symbol_indices
@pytest.mark.parametrize('index, expected', [
    (None, ['SPY', 'QQQ', 'XLK']),
    (-1, ['SPY', 'QQQ', 'XLK']),
    (0, ['XLK', 'SPY', 'QQQ']),
    (1, ['SPY', 'XLK', 'QQQ']),
    (2, ['SPY', 'QQQ', 'XLK']),
    (20, ['SPY', 'QQQ', 'XLK']),
])
def test_add_symbol_indices(index: int | None, expected: list) -> None:
    '''
    Apply each insertion boundary without mutating the old list in place.

    :param index: The requested index, or None to exercise the default.
    :type index: int | None
    :param expected: The final symbol order.
    :type expected: list
    '''

    watchlist = WatchlistAggregate(id='etfs', name='ETFs', symbol_ids=['SPY', 'QQQ'])
    original = watchlist.symbol_ids

    if index is None:
        watchlist.add_symbol('XLK')
    else:
        watchlist.add_symbol('XLK', index=index)

    assert watchlist.symbol_ids == expected
    assert original == ['SPY', 'QQQ']
    assert original is not watchlist.symbol_ids

# ** test: move_symbol_indices
@pytest.mark.parametrize('symbol_id, index, expected', [
    ('SPY', None, ['QQQ', 'XLK', 'SPY']),
    ('SPY', -1, ['QQQ', 'XLK', 'SPY']),
    ('XLK', 0, ['XLK', 'SPY', 'QQQ']),
    ('SPY', 1, ['QQQ', 'SPY', 'XLK']),
    ('SPY', 2, ['QQQ', 'XLK', 'SPY']),
    ('SPY', 3, ['QQQ', 'XLK', 'SPY']),
    ('SPY', 30, ['QQQ', 'XLK', 'SPY']),
    ('QQQ', 1, ['SPY', 'QQQ', 'XLK']),
    ('XLK', 1, ['SPY', 'XLK', 'QQQ']),
])
def test_move_symbol_indices(symbol_id: str, index: int | None, expected: list) -> None:
    '''
    Make the index the final position regardless of movement direction.

    :param symbol_id: The existing symbol to move.
    :type symbol_id: str
    :param index: The requested index, or None to exercise the default.
    :type index: int | None
    :param expected: The final symbol order.
    :type expected: list
    '''

    watchlist = WatchlistAggregate(id='etfs', name='ETFs', symbol_ids=['SPY', 'QQQ', 'XLK'])
    original = watchlist.symbol_ids

    if index is None:
        watchlist.move_symbol(symbol_id)
    else:
        watchlist.move_symbol(symbol_id, to_index=index)

    assert watchlist.symbol_ids == expected
    assert original == ['SPY', 'QQQ', 'XLK']
    assert original is not watchlist.symbol_ids

# ** test: invalid_mutation_preserves_state
@pytest.mark.parametrize('method, kwargs, error_code', [
    ('add_symbol', {'symbol_id': 'SPY'}, 'WATCHLIST_SYMBOL_EXISTS'),
    ('add_symbol', {'symbol_id': 'XLK', 'index': -2}, 'WATCHLIST_INDEX_OUT_OF_RANGE'),
    ('add_symbol', {'symbol_id': 'XLK', 'index': -100}, 'WATCHLIST_INDEX_OUT_OF_RANGE'),
    ('remove_symbol', {'symbol_id': 'XLK'}, 'WATCHLIST_SYMBOL_NOT_FOUND'),
    ('move_symbol', {'symbol_id': 'XLK'}, 'WATCHLIST_SYMBOL_NOT_FOUND'),
    ('move_symbol', {'symbol_id': 'SPY', 'to_index': -2}, 'WATCHLIST_INDEX_OUT_OF_RANGE'),
])
def test_invalid_mutation_preserves_state(method: str, kwargs: dict, error_code: str) -> None:
    '''
    Model backstops name the defect and leave every field untouched.

    :param method: The aggregate mutator to call.
    :type method: str
    :param kwargs: The invalid request.
    :type kwargs: dict
    :param error_code: The expected model error code.
    :type error_code: str
    '''

    watchlist = WatchlistAggregate(id='etfs', name='ETFs', symbol_ids=['SPY', 'QQQ'])
    original = watchlist.model_dump()

    with pytest.raises(ModelError) as raised:
        getattr(watchlist, method)(**kwargs)

    assert raised.value.error_code == error_code
    assert raised.value.model['id'] == 'etfs'
    assert watchlist.model_dump() == original

# ** test: remove_symbol_copies_list
def test_remove_symbol_copies_list() -> None:
    '''
    Remove the chosen symbol and preserve the old list and remaining order.
    '''

    watchlist = WatchlistAggregate(id='etfs', name='ETFs', symbol_ids=['SPY', 'QQQ', 'XLK'])
    original = watchlist.symbol_ids

    watchlist.remove_symbol('QQQ')

    assert watchlist.symbol_ids == ['SPY', 'XLK']
    assert original == ['SPY', 'QQQ', 'XLK']
    assert watchlist.created_at is None
    assert watchlist.updated_at is None

# ** test: empty_and_single_symbol_boundaries
def test_empty_and_single_symbol_boundaries() -> None:
    '''
    Empty and single-symbol watchlists obey the same ordering rules.
    '''

    watchlist = WatchlistAggregate(id='etfs', name='ETFs')
    watchlist.add_symbol('SPY', index=20)
    watchlist.move_symbol('SPY', to_index=20)

    assert watchlist.symbol_ids == ['SPY']

    watchlist.remove_symbol('SPY')

    assert watchlist.symbol_ids == []

# ** test: settable_labels
@pytest.mark.parametrize('attribute, value', [('name', 'Renamed'), ('description', 'New description'), ('description', None)])
def test_settable_labels(attribute: str, value: str | None) -> None:
    '''
    Allow only the descriptive labels through the generic setter.

    :param attribute: The permitted label field.
    :type attribute: str
    :param value: The replacement value.
    :type value: str | None
    '''

    watchlist = WatchlistAggregate(id='etfs', name='ETFs')
    watchlist.set_attribute(attribute, value)

    assert getattr(watchlist, attribute) == value

# ** test: dedicated_fields_not_settable
@pytest.mark.parametrize('attribute, value', [
    ('id', 'changed'),
    ('symbol_ids', ['SPY']),
    ('created_at', '2026-11-06T14:00:00-07:00'),
    ('updated_at', '2026-11-06T14:00:00-07:00'),
    ('unknown', 'value'),
])
def test_dedicated_fields_not_settable(attribute: str, value) -> None:
    '''
    Reject identity, ordering and audit field changes through set_attribute.

    :param attribute: The disallowed field.
    :type attribute: str
    :param value: The replacement value.
    :type value: Any
    '''

    watchlist = WatchlistAggregate(id='etfs', name='ETFs')
    original = watchlist.model_dump()

    with pytest.raises(ModelError) as raised:
        watchlist.set_attribute(attribute, value)

    assert raised.value.error_code == 'ATTRIBUTE_NOT_SETTABLE'
    assert watchlist.model_dump() == original

# ** test: upsert_preserves_creation
def test_upsert_preserves_creation() -> None:
    '''
    Stamp both fields once, then update only the change timestamp.
    '''

    watchlist = WatchlistAggregate(id='etfs', name='ETFs')
    first = '2026-11-06T14:00:00-07:00'
    second = '2026-11-06T15:00:00-07:00'
    watchlist.upsert(at=first)

    assert watchlist.created_at == first
    assert watchlist.updated_at == first

    watchlist.upsert(at=second)

    assert watchlist.created_at == first
    assert watchlist.updated_at == second

# ** test: invalid_upsert_preserves_state
@pytest.mark.parametrize('created_at', [None, '2026-11-06T14:00:00-07:00'])
def test_invalid_upsert_preserves_state(created_at: str | None) -> None:
    '''
    Validate a timestamp before applying either audit field.

    :param created_at: An empty or previously stamped creation time.
    :type created_at: str | None
    '''

    watchlist = WatchlistAggregate(id='etfs', name='ETFs', created_at=created_at)
    original = watchlist.model_dump()

    with pytest.raises(ValidationError):
        watchlist.upsert(at='invalid')

    assert watchlist.model_dump() == original

# ** test: config_serialization_and_mapping
def test_config_serialization_and_mapping() -> None:
    '''
    Omit identity and None values while retaining empty strings and lists.
    '''

    config = WatchlistConfigObject(id='etfs', name='ETFs')
    data = config.to_primitive(role='to_data')

    assert data == {'name': 'ETFs', 'symbol_ids': []}
    assert WatchlistConfigObject._ROLES == {'to_model': {}, 'to_data': {'exclude': {'id'}}}

    mapped = config.map()
    assert isinstance(mapped, WatchlistAggregate)
    assert mapped.id == 'etfs'
    assert mapped.symbol_ids == []
    assert mapped.symbol_ids is not config.symbol_ids

    with_description = WatchlistConfigObject.from_model(mapped, description='')
    assert with_description.to_primitive(role='to_data')['description'] == ''

# ** test: config_round_trip
def test_config_round_trip() -> None:
    '''
    Preserve ordering, labels and stamps through a keyed document body.
    '''

    watchlist = WatchlistAggregate(id='etfs', name='ETFs', description='Broad ETFs', symbol_ids=['SPY', 'QQQ'])
    watchlist.upsert(at='2026-11-06T14:00:00-07:00')
    data = WatchlistConfigObject.from_model(watchlist).to_primitive(role='to_data')
    restored = WatchlistConfigObject(id='etfs', **data).map()

    assert 'id' not in data
    assert restored == watchlist
    assert restored.symbol_ids is not watchlist.symbol_ids
    assert WatchlistConfigObject(id='etfs', **data).map(name='Override').name == 'Override'
