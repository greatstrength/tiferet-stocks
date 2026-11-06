"""Tiferet Stocks Watchlist Domain Tests"""

# *** imports

# ** infra
import pytest
from pydantic import ValidationError

# ** app
from tiferet_stocks.domain import Watchlist

# *** tests

# ** test: watchlist_fields_and_defaults
def test_watchlist_fields_and_defaults() -> None:
    '''
    Keep exactly the six specified fields and independent ordered lists.
    '''

    first = Watchlist(id='one', name='One')
    second = Watchlist(id='two', name='Two')

    assert set(Watchlist.model_fields) == {'id', 'name', 'description', 'created_at', 'updated_at', 'symbol_ids'}
    assert first.description is None
    assert first.created_at is None
    assert first.updated_at is None
    assert first.symbol_ids == []
    assert first.symbol_ids is not second.symbol_ids

# ** test: watchlist_rejects_invalid_structure
@pytest.mark.parametrize('overrides', [
    {'symbol_ids': ['SPY', 'SPY']},
    {'icon': 'star'},
    {'created_at': '2026-11-06T14:00:00'},
    {'updated_at': 'not-a-timestamp'},
])
def test_watchlist_rejects_invalid_structure(overrides: dict) -> None:
    '''
    Reject duplicate ids, extra fields and invalid or offset-free timestamps.

    :param overrides: Invalid field values.
    :type overrides: dict
    '''

    with pytest.raises(ValidationError):
        Watchlist(id='etfs', name='ETFs', **overrides)

# ** test: watchlist_preserves_timestamp_offsets
@pytest.mark.parametrize('timestamp', ['2026-11-06T14:00:00-07:00', '2026-11-06T21:00:00+00:00', '2026-11-06T21:00:00Z'])
def test_watchlist_preserves_timestamp_offsets(timestamp: str) -> None:
    '''
    Validate timestamps without rewriting a caller's chosen UTC offset.

    :param timestamp: An ISO timestamp with an offset.
    :type timestamp: str
    '''

    watchlist = Watchlist(id='etfs', name='ETFs', created_at=timestamp, updated_at=timestamp)

    assert watchlist.created_at == timestamp
    assert watchlist.updated_at == timestamp

# ** test: watchlist_assignment_validation
def test_watchlist_assignment_validation() -> None:
    '''
    Field assignment rejects duplicates without replacing the original list.
    '''

    watchlist = Watchlist(id='etfs', name='ETFs', symbol_ids=['SPY', 'QQQ'])

    with pytest.raises(ValidationError):
        watchlist.symbol_ids = ['SPY', 'SPY']

    assert watchlist.symbol_ids == ['SPY', 'QQQ']
