"""Tiferet Stocks Assets Error

Catalogued error ids and their default error data.
"""

# *** imports

# ** infra
from tiferet.assets.core import EN_US, create_default_error_data

# *** constants (ids)

# ** constant: quotes_unavailable_id
QUOTES_UNAVAILABLE_ID = 'QUOTES_UNAVAILABLE'

# *** constants (models)

# ** constant: quotes_unavailable_data
QUOTES_UNAVAILABLE_DATA = create_default_error_data(
    'Quotes Unavailable',
    [(EN_US, 'No quotes are available for the requested symbols: {symbols}.')],
)

# ** constant: default_errors
DEFAULT_ERRORS = {
    QUOTES_UNAVAILABLE_ID: QUOTES_UNAVAILABLE_DATA,
}
