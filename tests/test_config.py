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

# ** constant: history_payload_path
HISTORY_PAYLOAD_PATH = os.path.join(os.path.dirname(__file__), 'repos', 'payloads', 'aapl_history.json')

# ** constant: static_history_path
STATIC_HISTORY_PATH = os.path.join(os.path.dirname(__file__), 'repos', 'fixtures', 'static_history.csv')

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

    quotations = app.run('quotes.get', data={'symbols': ['SPY']})

    assert isinstance(quotations.quotes['SPY'].price, float)
    assert quotations.quotes['SPY'].source == 'yahoo_chart'
    assert quotations.symbols['SPY'].exchange == 'NYSE_ARCA'

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
        quotations = app.run('quotes.get', data={'symbols': ['AAPL', 'NOPE']})
        with pytest.raises(TiferetAPIError) as exc_info:
            app.run('quotes.get', data={'symbols': ['NOPE']})

    assert quotations.quotes['AAPL'].source == 'static'
    assert [failure.symbol_id for failure in quotations.failures] == ['NOPE']
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

# ** test: quotes_history
def test_quotes_history() -> None:
    '''
    Test that quotes.history runs end to end through the reference configuration on the Yahoo provider.
    '''

    # Serve the recorded history payload.
    with open(HISTORY_PAYLOAD_PATH, 'rb') as file:
        body = file.read()
    response = mock.MagicMock()
    response.__enter__.return_value = io.BytesIO(body)

    # Run quotes.history.
    with mock.patch('urllib.request.urlopen', return_value=response):
        history = App('stocks_client', app_config=CONFIG_PATH).run('quotes.history', data={'symbol': 'AAPL', 'start': '2026-10-20', 'end': '2026-10-22'})

    bars = history.bars
    assert (history.symbol_id, history.start, history.end, history.failure) == ('AAPL', '2026-10-20', '2026-10-22', None)
    assert [bar.date for bar in bars] == ['2026-10-20', '2026-10-21', '2026-10-22']
    assert isinstance(bars[0].close, float)

# ** test: quotes_history_static_provider_swap
def test_quotes_history_static_provider_swap(tmp_path, monkeypatch) -> None:
    '''
    Test that the static provider serves quotes.history from CSV with no code change, and that the catalogued history
    errors surface with their configured messages.

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
        'params': {'history_path': STATIC_HISTORY_PATH},
    }
    (tmp_path / 'config.yml').write_text(yaml.safe_dump(config, sort_keys=False))
    monkeypatch.chdir(tmp_path)

    # Run quotes.history with the network blocked.
    with mock.patch('urllib.request.urlopen', side_effect=AssertionError('network used')):
        app = App('stocks_client', app_config=str(tmp_path / 'config.yml'))
        bars = app.run('quotes.history', data={'symbol': 'AAPL', 'start': '2026-10-19', 'end': '2026-10-23'}).bars
        empty = app.run('quotes.history', data={'symbol': 'AAPL', 'start': '2026-10-24', 'end': '2026-10-25'}).bars
        with pytest.raises(TiferetAPIError) as unavailable:
            app.run('quotes.history', data={'symbol': 'NOPE', 'start': '2026-10-19', 'end': '2026-10-23'})
        with pytest.raises(TiferetAPIError) as invalid:
            app.run('quotes.history', data={'symbol': 'AAPL', 'start': '2026-10-23', 'end': '2026-10-19'})

    assert [bar.date for bar in bars] == ['2026-10-19', '2026-10-20', '2026-10-21', '2026-10-23']
    assert empty == []
    assert unavailable.value.error_code == 'HISTORY_UNAVAILABLE'
    assert unavailable.value.message == 'No price history is available for NOPE: not_found.'
    assert invalid.value.error_code == 'INVALID_HISTORY_RANGE'
    assert invalid.value.message == 'The history range 2026-10-23 to 2026-10-19 is invalid: the start date is after the end date.'

# ** test: quotes_history_requires_params
def test_quotes_history_requires_params(app) -> None:
    '''
    Test that quotes.history validates its parameters.

    :param app: The app session.
    :type app: AppSessionContext
    '''

    with pytest.raises(TiferetAPIError) as exc_info:
        app.run('quotes.history', data={'symbol': 'AAPL', 'start': '2026-10-19'})

    assert exc_info.value.error_code == 'REQUEST_VALIDATION_FAILED'

# ** test: history_errors_config_match_assets
@pytest.mark.parametrize('error_id, error_data', [
    (a.HISTORY_UNAVAILABLE_ID, a.HISTORY_UNAVAILABLE_DATA),
    (a.INVALID_HISTORY_RANGE_ID, a.INVALID_HISTORY_RANGE_DATA),
])
def test_history_errors_config_match_assets(error_id: str, error_data: dict) -> None:
    '''
    Test that the reference config catalogues the history errors with the default error data from assets.

    :param error_id: The error id.
    :type error_id: str
    :param error_data: The default error data.
    :type error_data: dict
    '''

    with open(CONFIG_PATH, 'r', encoding='utf-8') as file:
        config = yaml.safe_load(file)

    assert config['errors'][error_id] == error_data
    assert a.DEFAULT_ERRORS[error_id] == error_data
