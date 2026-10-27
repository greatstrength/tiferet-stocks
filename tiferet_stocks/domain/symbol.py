"""Tiferet Stocks Symbol Domain Models"""

# *** imports

# ** core
from typing import Dict, List, Literal

# ** infra
from pydantic import Field
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

# *** models

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
