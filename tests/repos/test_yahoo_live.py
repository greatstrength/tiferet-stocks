"""Tiferet Stocks Yahoo Chart Repository Live Tests"""

# *** imports

# ** core
import os

# ** infra
import pytest
from tiferet.events import DomainEvent

# ** app
from tiferet_stocks.events import GetQuotes, GetSymbol
from tiferet_stocks.repos.symbol import SymbolAliasRepository, YahooChartSymbolRepository
from tiferet_stocks.repos.yahoo import YahooChartPriceRepository

# *** constants

# ** constant: live_flag
LIVE_FLAG = 'TIFERET_STOCKS_LIVE'

# ** constant: seed_path
SEED_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'data', 'symbols.yml')

# *** tests

# ** test: live_lookup
@pytest.mark.skipif(os.getenv(LIVE_FLAG) != '1', reason=f'set {LIVE_FLAG}=1 to run live provider checks')
def test_live_lookup() -> None:
    '''
    Opt-in live check that the Yahoo chart format still translates.
    '''

    lookup = YahooChartSymbolRepository().lookup(['AAPL', 'SPY'])

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

# ** test: live_brk_b_alias
@pytest.mark.skipif(os.getenv(LIVE_FLAG) != '1', reason=f'set {LIVE_FLAG}=1 to run live provider checks')
def test_live_brk_b_alias() -> None:
    '''
    Opt-in live check that canonical BRK.B is requested from Yahoo as BRK-B and answered under BRK.B.
    '''

    aliases = SymbolAliasRepository(symbol_config=SEED_PATH)
    lookup = DomainEvent.handle(GetSymbol, dependencies={'symbol_lookup_service': YahooChartSymbolRepository(), 'symbol_alias_service': aliases}, id='BRK.B')
    quotations = DomainEvent.handle(GetQuotes, dependencies={'price_service': YahooChartPriceRepository(), 'symbol_alias_service': aliases}, symbols=['BRK.B'])

    assert lookup.symbols['BRK.B'].exchange == 'NYSE'
    assert isinstance(quotations.quotes['BRK.B'].price, float)
    assert quotations.quotes['BRK.B'].symbol_id == 'BRK.B'
