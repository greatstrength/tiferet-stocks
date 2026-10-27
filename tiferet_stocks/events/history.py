"""Tiferet Stocks History Events"""

# *** imports

# ** core
from datetime import date
from typing import List

# ** infra
from tiferet.events import DomainEvent

# ** app
from .. import assets as a
from ..domain import PriceBar
from ..interfaces import PriceService

# *** events

# ** event: get_history
class GetHistory(DomainEvent):
    '''
    Domain event to get the daily price history for one symbol and date range.
    '''

    # * attribute: price_service
    price_service: PriceService

    # * init
    def __init__(self, price_service: PriceService) -> None:
        '''
        Initialize the event with the price service.

        :param price_service: The price service.
        :type price_service: PriceService
        '''

        # Store the injected price service.
        self.price_service = price_service

    # * method: execute
    @DomainEvent.parameters_required(['symbol', 'start', 'end'])
    def execute(self, symbol: str, start: str, end: str, **kwargs) -> List[PriceBar]:
        '''
        Get the daily bars, oldest first; a provider failure raises HISTORY_UNAVAILABLE.

        :param symbol: The requested symbol id (ticker).
        :type symbol: str
        :param start: The first day, as an ISO 8601 date (inclusive).
        :type start: str
        :param end: The last day, as an ISO 8601 date (inclusive).
        :type end: str
        :param kwargs: Additional keyword arguments.
        :type kwargs: dict
        :return: The bars within the range, oldest first; empty when the range has no trading days.
        :rtype: List[PriceBar]
        '''

        # Both dates must be ISO dates in YYYY-MM-DD form.
        try:
            first, last = date.fromisoformat(str(start)), date.fromisoformat(str(end))
        except ValueError:
            first = last = None
        self.verify(
            first is not None and (first.isoformat(), last.isoformat()) == (start, end),
            a.INVALID_HISTORY_RANGE_ID,
            start=start,
            end=end,
            detail='dates must be ISO 8601 dates (YYYY-MM-DD)',
        )

        # The range must not run backwards.
        self.verify(
            first <= last,
            a.INVALID_HISTORY_RANGE_ID,
            start=start,
            end=end,
            detail='the start date is after the end date',
        )

        # Get the history from the configured provider.
        history = self.price_service.get_history(symbol, first.isoformat(), last.isoformat())

        # Raise the catalogued error when the provider failed for the symbol.
        failure = history.failure
        self.verify(
            failure is None,
            a.HISTORY_UNAVAILABLE_ID,
            symbol=symbol,
            reason=failure.reason if failure else None,
            failure=failure.model_dump() if failure else None,
        )

        # Return the bars.
        return history.bars
