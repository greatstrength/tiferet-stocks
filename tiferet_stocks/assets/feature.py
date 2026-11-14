"""Tiferet Stocks Assets Feature

Default feature definitions for every stocks feature, seeded into the cache
by the stocks CLI blueprint so features run with no configuration file.
"""

# *** imports

# ** core
from typing import Any, Dict

# ** infra
from tiferet.assets.core import create_default_feature_data, create_params_schema

# ** app
from .core import (
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
    SYMBOLS_GET_FEATURE_ID,
    SYMBOLS_RESOLVE_FEATURE_ID,
    EXCHANGES_LIST_FEATURE_ID,
    QUOTES_GET_FEATURE_ID,
    QUOTES_HISTORY_FEATURE_ID,
    WATCHLISTS_GET_FEATURE_ID,
    WATCHLISTS_LIST_FEATURE_ID,
    WATCHLISTS_CREATE_FEATURE_ID,
    WATCHLISTS_UPDATE_FEATURE_ID,
    WATCHLISTS_DELETE_FEATURE_ID,
    WATCHLISTS_ADD_FEATURE_ID,
    WATCHLISTS_REMOVE_FEATURE_ID,
    WATCHLISTS_MOVE_FEATURE_ID,
)

# *** constants (features)

# ** constant: watchlists_get_feature_data
WATCHLISTS_GET_FEATURE_DATA = create_default_feature_data(
    'GetWatchlist',
    'watchlists',
    'get',
    [
        {
            'service_id': GET_WATCHLIST_EVENT_ID,
            'name': 'GetWatchlist',
        },
    ],
    description='GetWatchlist through the watchlist service',
)

# ** constant: watchlists_list_feature_data
WATCHLISTS_LIST_FEATURE_DATA = create_default_feature_data(
    'ListWatchlists',
    'watchlists',
    'list',
    [
        {
            'service_id': LIST_WATCHLISTS_EVENT_ID,
            'name': 'ListWatchlists',
        },
    ],
    description='ListWatchlists through the watchlist service',
)

# ** constant: watchlists_create_feature_data
WATCHLISTS_CREATE_FEATURE_DATA = create_default_feature_data(
    'CreateWatchlist',
    'watchlists',
    'create',
    [
        {
            'service_id': CREATE_WATCHLIST_EVENT_ID,
            'name': 'CreateWatchlist',
        },
    ],
    description='CreateWatchlist through the watchlist service',
)

# ** constant: watchlists_update_feature_data
WATCHLISTS_UPDATE_FEATURE_DATA = create_default_feature_data(
    'UpdateWatchlist',
    'watchlists',
    'update',
    [
        {
            'service_id': UPDATE_WATCHLIST_EVENT_ID,
            'name': 'UpdateWatchlist',
        },
    ],
    description='UpdateWatchlist through the watchlist service',
)

# ** constant: watchlists_delete_feature_data
WATCHLISTS_DELETE_FEATURE_DATA = create_default_feature_data(
    'DeleteWatchlist',
    'watchlists',
    'delete',
    [
        {
            'service_id': DELETE_WATCHLIST_EVENT_ID,
            'name': 'DeleteWatchlist',
        },
    ],
    description='DeleteWatchlist through the watchlist service',
)

# ** constant: watchlists_add_feature_data
WATCHLISTS_ADD_FEATURE_DATA = create_default_feature_data(
    'AddWatchlistSymbol',
    'watchlists',
    'add',
    [
        {
            'service_id': ADD_WATCHLIST_SYMBOL_EVENT_ID,
            'name': 'AddWatchlistSymbol',
        },
    ],
    description='AddWatchlistSymbol through the watchlist service',
)

# ** constant: watchlists_remove_feature_data
WATCHLISTS_REMOVE_FEATURE_DATA = create_default_feature_data(
    'RemoveWatchlistSymbol',
    'watchlists',
    'remove',
    [
        {
            'service_id': REMOVE_WATCHLIST_SYMBOL_EVENT_ID,
            'name': 'RemoveWatchlistSymbol',
        },
    ],
    description='RemoveWatchlistSymbol through the watchlist service',
)

# ** constant: watchlists_move_feature_data
WATCHLISTS_MOVE_FEATURE_DATA = create_default_feature_data(
    'MoveWatchlistSymbol',
    'watchlists',
    'move',
    [
        {
            'service_id': MOVE_WATCHLIST_SYMBOL_EVENT_ID,
            'name': 'MoveWatchlistSymbol',
        },
    ],
    description='MoveWatchlistSymbol through the watchlist service',
)

# ** constant: quotes_get_feature_data
QUOTES_GET_FEATURE_DATA = create_default_feature_data(
    'Get Quotes',
    'quotes',
    'get',
    [
        {
            'service_id': GET_QUOTES_EVENT_ID,
            'name': 'Get the quotes',
        },
    ],
    description='Gets the latest quote for each requested symbol; partial failures are returned as data',
)

# ** constant: quotes_history_feature_data
QUOTES_HISTORY_FEATURE_DATA = create_default_feature_data(
    'Get History',
    'quotes',
    'history',
    [
        {
            'service_id': GET_HISTORY_EVENT_ID,
            'name': 'Get the history',
        },
    ],
    description='Gets the daily bars for one symbol between two ISO dates, inclusive, oldest first',
    params_schema=create_params_schema(
        symbol='str',
        start='str',
        end='str',
    ),
)

# ** constant: symbols_get_feature_data
SYMBOLS_GET_FEATURE_DATA = create_default_feature_data(
    'Get Symbol',
    'symbols',
    'get',
    [
        {
            'service_id': GET_SYMBOL_EVENT_ID,
            'name': 'Look up the symbol',
        },
    ],
    description='Looks up one symbol and checks it against an optional expected exchange',
    params_schema=create_params_schema(
        id='str',
        exchange={'type': 'str', 'required': False},
    ),
)

# ** constant: symbols_resolve_feature_data
SYMBOLS_RESOLVE_FEATURE_DATA = create_default_feature_data(
    'Resolve Symbols',
    'symbols',
    'resolve',
    [
        {
            'service_id': RESOLVE_SYMBOLS_EVENT_ID,
            'name': 'Resolve the symbols',
        },
    ],
    description='Looks up many symbols and reports mismatches and unresolved ids as failures',
)

# ** constant: exchanges_list_feature_data
EXCHANGES_LIST_FEATURE_DATA = create_default_feature_data(
    'List Exchanges',
    'exchanges',
    'list',
    [
        {
            'service_id': LIST_EXCHANGES_EVENT_ID,
            'name': 'List the exchanges',
        },
    ],
    description='Lists the exchange ids the domain recognizes',
)

# *** constants (groups)

# ** constant: stocks_default_features
STOCKS_DEFAULT_FEATURES: Dict[str, Dict[str, Any]] = {
    WATCHLISTS_GET_FEATURE_ID: WATCHLISTS_GET_FEATURE_DATA,
    WATCHLISTS_LIST_FEATURE_ID: WATCHLISTS_LIST_FEATURE_DATA,
    WATCHLISTS_CREATE_FEATURE_ID: WATCHLISTS_CREATE_FEATURE_DATA,
    WATCHLISTS_UPDATE_FEATURE_ID: WATCHLISTS_UPDATE_FEATURE_DATA,
    WATCHLISTS_DELETE_FEATURE_ID: WATCHLISTS_DELETE_FEATURE_DATA,
    WATCHLISTS_ADD_FEATURE_ID: WATCHLISTS_ADD_FEATURE_DATA,
    WATCHLISTS_REMOVE_FEATURE_ID: WATCHLISTS_REMOVE_FEATURE_DATA,
    WATCHLISTS_MOVE_FEATURE_ID: WATCHLISTS_MOVE_FEATURE_DATA,
    QUOTES_GET_FEATURE_ID: QUOTES_GET_FEATURE_DATA,
    QUOTES_HISTORY_FEATURE_ID: QUOTES_HISTORY_FEATURE_DATA,
    SYMBOLS_GET_FEATURE_ID: SYMBOLS_GET_FEATURE_DATA,
    SYMBOLS_RESOLVE_FEATURE_ID: SYMBOLS_RESOLVE_FEATURE_DATA,
    EXCHANGES_LIST_FEATURE_ID: EXCHANGES_LIST_FEATURE_DATA,
}
