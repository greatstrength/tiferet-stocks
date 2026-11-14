"""Tiferet Stocks Assets App

Default app sessions and app service dependencies for the stocks package,
seeded into the cache by the stocks CLI blueprint so the standard services
run with no configuration file.
"""

# *** imports

# ** core
from typing import Any, Dict

# ** infra
from tiferet.assets.core import create_app_service_dependency_data, create_default_app_session_data

# ** app
from .cli import STOCKS_CLI_SESSION_ID
from .core import (
    WATCHLIST_SERVICE_ID,
    SYMBOL_ALIAS_SERVICE_ID,
    SYMBOL_LOOKUP_SERVICE_ID,
    PRICE_SERVICE_ID,
    GET_SYMBOL_EVENT_ID,
    RESOLVE_SYMBOLS_EVENT_ID,
    LIST_EXCHANGES_EVENT_ID,
    GET_QUOTES_EVENT_ID,
    GET_HISTORY_EVENT_ID,
    GET_WATCHLIST_EVENT_ID,
    LIST_WATCHLISTS_EVENT_ID,
    CREATE_WATCHLIST_EVENT_ID,
    UPDATE_WATCHLIST_EVENT_ID,
    DELETE_WATCHLIST_EVENT_ID,
    ADD_WATCHLIST_SYMBOL_EVENT_ID,
    REMOVE_WATCHLIST_SYMBOL_EVENT_ID,
    MOVE_WATCHLIST_SYMBOL_EVENT_ID,
)

# *** constants (ids)

# ** constant: stocks_client_session_id
STOCKS_CLIENT_SESSION_ID = 'stocks_client'

# *** constants (sessions)

# ** constant: stocks_cli_session_data
STOCKS_CLI_SESSION_DATA = create_default_app_session_data(
    'Stocks CLI',
    description='Run reporting and watchlist commands through the core CLI.',
)

# ** constant: stocks_client_session_data
STOCKS_CLIENT_SESSION_DATA = create_default_app_session_data(
    'Stocks Client',
    description='Reference client session for tiferet-stocks features.',
)

# *** constants (services)

# ** constant: watchlist_service_data
WATCHLIST_SERVICE_DATA = create_app_service_dependency_data(
    'tiferet_stocks.repos.watchlist',
    'WatchlistConfigRepository',
    parameters={
        'watchlist_config': 'data/watchlists.yml',
    },
)

# ** constant: symbol_alias_service_data
SYMBOL_ALIAS_SERVICE_DATA = create_app_service_dependency_data(
    'tiferet_stocks.repos.symbol',
    'SymbolAliasRepository',
)

# ** constant: symbol_lookup_service_data
SYMBOL_LOOKUP_SERVICE_DATA = create_app_service_dependency_data(
    'tiferet_stocks.repos.symbol',
    'YahooChartSymbolRepository',
    parameters={
        'timeout': '10',
        'retries': '1',
    },
)

# ** constant: price_service_data
PRICE_SERVICE_DATA = create_app_service_dependency_data(
    'tiferet_stocks.repos.yahoo',
    'YahooChartPriceRepository',
    parameters={
        'timeout': '10',
        'retries': '1',
        'batch_quote_url': 'https://query1.finance.yahoo.com/v7/finance/quote?symbols={symbols}&crumb={crumb}',
        'cookie_url': 'https://fc.yahoo.com',
        'crumb_url': 'https://query1.finance.yahoo.com/v1/test/getcrumb',
    },
)

# ** constant: get_symbol_event_data
GET_SYMBOL_EVENT_DATA = create_app_service_dependency_data(
    'tiferet_stocks.events.symbol',
    'GetSymbol',
)

# ** constant: resolve_symbols_event_data
RESOLVE_SYMBOLS_EVENT_DATA = create_app_service_dependency_data(
    'tiferet_stocks.events.symbol',
    'ResolveSymbols',
)

# ** constant: list_exchanges_event_data
LIST_EXCHANGES_EVENT_DATA = create_app_service_dependency_data(
    'tiferet_stocks.events.symbol',
    'ListExchanges',
)

# ** constant: get_quotes_event_data
GET_QUOTES_EVENT_DATA = create_app_service_dependency_data(
    'tiferet_stocks.events.quote',
    'GetQuotes',
)

# ** constant: get_history_event_data
GET_HISTORY_EVENT_DATA = create_app_service_dependency_data(
    'tiferet_stocks.events.history',
    'GetHistory',
)

# ** constant: get_watchlist_event_data
GET_WATCHLIST_EVENT_DATA = create_app_service_dependency_data(
    'tiferet_stocks.events.watchlist',
    'GetWatchlist',
)

# ** constant: list_watchlists_event_data
LIST_WATCHLISTS_EVENT_DATA = create_app_service_dependency_data(
    'tiferet_stocks.events.watchlist',
    'ListWatchlists',
)

# ** constant: create_watchlist_event_data
CREATE_WATCHLIST_EVENT_DATA = create_app_service_dependency_data(
    'tiferet_stocks.events.watchlist',
    'CreateWatchlist',
)

# ** constant: update_watchlist_event_data
UPDATE_WATCHLIST_EVENT_DATA = create_app_service_dependency_data(
    'tiferet_stocks.events.watchlist',
    'UpdateWatchlist',
)

# ** constant: delete_watchlist_event_data
DELETE_WATCHLIST_EVENT_DATA = create_app_service_dependency_data(
    'tiferet_stocks.events.watchlist',
    'DeleteWatchlist',
)

# ** constant: add_watchlist_symbol_event_data
ADD_WATCHLIST_SYMBOL_EVENT_DATA = create_app_service_dependency_data(
    'tiferet_stocks.events.watchlist',
    'AddWatchlistSymbol',
)

# ** constant: remove_watchlist_symbol_event_data
REMOVE_WATCHLIST_SYMBOL_EVENT_DATA = create_app_service_dependency_data(
    'tiferet_stocks.events.watchlist',
    'RemoveWatchlistSymbol',
)

# ** constant: move_watchlist_symbol_event_data
MOVE_WATCHLIST_SYMBOL_EVENT_DATA = create_app_service_dependency_data(
    'tiferet_stocks.events.watchlist',
    'MoveWatchlistSymbol',
)

# *** constants (groups)

# ** constant: stocks_default_app_sessions
STOCKS_DEFAULT_APP_SESSIONS: Dict[str, Dict[str, Any]] = {
    STOCKS_CLI_SESSION_ID: STOCKS_CLI_SESSION_DATA,
    STOCKS_CLIENT_SESSION_ID: STOCKS_CLIENT_SESSION_DATA,
}

# ** constant: stocks_default_services
# Repositories precede the events that inject them (DI order).
STOCKS_DEFAULT_SERVICES: Dict[str, Dict[str, Any]] = {
    WATCHLIST_SERVICE_ID: WATCHLIST_SERVICE_DATA,
    SYMBOL_ALIAS_SERVICE_ID: SYMBOL_ALIAS_SERVICE_DATA,
    SYMBOL_LOOKUP_SERVICE_ID: SYMBOL_LOOKUP_SERVICE_DATA,
    PRICE_SERVICE_ID: PRICE_SERVICE_DATA,
    GET_SYMBOL_EVENT_ID: GET_SYMBOL_EVENT_DATA,
    RESOLVE_SYMBOLS_EVENT_ID: RESOLVE_SYMBOLS_EVENT_DATA,
    LIST_EXCHANGES_EVENT_ID: LIST_EXCHANGES_EVENT_DATA,
    GET_QUOTES_EVENT_ID: GET_QUOTES_EVENT_DATA,
    GET_HISTORY_EVENT_ID: GET_HISTORY_EVENT_DATA,
    GET_WATCHLIST_EVENT_ID: GET_WATCHLIST_EVENT_DATA,
    LIST_WATCHLISTS_EVENT_ID: LIST_WATCHLISTS_EVENT_DATA,
    CREATE_WATCHLIST_EVENT_ID: CREATE_WATCHLIST_EVENT_DATA,
    UPDATE_WATCHLIST_EVENT_ID: UPDATE_WATCHLIST_EVENT_DATA,
    DELETE_WATCHLIST_EVENT_ID: DELETE_WATCHLIST_EVENT_DATA,
    ADD_WATCHLIST_SYMBOL_EVENT_ID: ADD_WATCHLIST_SYMBOL_EVENT_DATA,
    REMOVE_WATCHLIST_SYMBOL_EVENT_ID: REMOVE_WATCHLIST_SYMBOL_EVENT_DATA,
    MOVE_WATCHLIST_SYMBOL_EVENT_ID: MOVE_WATCHLIST_SYMBOL_EVENT_DATA,
}
