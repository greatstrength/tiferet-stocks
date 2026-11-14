"""Tiferet Stocks Symbol Domain Models"""

# *** imports

# ** core
from typing import Dict, List, Literal, TypeVar

# ** infra
from pydantic import Field, model_validator
from tiferet.domain import DomainObject

# ** app
from .quote import QuoteFailure

# *** constants (exchanges)

# ** constant: nyse
NYSE = 'NYSE'

# ** constant: nasdaq
NASDAQ = 'NASDAQ'

# ** constant: nyse_arca
NYSE_ARCA = 'NYSE_ARCA'

# ** constant: cboe_bzx
CBOE_BZX = 'CBOE_BZX'

# ** constant: nyse_american
NYSE_AMERICAN = 'NYSE_AMERICAN'

# ** constant: exchanges
EXCHANGES = [
    NYSE,
    NASDAQ,
    NYSE_ARCA,
    CBOE_BZX,
    NYSE_AMERICAN,
]

# *** constants (asset_types)

# ** constant: equity
EQUITY = 'equity'

# ** constant: etf
ETF = 'etf'

# ** constant: mutual_fund
MUTUAL_FUND = 'mutual_fund'

# ** constant: money_market_fund
MONEY_MARKET_FUND = 'money_market_fund'

# ** constant: asset_types
ASSET_TYPES = [
    EQUITY,
    ETF,
    MUTUAL_FUND,
    MONEY_MARKET_FUND,
]

# ** constant: fund_asset_types
FUND_ASSET_TYPES = [
    MUTUAL_FUND,
    MONEY_MARKET_FUND,
]

# *** constants (warnings)

# ** constant: unmapped_exchange
UNMAPPED_EXCHANGE = 'unmapped_exchange'

# ** constant: unmapped_asset_type
UNMAPPED_ASSET_TYPE = 'unmapped_asset_type'

# ** constant: warning_reasons
WARNING_REASONS = [
    UNMAPPED_EXCHANGE,
    UNMAPPED_ASSET_TYPE,
]

# *** constants (providers)

# ** constant: yahoo_chart
YAHOO_CHART = 'yahoo_chart'

# ** constant: providers
PROVIDERS = [
    YAHOO_CHART,
]

# *** models

# ** model: symbol_alias
class SymbolAlias(DomainObject):
    '''
    A provider-facing ticker for a canonical symbol id, tagged by provider.
    '''

    # * attribute: provider
    provider: Literal[tuple(PROVIDERS)] = Field(..., description='The provider id, such as yahoo_chart.')

    # * attribute: provider_ticker
    provider_ticker: str = Field(..., description='The ticker the provider expects, such as BRK-B.')

    # * attribute: canonical_id
    canonical_id: str = Field(..., description='The canonical symbol id, such as BRK.B.')

# ** model: symbol
class Symbol(DomainObject):
    '''
    A tradable or quotable instrument, in the library's provider-neutral vocabulary.
    '''

    # * attribute: id
    id: str = Field(..., description='The ticker, such as AAPL.')

    # * attribute: exchange
    exchange: Literal[tuple(EXCHANGES)] | None = Field(default=None, description='The exchange id; empty for a fund or an unmapped listing.')

    # * attribute: name
    name: str | None = Field(default=None, description='The instrument name.')

    # * attribute: asset_type
    asset_type: Literal[tuple(ASSET_TYPES)] | None = Field(default=None, description='The asset type; empty when the provider type is unmapped.')

    # * attribute: currency
    currency: str = Field(default='USD', description='The trading currency.')

    # * attribute: aliases
    aliases: List[SymbolAlias] = Field(default_factory=list, description='Provider-facing tickers for this symbol; at most one alias per provider.')

    # * method: validate_aliases (validator)
    @model_validator(mode='after')
    def validate_aliases(self) -> 'Symbol':
        '''
        Restrict aliases to at most one per provider, and only those that belong to this symbol.

        :return: The validated symbol.
        :rtype: Symbol
        '''

        # At most one alias for each provider.
        providers = [alias.provider for alias in self.aliases]
        if len(providers) != len(set(providers)):
            raise ValueError('A symbol accepts at most one alias per provider.')

        # An alias belongs when its canonical id or its provider ticker is this symbol's id.
        for alias in self.aliases:
            if alias.canonical_id != self.id and alias.provider_ticker != self.id:
                raise ValueError(
                    f'Alias for {alias.canonical_id} does not belong to symbol {self.id}.'
                )

        # Return the validated symbol.
        return self

# ** model: symbol_warning
class SymbolWarning(DomainObject):
    '''
    A soft notice attached to a symbol result.
    '''

    # * attribute: symbol_id
    symbol_id: str = Field(..., description='The requested symbol id (ticker).')

    # * attribute: reason
    reason: Literal[tuple(WARNING_REASONS)] = Field(..., description='The warning reason.')

    # * attribute: detail
    detail: str | None = Field(default=None, description='Detail about the warning, such as the raw provider code.')

# ** model: symbol_lookup
class SymbolLookup(DomainObject):
    '''
    One symbol lookup call's answer: symbols by requested id, warnings and failures.
    '''

    # * attribute: symbols
    symbols: Dict[str, Symbol] = Field(default_factory=dict, description='The resolved symbols, keyed by requested id.')

    # * attribute: warnings
    warnings: List[SymbolWarning] = Field(default_factory=list, description='The warnings raised while resolving symbols.')

    # * attribute: failures
    failures: List[QuoteFailure] = Field(default_factory=list, description='The requested symbols that produced no result.')

# *** functions

# ** typevar: T
T = TypeVar('T')

# ** function: merge_symbol_aliases
def merge_symbol_aliases(configured: Dict[str, SymbolAlias], defaults: Dict[str, SymbolAlias]) -> Dict[str, SymbolAlias]:
    '''
    Return one alias map for a provider in which the later definition wins: the defaults first, then the configured aliases in order.

    A default is dropped when a configured alias has its provider ticker or its canonical id. The configured aliases hold
    at most one alias per canonical id, which the alias events enforce with ALIAS_PROVIDER_EXISTS, so each canonical id
    has one alias and the merged map is safe to use in both directions.

    :param configured: The configured aliases for one provider, keyed by provider ticker, at most one per canonical id.
    :type configured: Dict[str, SymbolAlias]
    :param defaults: The default aliases for the same provider, keyed by provider ticker.
    :type defaults: Dict[str, SymbolAlias]
    :return: A new map holding the surviving defaults followed by the configured aliases, keyed by provider ticker.
    :rtype: Dict[str, SymbolAlias]
    '''

    # Keep a default only when no configured alias covers its provider ticker or canonical id.
    canonical_ids = {alias.canonical_id for alias in configured.values()}
    merged = {
        provider_ticker: alias
        for provider_ticker, alias in defaults.items()
        if provider_ticker not in configured and alias.canonical_id not in canonical_ids
    }

    # Add the configured aliases, in order, after the surviving defaults.
    merged.update(configured)
    return merged

# ** function: to_provider_ticker
def to_provider_ticker(symbol_id: str, aliases: Dict[str, SymbolAlias]) -> str:
    '''
    Return the provider ticker for a canonical symbol id, or the id itself when there is no alias.

    :param symbol_id: The canonical symbol id (ticker).
    :type symbol_id: str
    :param aliases: The aliases for one provider, keyed by provider ticker.
    :type aliases: Dict[str, SymbolAlias]
    :return: The provider ticker, or the original id when no alias applies.
    :rtype: str
    '''

    # Pass through a requested id that has no alias for this provider.
    for alias in aliases.values():
        if alias.canonical_id == symbol_id:
            return alias.provider_ticker
    return symbol_id

# ** function: to_provider_tickers
def to_provider_tickers(ids: List[str], aliases: Dict[str, SymbolAlias]) -> List[str]:
    '''
    Map each canonical symbol id to its provider ticker, passing through ids with no alias.

    :param ids: The canonical symbol ids (tickers).
    :type ids: List[str]
    :param aliases: The aliases for one provider, keyed by provider ticker.
    :type aliases: Dict[str, SymbolAlias]
    :return: The provider tickers, in the same order.
    :rtype: List[str]
    '''

    # Apply the outbound rule to each id; a missing alias is a passthrough.
    return [to_provider_ticker(symbol_id, aliases) for symbol_id in ids]

# ** function: to_canonical_id
def to_canonical_id(symbol_id: str, aliases: Dict[str, SymbolAlias]) -> str:
    '''
    Return the canonical symbol id for a provider ticker, or the id itself when there is no alias.

    :param symbol_id: The provider ticker, or a canonical id with no alias.
    :type symbol_id: str
    :param aliases: The aliases for one provider, keyed by provider ticker.
    :type aliases: Dict[str, SymbolAlias]
    :return: The canonical symbol id, or the original id when no alias applies.
    :rtype: str
    '''

    # The map is keyed by provider ticker; a canonical id or unknown ticker passes through.
    alias = aliases.get(symbol_id)
    return alias.canonical_id if alias is not None else symbol_id

# ** function: rekey_map
def rekey_map(items: Dict[str, T], aliases: Dict[str, SymbolAlias]) -> Dict[str, T]:
    '''
    Return a new map whose keys are canonical symbol ids.

    :param items: A map keyed by provider ticker or canonical id.
    :type items: Dict[str, T]
    :param aliases: The aliases for one provider, keyed by provider ticker.
    :type aliases: Dict[str, SymbolAlias]
    :return: A new map keyed by canonical id, with the same values.
    :rtype: Dict[str, T]
    '''

    # Rewrite each key; values are left unchanged for the caller to rewrite separately.
    return {to_canonical_id(key, aliases): value for key, value in items.items()}

# ** function: rekey_symbol_id
def rekey_symbol_id(item: T, aliases: Dict[str, SymbolAlias]) -> T:
    '''
    Return a copy of the item with its symbol_id set to the canonical id.

    :param item: A domain object with a symbol_id field.
    :type item: T
    :param aliases: The aliases for one provider, keyed by provider ticker.
    :type aliases: Dict[str, SymbolAlias]
    :return: The original item when the id is already canonical, otherwise a copy.
    :rtype: T
    '''

    # Pass through an item whose symbol_id is already the canonical id.
    current = item.symbol_id
    canonical = to_canonical_id(current, aliases)
    if canonical == current:
        return item

    # Copy so the helper stays pure and does not mutate the caller's object.
    return item.model_copy(update={'symbol_id': canonical})

# ** function: rekey_symbol_ids
def rekey_symbol_ids(items: List[T], aliases: Dict[str, SymbolAlias]) -> List[T]:
    '''
    Return a new list with each item's symbol_id set to the canonical id.

    :param items: Domain objects with a symbol_id field.
    :type items: List[T]
    :param aliases: The aliases for one provider, keyed by provider ticker.
    :type aliases: Dict[str, SymbolAlias]
    :return: A new list of items with canonical symbol ids.
    :rtype: List[T]
    '''

    # Apply the inbound symbol_id rewrite to each item, in order.
    return [rekey_symbol_id(item, aliases) for item in items]
