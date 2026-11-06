"""Tiferet Stocks Assets Error

Catalogued error ids and their default error data.
"""

# *** imports

# ** infra
from tiferet.assets.core import EN_US, create_default_error_data

# *** constants (ids)

# ** constant: quotes_unavailable_id
QUOTES_UNAVAILABLE_ID = 'QUOTES_UNAVAILABLE'

# ** constant: watchlist_not_found_id
WATCHLIST_NOT_FOUND_ID = 'WATCHLIST_NOT_FOUND'

# ** constant: watchlist_exists_id
WATCHLIST_EXISTS_ID = 'WATCHLIST_EXISTS'

# ** constant: watchlist_symbol_exists_id
WATCHLIST_SYMBOL_EXISTS_ID = 'WATCHLIST_SYMBOL_EXISTS'

# ** constant: watchlist_symbol_not_found_id
WATCHLIST_SYMBOL_NOT_FOUND_ID = 'WATCHLIST_SYMBOL_NOT_FOUND'

# ** constant: watchlist_index_out_of_range_id
WATCHLIST_INDEX_OUT_OF_RANGE_ID = 'WATCHLIST_INDEX_OUT_OF_RANGE'

# *** constants (models)

# ** constant: quotes_unavailable_data
QUOTES_UNAVAILABLE_DATA = create_default_error_data(
    'Quotes Unavailable',
    [(EN_US, 'No quotes are available for the requested symbols: {symbols}.')],
)

# ** constant: watchlist_not_found_data
WATCHLIST_NOT_FOUND_DATA = create_default_error_data(
    'Watchlist Not Found',
    [(EN_US, 'Watchlist not found: {id}.')],
)

# ** constant: watchlist_exists_data
WATCHLIST_EXISTS_DATA = create_default_error_data(
    'Watchlist Exists',
    [(EN_US, 'Watchlist already exists: {id}.')],
)

# ** constant: watchlist_symbol_exists_data
WATCHLIST_SYMBOL_EXISTS_DATA = create_default_error_data(
    'Watchlist Symbol Exists',
    [(EN_US, 'Symbol already exists in watchlist {id}: {symbol_id}.')],
)

# ** constant: watchlist_symbol_not_found_data
WATCHLIST_SYMBOL_NOT_FOUND_DATA = create_default_error_data(
    'Watchlist Symbol Not Found',
    [(EN_US, 'Symbol not found in watchlist {id}: {symbol_id}.')],
)

# ** constant: watchlist_index_out_of_range_data
WATCHLIST_INDEX_OUT_OF_RANGE_DATA = create_default_error_data(
    'Watchlist Index Out Of Range',
    [(EN_US, 'Watchlist index must be -1 or greater: {index}.')],
)

# *** constants (groups)

# ** constant: default_errors
DEFAULT_ERRORS = {
    QUOTES_UNAVAILABLE_ID: QUOTES_UNAVAILABLE_DATA,
    WATCHLIST_NOT_FOUND_ID: WATCHLIST_NOT_FOUND_DATA,
    WATCHLIST_EXISTS_ID: WATCHLIST_EXISTS_DATA,
    WATCHLIST_SYMBOL_EXISTS_ID: WATCHLIST_SYMBOL_EXISTS_DATA,
    WATCHLIST_SYMBOL_NOT_FOUND_ID: WATCHLIST_SYMBOL_NOT_FOUND_DATA,
    WATCHLIST_INDEX_OUT_OF_RANGE_ID: WATCHLIST_INDEX_OUT_OF_RANGE_DATA,
}
