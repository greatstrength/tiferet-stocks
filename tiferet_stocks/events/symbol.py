"""Tiferet Stocks Symbol Events"""

# *** imports

# ** core
from typing import Dict, List

# ** infra
from tiferet.events import DomainEvent

# ** app
from .. import assets as a
from ..domain import (
    EXCHANGES,
    NOT_FOUND,
    SYMBOL_MISMATCH,
    YAHOO_CHART,
    QuoteFailure,
    Symbol,
    SymbolAlias,
    SymbolLookup,
    rekey_symbol_ids,
    to_provider_tickers,
)
from ..interfaces import SymbolAliasService, SymbolLookupService
from ..mappers import SymbolAggregate

# *** functions

# ** function: apply_symbol_alias
def apply_symbol_alias(symbol: Symbol, aliases: Dict[str, SymbolAlias]) -> Symbol:
    '''
    Return the symbol with its id returned to the canonical ticker when the provider answered under an aliased ticker.

    :param symbol: The symbol as the provider returned it.
    :type symbol: Symbol
    :param aliases: The aliases for one provider, keyed by provider ticker.
    :type aliases: Dict[str, SymbolAlias]
    :return: The original symbol when no alias applies, otherwise a copy carrying the alias with the canonical id.
    :rtype: Symbol
    '''

    # Pass through a symbol whose ticker has no alias (exact match).
    alias = aliases.get(symbol.id)
    if alias is None:
        return symbol

    # Add the alias to a copy of the aggregate and apply it, so only apply_alias sets the id.
    aggregate = SymbolAggregate.model_validate(symbol.model_dump())
    if alias not in aggregate.aliases:
        aggregate.add_alias(alias)
    aggregate.apply_alias(alias)
    return aggregate

# *** events

# ** event: symbol_lookup_event
class SymbolLookupEvent(DomainEvent):
    '''
    Shared symbol lookup dependency and resolution rules for symbol events.
    '''

    # * attribute: symbol_lookup_service
    symbol_lookup_service: SymbolLookupService

    # * attribute: symbol_alias_service
    symbol_alias_service: SymbolAliasService

    # * init
    def __init__(self, symbol_lookup_service: SymbolLookupService, symbol_alias_service: SymbolAliasService) -> None:
        '''
        Initialize the event with the symbol lookup and symbol alias services.

        :param symbol_lookup_service: The symbol lookup service.
        :type symbol_lookup_service: SymbolLookupService
        :param symbol_alias_service: The symbol alias service.
        :type symbol_alias_service: SymbolAliasService
        '''

        # Store the injected services.
        self.symbol_lookup_service = symbol_lookup_service
        self.symbol_alias_service = symbol_alias_service

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

        # Collect the distinct requested ids; a single id string is one id.
        if isinstance(ids, str):
            ids = [ids]
        requested = list(dict.fromkeys(ids))
        exchanges = exchanges or {}

        # Read the aliases first, then look up the provider tickers; an id with no alias passes through.
        aliases = self.symbol_alias_service.get_aliases(YAHOO_CHART)
        provider_ids = dict(zip(requested, to_provider_tickers(requested, aliases)))
        lookup = self.symbol_lookup_service.lookup(list(dict.fromkeys(provider_ids.values())))

        # Re-key the provider's warnings and failures to the canonical ids, keeping those for the requested ids.
        warnings = [warning for warning in rekey_symbol_ids(lookup.warnings, aliases) if warning.symbol_id in requested]
        failures = [failure for failure in rekey_symbol_ids(lookup.failures, aliases) if failure.symbol_id in requested]
        failed_ids = {failure.symbol_id for failure in failures}

        # Check each requested id; nothing requested is silently dropped.
        symbols = {}
        for symbol_id in requested:
            symbol = lookup.symbols.get(provider_ids[symbol_id])

            # An id with neither a result nor a failure is reported as not found.
            if symbol is None:
                if symbol_id not in failed_ids:
                    failures.append(QuoteFailure(
                        symbol_id=symbol_id,
                        reason=NOT_FOUND,
                        detail='The provider returned no result.',
                    ))
                continue

            # Apply the alias inbound, before the mismatch check, so the id returns to the canonical ticker.
            symbol = apply_symbol_alias(symbol, aliases)

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
        Look up one symbol by id; a ticker the provider does not know raises SYMBOL_NOT_FOUND.

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
        lookup = self.resolve([id], exchanges={id: exchange} if exchange else None)

        # Raise the catalogued error when the provider has no such ticker after the alias and lookup steps.
        failure = next((failure for failure in lookup.failures if failure.symbol_id == id), None)
        self.verify(
            id in lookup.symbols or failure is None or failure.reason != NOT_FOUND,
            a.SYMBOL_NOT_FOUND_ID,
            id=id,
            failure=failure.model_dump() if failure else None,
        )

        # Return the lookup answer.
        return lookup

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
