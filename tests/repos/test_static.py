"""Tiferet Stocks Static Price Repository Tests"""

# *** imports

# ** core
import json
import os
from unittest import mock

# ** infra
import pytest

# ** app
from tiferet_stocks import assets as a
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

# ** test: get_quotes_duplicate_unknown_id
def test_get_quotes_duplicate_unknown_id() -> None:
    '''
    Test that a repeated unknown id gives exactly one failure.
    '''

    quote_set = StaticPriceRepository(prices={}).get_quotes(['NOPE', 'NOPE'])

    assert [(f.symbol_id, f.reason) for f in quote_set.failures] == [('NOPE', 'not_found')]

# ** test: get_quotes_reads_no_file
def test_get_quotes_reads_no_file() -> None:
    '''
    Test that get_quotes never opens a file after construction.
    '''

    repo = StaticPriceRepository(fixture_path=FIXTURE_PATH)

    with mock.patch('builtins.open') as patched_open:
        repo.get_quotes(['AAPL', 'NOPE'])

    patched_open.assert_not_called()

# ** test: get_quotes_bad_rows
@pytest.mark.parametrize('row', [{}, {'price': 'n/a'}, {'price': True}, {'price': float('nan')}, 'not a row'])
def test_get_quotes_bad_rows(row) -> None:
    '''
    Test that a row with no usable price is a bad_payload failure, not an exception.

    :param row: The fixture row.
    :type row: Any
    '''

    quote_set = StaticPriceRepository(prices={'BAD': row}).get_quotes(['BAD'])

    assert quote_set.quotes == {}
    assert [(f.symbol_id, f.reason) for f in quote_set.failures] == [('BAD', 'bad_payload')]

# ** test: get_quotes_unusable_previous_close
@pytest.mark.parametrize('previous_close', ['250.0', True, -50.0, float('inf')])
def test_get_quotes_unusable_previous_close(previous_close) -> None:
    '''
    Test that an unusable previous close is dropped and the quote is kept.

    :param previous_close: The previous close value.
    :type previous_close: Any
    '''

    quote = StaticPriceRepository(prices={'X': {'price': 10, 'previous_close': previous_close}}).get_quotes(['X']).quotes['X']

    assert quote.previous_close is None
    assert quote.change_pct is None

# ** test: init_source_default
def test_init_source_default() -> None:
    '''
    Test that the default source matches the catalogued static provider id.
    '''

    assert StaticPriceRepository().source == a.STATIC_PROVIDER_ID

# ** test: get_quotes_source_override
def test_get_quotes_source_override() -> None:
    '''
    Test that a configured source reaches each quote.
    '''

    quote_set = StaticPriceRepository(prices={'X': {'price': 10}}, source='alt').get_quotes(['X'])

    assert quote_set.quotes['X'].source == 'alt'
