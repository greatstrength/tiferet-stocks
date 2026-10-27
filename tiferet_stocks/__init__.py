"""Tiferet Stocks Version and Global Exports"""

# *** exports

# ** app
# Wrap runtime imports in a try/except so that build tools can read
# __version__ without the full dependency tree installed.
try:
    from . import assets as a
    from .domain import (
        EXCHANGES,
        ASSET_TYPES,
        Symbol,
        SymbolWarning,
        SymbolLookup,
        QuoteFailure,
        Quote,
        Quotations,
    )
    from .interfaces import PriceService, SymbolLookupService
except Exception as e:
    import os, sys
    if not os.getenv('TIFERET_STOCKS_SILENT_IMPORTS'):
        print(f'Warning: Failed to import tiferet_stocks modules: {e}', file=sys.stderr)

# *** version

__version__ = '1.0.0b1'
