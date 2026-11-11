"""Tiferet Stocks Watchlist Domain Models"""

# *** imports

# ** core
from datetime import datetime
from typing import List

# ** infra
from pydantic import Field, field_validator
from tiferet.domain import DomainObject

# *** models

# ** model: watchlist
class Watchlist(DomainObject):
    '''
    Keeps the user's ordered symbol choices without storing market data.
    Creation and change times describe the watchlist, not its symbols.
    '''

    # * attribute: id
    id: str = Field(..., description='The watchlist document key.')

    # * attribute: name
    name: str = Field(..., description='The watchlist display name.')

    # * attribute: description
    description: str | None = Field(default=None, description='An optional description.')

    # * attribute: created_at
    created_at: str | None = Field(default=None, description='The creation time in ISO 8601 with a UTC offset.')

    # * attribute: updated_at
    updated_at: str | None = Field(default=None, description='The last change time in ISO 8601 with a UTC offset.')

    # * attribute: symbol_ids
    symbol_ids: List[str] = Field(default_factory=list, description='Unique tickers in the user-chosen order.')

    # * method: validate_symbol_ids (validator)
    @field_validator('symbol_ids')
    @classmethod
    def validate_symbol_ids(cls, value: List[str]) -> List[str]:
        '''
        Reject repeated symbol ids without changing their order.

        :param value: The validated symbol ids.
        :type value: List[str]
        :return: The ordered, unique symbol ids.
        :rtype: List[str]
        '''

        # Keep uniqueness as a structural invariant on construction and assignment.
        if len(value) != len(set(value)):
            raise ValueError('Watchlist symbol ids must be unique.')

        # Return the original order.
        return value

    # * method: validate_timestamp (validator)
    @field_validator('created_at', 'updated_at')
    @classmethod
    def validate_timestamp(cls, value: str | None) -> str | None:
        '''
        Require a UTC offset whenever a timestamp is present.

        :param value: The optional ISO timestamp.
        :type value: str | None
        :return: The timestamp without normalization.
        :rtype: str | None
        '''

        # Leave an unstamped watchlist empty until its first upsert.
        if value is None:
            return value

        # Parse only for validation; preserve the caller's offset and spelling.
        # Python 3.10 rejects a trailing Z, so map it to +00:00 for the check only.
        check_value = value[:-1] + '+00:00' if value.endswith('Z') else value
        timestamp = datetime.fromisoformat(check_value)
        if timestamp.utcoffset() is None:
            raise ValueError('Watchlist timestamps must include a UTC offset.')

        # Return the original timestamp.
        return value
