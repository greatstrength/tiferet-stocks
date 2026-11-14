"""Tiferet Stocks Assets Symbol

Default symbol aliases that come out of the box, seeded into the cache as an
app constant by the stocks CLI blueprint so the symbol alias service resolves
them when no configured alias matches.
"""

# *** imports

# ** core
from typing import Any, Dict

# ** app
from .core import create_default_symbol_alias_data

# *** constants (ids)

# ** constant: yahoo_default_symbol_aliases_id
YAHOO_DEFAULT_SYMBOL_ALIASES_ID = 'yahoo_default_symbol_aliases'

# *** constants (ids_yahoo)

# ** constant: yahoo_brk_b_symbol_alias_id
YAHOO_BRK_B_SYMBOL_ALIAS_ID = 'BRK-B'

# *** constants (data_yahoo)

# ** constant: yahoo_brk_b_symbol_alias_data
YAHOO_BRK_B_SYMBOL_ALIAS_DATA = create_default_symbol_alias_data(
    'BRK.B',
)

# *** constants (groups)

# ** constant: yahoo_default_symbol_aliases
YAHOO_DEFAULT_SYMBOL_ALIASES: Dict[str, Dict[str, Any]] = {
    YAHOO_BRK_B_SYMBOL_ALIAS_ID: YAHOO_BRK_B_SYMBOL_ALIAS_DATA,
}

# ** constant: stocks_default_constants
STOCKS_DEFAULT_CONSTANTS: Dict[str, Any] = {
    YAHOO_DEFAULT_SYMBOL_ALIASES_ID: YAHOO_DEFAULT_SYMBOL_ALIASES,
}
