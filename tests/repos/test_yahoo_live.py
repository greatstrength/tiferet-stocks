"""Tiferet Stocks Yahoo Chart Repository Live Tests"""

# *** imports

# ** core
import os

# ** infra
import pytest

# ** app
from tiferet_stocks.repos import YahooChartPriceRepository

# *** constants

# ** constant: live_flag
LIVE_FLAG = 'TIFERET_STOCKS_LIVE'

# *** tests

# ** test: live_lookup
@pytest.mark.skipif(not os.getenv(LIVE_FLAG), reason=f'set {LIVE_FLAG}=1 to run live provider checks')
def test_live_lookup() -> None:
    '''
    Opt-in live check that the Yahoo chart format still translates.
    '''

    lookup = YahooChartPriceRepository().lookup(['AAPL', 'SPY'])

    assert lookup.symbols['AAPL'].exchange == 'NASDAQ'
    assert lookup.symbols['SPY'].exchange == 'NYSE_ARCA'
    assert lookup.symbols['SPY'].asset_type == 'etf'
