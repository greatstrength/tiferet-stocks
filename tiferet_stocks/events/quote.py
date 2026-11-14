"""Tiferet Stocks Quote Events"""

# *** imports

# ** core
from typing import List

# ** infra
from tiferet.events import DomainEvent

# ** app
from .. import assets as a
from ..domain import (
    YAHOO_CHART,
    Quotations,
    rekey_map,
    rekey_symbol_id,
    rekey_symbol_ids,
    to_provider_tickers,
)
from ..interfaces import PriceService, SymbolAliasService
from .symbol import apply_symbol_alias

# *** events

# ** event: get_quotes
class GetQuotes(DomainEvent):
    '''
    Domain event to get the latest quote for each requested symbol.
    '''

    # * attribute: price_service
    price_service: PriceService

    # * attribute: symbol_alias_service
    symbol_alias_service: SymbolAliasService

    # * init
    def __init__(self, price_service: PriceService, symbol_alias_service: SymbolAliasService) -> None:
        '''
        Initialize the event with the price and symbol alias services.

        :param price_service: The price service.
        :type price_service: PriceService
        :param symbol_alias_service: The symbol alias service.
        :type symbol_alias_service: SymbolAliasService
        '''

        # Store the injected services.
        self.price_service = price_service
        self.symbol_alias_service = symbol_alias_service

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

        # Get the quotes from the configured provider under the provider tickers; an id with no alias passes through.
        aliases = self.symbol_alias_service.get_aliases(YAHOO_CHART)
        provided = self.price_service.get_quotes(to_provider_tickers(symbols, aliases))

        # Re-key every part of the answer to the canonical ids.
        quotations = Quotations(
            quotes={symbol_id: rekey_symbol_id(quote, aliases) for symbol_id, quote in rekey_map(provided.quotes, aliases).items()},
            symbols={symbol_id: apply_symbol_alias(symbol, aliases) for symbol_id, symbol in rekey_map(provided.symbols, aliases).items()},
            warnings=rekey_symbol_ids(provided.warnings, aliases),
            failures=rekey_symbol_ids(provided.failures, aliases),
            fetched_at=provided.fetched_at,
        )

        # Raise the catalogued error only when no symbol produced a quote.
        self.verify(
            bool(quotations.quotes),
            a.QUOTES_UNAVAILABLE_ID,
            symbols=', '.join(dict.fromkeys(symbols)),
            failures=[failure.model_dump() for failure in quotations.failures],
        )

        # Return the quotations.
        return quotations
