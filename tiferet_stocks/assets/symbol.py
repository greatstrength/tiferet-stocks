"""Tiferet Stocks Assets Symbol

The default symbols file path, which the symbol alias repository reads unless
a client application passes another, and the default symbol aliases that come
out of the box, reconciled by the symbol alias events with the configured
aliases, which take precedence.
"""

# *** imports

# ** core
from typing import Any, Dict

# ** app
from .core import create_default_symbol_alias_data

# *** constants

# ** constant: default_symbol_config_file
DEFAULT_SYMBOL_CONFIG_FILE = 'data/symbols.yml'

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
