"""Tiferet Stocks Symbol Events"""

# *** imports

# ** core
from typing import Dict, List

# ** infra
from tiferet.events import DomainEvent

# ** app
from ..domain import (
    EXCHANGES,
    NOT_FOUND,
    SYMBOL_MISMATCH,
    QuoteFailure,
    SymbolLookup,
)
from ..interfaces import SymbolLookupService

# *** events

# ** event: symbol_lookup_event
class SymbolLookupEvent(DomainEvent):
    '''
    Shared symbol lookup dependency and resolution rules for symbol events.
    '''

    # * attribute: symbol_lookup_service
    symbol_lookup_service: SymbolLookupService

    # * init
    def __init__(self, symbol_lookup_service: SymbolLookupService) -> None:
        '''
        Initialize the event with the symbol lookup service.

        :param symbol_lookup_service: The symbol lookup service.
        :type symbol_lookup_service: SymbolLookupService
        '''

        # Store the injected symbol lookup service.
        self.symbol_lookup_service = symbol_lookup_service

    # * method: resolve
    def resolve(self, ids: List[str], exchanges: Dict[str, str] = None) -> SymbolLookup:
        '''
        Look up the requested ids and check each result against the request.

        :param ids: The requested symbol ids (tickers).
        :type ids: List[str]
        :param exchanges: The expected exchange id per requested symbol id, when known.
        :type exchanges: Dict[str, str]
        :return: The matching symbols by requested id, with warnings and failures.
        :rtype: SymbolLookup
        '''

        # Look up the distinct requested ids with the provider; a single id string is one id.
        if isinstance(ids, str):
            ids = [ids]
        requested = list(dict.fromkeys(ids))
        exchanges = exchanges or {}
        lookup = self.symbol_lookup_service.lookup(requested)

        # Keep the provider's warnings and failures for the requested ids.
        warnings = [warning for warning in lookup.warnings if warning.symbol_id in requested]
        failures = [failure for failure in lookup.failures if failure.symbol_id in requested]
        failed_ids = {failure.symbol_id for failure in failures}

        # Check each requested id; nothing requested is silently dropped.
        symbols = {}
        for symbol_id in requested:
            symbol = lookup.symbols.get(symbol_id)

            # An id with neither a result nor a failure is reported as not found.
            if symbol is None:
                if symbol_id not in failed_ids:
                    failures.append(QuoteFailure(
                        symbol_id=symbol_id,
                        reason=NOT_FOUND,
                        detail='The provider returned no result.',
                    ))
                continue

            # A result for a different ticker is a mismatch.
            if symbol.id.upper() != symbol_id.upper():
                failures.append(QuoteFailure(
                    symbol_id=symbol_id,
                    reason=SYMBOL_MISMATCH,
                    detail=f'expected ticker {symbol_id}, actual ticker {symbol.id}',
                ))
                continue

            # A result on a different exchange than expected is a mismatch.
            expected_exchange = exchanges.get(symbol_id)
            if expected_exchange and symbol.exchange != expected_exchange:
                failures.append(QuoteFailure(
                    symbol_id=symbol_id,
                    reason=SYMBOL_MISMATCH,
                    detail=f'expected exchange {expected_exchange}, actual exchange {symbol.exchange}',
                ))
                continue

            # The result matches the request.
            symbols[symbol_id] = symbol

        # Return the checked lookup answer.
        return SymbolLookup(symbols=symbols, warnings=warnings, failures=failures)

# ** event: get_symbol
class GetSymbol(SymbolLookupEvent):
    '''
    Domain event to look up one symbol and check it against the request.
    '''

    # * method: execute
    @DomainEvent.parameters_required(['id'])
    def execute(self, id: str, exchange: str = None, **kwargs) -> SymbolLookup:
        '''
        Look up one symbol by id.

        :param id: The requested symbol id (ticker).
        :type id: str
        :param exchange: The expected exchange id, when known.
        :type exchange: str
        :param kwargs: Additional keyword arguments.
        :type kwargs: dict
        :return: The symbol lookup answer for the one id.
        :rtype: SymbolLookup
        '''

        # Resolve the single id with its expected exchange.
        return self.resolve([id], exchanges={id: exchange} if exchange else None)

# ** event: resolve_symbols
class ResolveSymbols(SymbolLookupEvent):
    '''
    Domain event to look up many symbols and check each against the request.
    '''

    # * method: execute
    @DomainEvent.parameters_required(['ids'])
    def execute(self, ids: List[str], exchanges: Dict[str, str] = None, **kwargs) -> SymbolLookup:
        '''
        Look up many symbols by id.

        :param ids: The requested symbol ids (tickers).
        :type ids: List[str]
        :param exchanges: The expected exchange id per requested symbol id, when known.
        :type exchanges: Dict[str, str]
        :param kwargs: Additional keyword arguments.
        :type kwargs: dict
        :return: The symbol lookup answer for the requested ids.
        :rtype: SymbolLookup
        '''

        # Resolve the requested ids with any expected exchanges.
        return self.resolve(ids, exchanges=exchanges)

# ** event: list_exchanges
class ListExchanges(DomainEvent):
    '''
    Domain event to list the exchange ids the domain recognizes.
    '''

    # * method: execute
    def execute(self, **kwargs) -> List[str]:
        '''
        List the recognized exchange ids.

        :param kwargs: Additional keyword arguments.
        :type kwargs: dict
        :return: The exchange ids, in order.
        :rtype: List[str]
        '''

        # Return a copy of the exchange list.
        return list(EXCHANGES)
