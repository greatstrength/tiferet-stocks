"""Tiferet Stocks Reference Configuration Tests"""

# *** imports

# ** core
import io
import os
from unittest import mock

# ** infra
import pytest
import yaml
from tiferet import App, TiferetAPIError

# ** app
from tiferet_stocks import assets as a
from tiferet_stocks.domain import EXCHANGES

# *** constants

# ** constant: config_path
CONFIG_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'config.yml')

# ** constant: payload_path
PAYLOAD_PATH = os.path.join(os.path.dirname(__file__), 'repos', 'payloads', 'spy.json')

# ** constant: static_prices_path
STATIC_PRICES_PATH = os.path.join(os.path.dirname(__file__), 'repos', 'fixtures', 'static_prices.yml')

# *** fixtures

# ** fixture: app
@pytest.fixture
def app():
    '''
    The reference stocks client session with urlopen patched to a recorded SPY payload.
    '''

    # Read the recorded payload once.
    with open(PAYLOAD_PATH, 'rb') as file:
        body = file.read()

    # Return a fresh context-managed response per call.
    def respond(*args, **kwargs):
        response = mock.MagicMock()
        response.__enter__.return_value = io.BytesIO(body)
        return response

    # Yield the app session with the network patched out.
    with mock.patch('urllib.request.urlopen', side_effect=respond):
        yield App('stocks_client', app_config=CONFIG_PATH)

# *** tests

# ** test: symbols_get
def test_symbols_get(app) -> None:
    '''
    Test that symbols.get runs end to end through the reference configuration.

    :param app: The app session.
    :type app: AppSessionContext
    '''

    lookup = app.run('symbols.get', data={'id': 'SPY', 'exchange': 'NYSE_ARCA'})

    assert lookup.symbols['SPY'].exchange == 'NYSE_ARCA'
    assert lookup.failures == []

# ** test: symbols_get_requires_id
def test_symbols_get_requires_id(app) -> None:
    '''
    Test that symbols.get rejects a request with no id.

    :param app: The app session.
    :type app: AppSessionContext
    '''

    with pytest.raises(TiferetAPIError):
        app.run('symbols.get', data={})

# ** test: symbols_resolve
def test_symbols_resolve(app) -> None:
    '''
    Test that symbols.resolve reports an expected exchange mismatch as a failure.

    :param app: The app session.
    :type app: AppSessionContext
    '''

    lookup = app.run('symbols.resolve', data={'ids': ['SPY'], 'exchanges': {'SPY': 'NYSE'}})

    assert lookup.symbols == {}
    assert lookup.failures[0].reason == 'symbol_mismatch'

# ** test: exchanges_list
def test_exchanges_list(app) -> None:
    '''
    Test that exchanges.list returns the domain exchange ids.

    :param app: The app session.
    :type app: AppSessionContext
    '''

    assert app.run('exchanges.list') == EXCHANGES

# ** test: quotes_get
def test_quotes_get(app) -> None:
    '''
    Test that quotes.get runs end to end through the reference configuration on the Yahoo provider.

    :param app: The app session.
    :type app: AppSessionContext
    '''

    quote_set = app.run('quotes.get', data={'symbols': ['SPY']})

    assert isinstance(quote_set.quotes['SPY'].price, float)
    assert quote_set.quotes['SPY'].source == 'yahoo_chart'
    assert quote_set.symbols['SPY'].exchange == 'NYSE_ARCA'

# ** test: quotes_get_static_provider_swap
def test_quotes_get_static_provider_swap(tmp_path, monkeypatch) -> None:
    '''
    Test that changing only the price_service entry swaps the provider with no code change, and that a total failure
    surfaces QUOTES_UNAVAILABLE with its configured message.

    :param tmp_path: A temporary directory.
    :type tmp_path: pathlib.Path
    :param monkeypatch: The pytest monkeypatch fixture.
    :type monkeypatch: pytest.MonkeyPatch
    '''

    # Copy the reference config and change only the price_service entry, keeping entry order (services before events).
    with open(CONFIG_PATH, 'r', encoding='utf-8') as file:
        config = yaml.safe_load(file)
    config['services']['price_service'] = {
        'module_path': 'tiferet_stocks.repos.static',
        'class_name': 'StaticPriceRepository',
        'params': {'fixture_path': STATIC_PRICES_PATH},
    }
    (tmp_path / 'config.yml').write_text(yaml.safe_dump(config, sort_keys=False))
    monkeypatch.chdir(tmp_path)

    # Run quotes.get with the network blocked.
    with mock.patch('urllib.request.urlopen', side_effect=AssertionError('network used')):
        app = App('stocks_client', app_config=str(tmp_path / 'config.yml'))
        quote_set = app.run('quotes.get', data={'symbols': ['AAPL', 'NOPE']})
        with pytest.raises(TiferetAPIError) as exc_info:
            app.run('quotes.get', data={'symbols': ['NOPE']})

    assert quote_set.quotes['AAPL'].source == 'static'
    assert [failure.symbol_id for failure in quote_set.failures] == ['NOPE']
    assert exc_info.value.error_code == 'QUOTES_UNAVAILABLE'
    assert exc_info.value.message == 'No quotes are available for the requested symbols: NOPE.'

# ** test: quotes_unavailable_config_matches_assets
def test_quotes_unavailable_config_matches_assets() -> None:
    '''
    Test that the reference config catalogues QUOTES_UNAVAILABLE with the default error data from assets.
    '''

    with open(CONFIG_PATH, 'r', encoding='utf-8') as file:
        config = yaml.safe_load(file)

    assert config['errors'][a.QUOTES_UNAVAILABLE_ID] == a.QUOTES_UNAVAILABLE_DATA
