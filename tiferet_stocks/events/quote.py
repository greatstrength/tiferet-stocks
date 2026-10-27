"""Tiferet Stocks Quote Events"""

# *** imports

# ** core
from typing import List

# ** infra
from tiferet.events import DomainEvent

# ** app
from .. import assets as a
from ..domain import Quotations
from ..interfaces import PriceService

# *** events

# ** event: get_quotes
class GetQuotes(DomainEvent):
    '''
    Domain event to get the latest quote for each requested symbol.
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
    @DomainEvent.parameters_required(['symbols'])
    def execute(self, symbols: List[str], **kwargs) -> Quotations:
        '''
        Get quotes; partial failure is data, and only a total failure raises QUOTES_UNAVAILABLE.

        :param symbols: The requested symbol ids (tickers).
        :type symbols: List[str]
        :param kwargs: Additional keyword arguments.
        :type kwargs: dict
        :return: The quotes by requested id, with symbols, warnings and failures.
        :rtype: Quotations
        '''

        # Treat a single id string as one id.
        if isinstance(symbols, str):
            symbols = [symbols]

        # Return empty quotations when no ids are requested.
        if not symbols:
            return Quotations()

        # Get the quotes from the configured provider.
        quotations = self.price_service.get_quotes(symbols)

        # Raise the catalogued error only when no symbol produced a quote.
        self.verify(
            bool(quotations.quotes),
            a.QUOTES_UNAVAILABLE_ID,
            symbols=', '.join(dict.fromkeys(symbols)),
            failures=[failure.model_dump() for failure in quotations.failures],
        )

        # Return the quotations.
        return quotations
