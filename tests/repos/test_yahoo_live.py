"""Tiferet Stocks Yahoo Chart Repository Live Tests"""

# *** imports

# ** core
import os

# ** infra
import pytest

# ** app
from tiferet_stocks.repos.yahoo import YahooChartPriceRepository

# *** constants

# ** constant: live_flag
LIVE_FLAG = 'TIFERET_STOCKS_LIVE'

# *** tests

# ** test: live_lookup
@pytest.mark.skipif(os.getenv(LIVE_FLAG) != '1', reason=f'set {LIVE_FLAG}=1 to run live provider checks')
def test_live_lookup() -> None:
    '''
    Opt-in live check that the Yahoo chart format still translates.
    '''

    lookup = YahooChartPriceRepository().lookup(['AAPL', 'SPY'])

    assert lookup.symbols['AAPL'].exchange == 'NASDAQ'
    assert lookup.symbols['SPY'].exchange == 'NYSE_ARCA'
    assert lookup.symbols['SPY'].asset_type == 'etf'

# ** test: live_quotes
@pytest.mark.skipif(os.getenv(LIVE_FLAG) != '1', reason=f'set {LIVE_FLAG}=1 to run live provider checks')
def test_live_quotes() -> None:
    '''
    Opt-in live check that the Yahoo chart format still yields float-priced quotes.
    '''

    quotations = YahooChartPriceRepository().get_quotes(['AAPL', 'SPY'])

    assert isinstance(quotations.quotes['AAPL'].price, float)
    assert quotations.quotes['SPY'].source == 'yahoo_chart'
    assert quotations.failures == []
