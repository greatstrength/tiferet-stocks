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

# ** test: live_history
@pytest.mark.skipif(os.getenv(LIVE_FLAG) != '1', reason=f'set {LIVE_FLAG}=1 to run live provider checks')
def test_live_history() -> None:
    '''
    Opt-in live check that the Yahoo daily chart format still yields float bars, oldest first.
    '''

    history = YahooChartPriceRepository().get_history('SPY', '2026-10-19', '2026-10-23')

    assert history.failure is None
    assert [bar.date for bar in history.bars] == sorted(bar.date for bar in history.bars)
    assert history.bars and all(isinstance(bar.close, float) for bar in history.bars)
