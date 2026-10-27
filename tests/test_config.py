"""Tiferet Stocks Reference Configuration Tests"""

# *** imports

# ** core
import io
import os
from unittest import mock

# ** infra
import pytest
from tiferet import App, TiferetAPIError

# ** app
from tiferet_stocks.domain import EXCHANGES

# *** constants

# ** constant: config_path
CONFIG_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'config.yml')

# ** constant: payload_path
PAYLOAD_PATH = os.path.join(os.path.dirname(__file__), 'repos', 'payloads', 'spy.json')

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
