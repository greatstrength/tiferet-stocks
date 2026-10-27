"""Tiferet Stocks Assets Error

Catalogued error ids and their default error data.
"""

# *** imports

# ** infra
from tiferet.assets.core import EN_US, create_default_error_data

# *** constants (ids)

# ** constant: quotes_unavailable_id
QUOTES_UNAVAILABLE_ID = 'QUOTES_UNAVAILABLE'

# ** constant: history_unavailable_id
HISTORY_UNAVAILABLE_ID = 'HISTORY_UNAVAILABLE'

# ** constant: invalid_history_range_id
INVALID_HISTORY_RANGE_ID = 'INVALID_HISTORY_RANGE'

# *** constants (models)

# ** constant: quotes_unavailable_data
QUOTES_UNAVAILABLE_DATA = create_default_error_data(
    'Quotes Unavailable',
    [(EN_US, 'No quotes are available for the requested symbols: {symbols}.')],
)

# ** constant: history_unavailable_data
HISTORY_UNAVAILABLE_DATA = create_default_error_data(
    'History Unavailable',
    [(EN_US, 'No price history is available for {symbol}: {reason}.')],
)

# ** constant: invalid_history_range_data
INVALID_HISTORY_RANGE_DATA = create_default_error_data(
    'Invalid History Range',
    [(EN_US, 'The history range {start} to {end} is invalid: {detail}.')],
)

# *** constants (groups)

# ** constant: default_errors
DEFAULT_ERRORS = {
    QUOTES_UNAVAILABLE_ID: QUOTES_UNAVAILABLE_DATA,
    HISTORY_UNAVAILABLE_ID: HISTORY_UNAVAILABLE_DATA,
    INVALID_HISTORY_RANGE_ID: INVALID_HISTORY_RANGE_DATA,
}
