"""Tiferet Stocks Static Price Repository Tests"""

# *** imports

# ** core
import json
import os

# ** app
from tiferet_stocks.repos.static import StaticPriceRepository

# *** constants

# ** constant: fixture_path
FIXTURE_PATH = os.path.join(os.path.dirname(__file__), 'fixtures', 'static_prices.yml')

# *** tests

# ** test: get_quotes_from_yaml_fixture
def test_get_quotes_from_yaml_fixture() -> None:
    '''
    Test that a YAML fixture serves float-priced quotes and a not_found failure for an unknown id.
    '''

    quote_set = StaticPriceRepository(fixture_path=FIXTURE_PATH).get_quotes(['AAPL', 'SPY', 'NOPE'])

    assert quote_set.quotes['AAPL'].price == 251.5
    assert quote_set.quotes['AAPL'].change_pct == 0.6
    assert isinstance(quote_set.quotes['SPY'].price, float)
    assert quote_set.quotes['SPY'].change_pct is None
    assert quote_set.quotes['SPY'].source == 'static'
    assert [(f.symbol_id, f.reason) for f in quote_set.failures] == [('NOPE', 'not_found')]

# ** test: get_quotes_from_json_fixture
def test_get_quotes_from_json_fixture(tmp_path) -> None:
    '''
    Test that a JSON fixture is read as well.

    :param tmp_path: A temporary directory.
    :type tmp_path: pathlib.Path
    '''

    path = tmp_path / 'prices.json'
    path.write_text(json.dumps({'prices': {'IBM': {'price': 300.25}}}))

    quote_set = StaticPriceRepository(fixture_path=str(path)).get_quotes(['IBM'])

    assert quote_set.quotes['IBM'].price == 300.25
    assert quote_set.quotes['IBM'].currency == 'USD'

# ** test: get_quotes_from_dict
def test_get_quotes_from_dict() -> None:
    '''
    Test that prices can be passed directly, with no file.
    '''

    quote_set = StaticPriceRepository(prices={'QQQ': {'price': 600, 'previous_close': 600}}).get_quotes(['QQQ'])

    assert quote_set.quotes['QQQ'].change_pct == 0.0
    assert quote_set.symbols == {}
