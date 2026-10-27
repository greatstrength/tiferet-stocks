"""Tiferet Stocks Yahoo Chart Repository Tests"""

# *** imports

# ** core
import io
import json
import os
from datetime import datetime, timezone
import socket
from http import client as http_client
from typing import Any, List
from unittest import mock
from urllib import error as url_error

# ** infra
import pytest

# ** app
from tiferet_stocks import assets as a
from tiferet_stocks.repos.yahoo import (
    YAHOO_ASSET_TYPE_MAP,
    YAHOO_EXCHANGE_MAP,
    YahooChartPriceRepository,
)

# *** constants

# ** constant: payloads_path
PAYLOADS_PATH = os.path.join(os.path.dirname(__file__), 'payloads')

# *** functions

# ** function: read_payload
def read_payload(name: str) -> bytes:
    '''
    Read a recorded Yahoo chart response.

    :param name: The payload file name without extension.
    :type name: str
    :return: The raw response body.
    :rtype: bytes
    '''

    # Read and return the recorded body.
    with open(os.path.join(PAYLOADS_PATH, f'{name}.json'), 'rb') as file:
        return file.read()

# ** function: make_response
def make_response(body: bytes) -> Any:
    '''
    Wrap a body as a context-managed urlopen response.

    :param body: The response body.
    :type body: bytes
    :return: A mock response.
    :rtype: Any
    '''

    # Build a context manager that yields a readable body.
    response = mock.MagicMock()
    response.__enter__.return_value = io.BytesIO(body)
    return response

# ** function: make_http_error
def make_http_error(code: int) -> url_error.HTTPError:
    '''
    Build an HTTP error with the given status code.

    :param code: The HTTP status code.
    :type code: int
    :return: The HTTP error.
    :rtype: url_error.HTTPError
    '''

    # Build and return the error.
    return url_error.HTTPError('https://example.test', code, 'error', {}, io.BytesIO(b''))

# *** fixtures

# ** fixture: repo
@pytest.fixture
def repo() -> YahooChartPriceRepository:
    '''
    A Yahoo chart repository with configuration-style string parameters.
    '''

    return YahooChartPriceRepository(timeout='5', retries='1')

# ** fixture: urlopen
@pytest.fixture
def urlopen():
    '''
    Patch urlopen so no test touches the network.
    '''

    with mock.patch('urllib.request.urlopen') as patched:
        yield patched

# *** tests

# ** test: exchange_map
def test_exchange_map() -> None:
    '''
    Test the Yahoo exchange code map.
    '''

    assert YAHOO_EXCHANGE_MAP == {
        'NYQ': 'NYSE',
        'NMS': 'NASDAQ',
        'NGM': 'NASDAQ',
        'NCM': 'NASDAQ',
        'PCX': 'NYSE_ARCA',
        'BTS': 'CBOE_BZX',
        'ASE': 'NYSE_AMERICAN',
    }

# ** test: asset_type_map
def test_asset_type_map() -> None:
    '''
    Test the Yahoo instrument type map.
    '''

    assert YAHOO_ASSET_TYPE_MAP == {
        'EQUITY': 'equity',
        'ETF': 'etf',
        'MONEYMARKET': 'money_market_fund',
        'MUTUALFUND': 'mutual_fund',
    }

# ** test: init_converts_string_params
def test_init_converts_string_params(repo: YahooChartPriceRepository) -> None:
    '''
    Test that string parameters from configuration are converted.

    :param repo: The repository.
    :type repo: YahooChartPriceRepository
    '''

    assert repo.timeout == 5.0
    assert repo.retries == 1

# ** test: lookup_recorded_payloads
@pytest.mark.parametrize('symbol_id, exchange, asset_type', [
    ('AAPL', 'NASDAQ', 'equity'),
    ('QQQ', 'NASDAQ', 'etf'),
    ('PLUG', 'NASDAQ', 'equity'),
    ('IBM', 'NYSE', 'equity'),
    ('SPY', 'NYSE_ARCA', 'etf'),
    ('XLK', 'NYSE_ARCA', 'etf'),
    ('ARKK', 'CBOE_BZX', 'etf'),
    ('IMO', 'NYSE_AMERICAN', 'equity'),
])
def test_lookup_recorded_payloads(repo: YahooChartPriceRepository,
                                  urlopen: mock.Mock,
                                  symbol_id: str,
                                  exchange: str,
                                  asset_type: str) -> None:
    '''
    Test that recorded payloads translate to domain exchange ids and asset types with no warning.

    :param repo: The repository.
    :type repo: YahooChartPriceRepository
    :param urlopen: The patched urlopen.
    :type urlopen: mock.Mock
    :param symbol_id: The requested symbol id.
    :type symbol_id: str
    :param exchange: The expected exchange id.
    :type exchange: str
    :param asset_type: The expected asset type.
    :type asset_type: str
    '''

    urlopen.return_value = make_response(read_payload(symbol_id.lower()))

    lookup = repo.lookup([symbol_id])

    assert lookup.symbols[symbol_id].exchange == exchange
    assert lookup.symbols[symbol_id].asset_type == asset_type
    assert lookup.warnings == []
    assert lookup.failures == []

# ** test: lookup_unmapped_exchange
def test_lookup_unmapped_exchange(repo: YahooChartPriceRepository, urlopen: mock.Mock) -> None:
    '''
    Test that an unmapped exchange code gives an empty exchange and one warning carrying the raw code.

    :param repo: The repository.
    :type repo: YahooChartPriceRepository
    :param urlopen: The patched urlopen.
    :type urlopen: mock.Mock
    '''

    urlopen.return_value = make_response(read_payload('tcehy'))

    lookup = repo.lookup(['TCEHY'])

    assert lookup.symbols['TCEHY'].exchange is None
    assert lookup.symbols['TCEHY'].asset_type == 'equity'
    assert len(lookup.warnings) == 1
    assert lookup.warnings[0].reason == 'unmapped_exchange'
    assert lookup.warnings[0].detail == 'PNK'
    assert lookup.failures == []

# ** test: lookup_money_market_fund
def test_lookup_money_market_fund(repo: YahooChartPriceRepository, urlopen: mock.Mock) -> None:
    '''
    Test that a money market fund gets an empty exchange and no warning.

    :param repo: The repository.
    :type repo: YahooChartPriceRepository
    :param urlopen: The patched urlopen.
    :type urlopen: mock.Mock
    '''

    urlopen.return_value = make_response(read_payload('frsxx'))

    lookup = repo.lookup(['FRSXX'])

    assert lookup.symbols['FRSXX'].exchange is None
    assert lookup.symbols['FRSXX'].asset_type == 'money_market_fund'
    assert lookup.warnings == []

# ** test: lookup_unmapped_asset_type
def test_lookup_unmapped_asset_type(repo: YahooChartPriceRepository, urlopen: mock.Mock) -> None:
    '''
    Test that an unmapped instrument type gives an empty asset type and an unmapped_asset_type warning.

    :param repo: The repository.
    :type repo: YahooChartPriceRepository
    :param urlopen: The patched urlopen.
    :type urlopen: mock.Mock
    '''

    payload = json.loads(read_payload('aapl'))
    payload['chart']['result'][0]['meta']['instrumentType'] = 'FUTURE'
    urlopen.return_value = make_response(json.dumps(payload).encode())

    lookup = repo.lookup(['AAPL'])

    assert lookup.symbols['AAPL'].asset_type is None
    assert lookup.symbols['AAPL'].exchange == 'NASDAQ'
    assert [(w.reason, w.detail) for w in lookup.warnings] == [('unmapped_asset_type', 'FUTURE')]

# ** test: lookup_not_found
def test_lookup_not_found(repo: YahooChartPriceRepository, urlopen: mock.Mock) -> None:
    '''
    Test that a 404 is a not_found failure after one attempt, with no retry.

    :param repo: The repository.
    :type repo: YahooChartPriceRepository
    :param urlopen: The patched urlopen.
    :type urlopen: mock.Mock
    '''

    urlopen.side_effect = make_http_error(404)

    lookup = repo.lookup(['ZZZZQ'])

    assert lookup.symbols == {}
    assert lookup.failures[0].reason == 'not_found'
    assert lookup.failures[0].attempts == 1
    assert urlopen.call_count == 1

# ** test: lookup_timeout_then_success
def test_lookup_timeout_then_success(repo: YahooChartPriceRepository, urlopen: mock.Mock) -> None:
    '''
    Test that a timeout followed by success returns the symbol, proving the single retry.

    :param repo: The repository.
    :type repo: YahooChartPriceRepository
    :param urlopen: The patched urlopen.
    :type urlopen: mock.Mock
    '''

    urlopen.side_effect = [socket.timeout('timed out'), make_response(read_payload('aapl'))]

    lookup = repo.lookup(['AAPL'])

    assert lookup.symbols['AAPL'].exchange == 'NASDAQ'
    assert lookup.failures == []
    assert urlopen.call_count == 2

# ** test: lookup_timeout_exhausted
def test_lookup_timeout_exhausted(repo: YahooChartPriceRepository, urlopen: mock.Mock) -> None:
    '''
    Test that two timeouts give a timeout failure with two attempts.

    :param repo: The repository.
    :type repo: YahooChartPriceRepository
    :param urlopen: The patched urlopen.
    :type urlopen: mock.Mock
    '''

    urlopen.side_effect = [url_error.URLError(socket.timeout('timed out')), socket.timeout('timed out')]

    lookup = repo.lookup(['AAPL'])

    assert lookup.failures[0].reason == 'timeout'
    assert lookup.failures[0].attempts == 2

# ** test: lookup_http_error
def test_lookup_http_error(repo: YahooChartPriceRepository, urlopen: mock.Mock) -> None:
    '''
    Test that repeated server errors give an http_error failure carrying the status.

    :param repo: The repository.
    :type repo: YahooChartPriceRepository
    :param urlopen: The patched urlopen.
    :type urlopen: mock.Mock
    '''

    urlopen.side_effect = [make_http_error(500), make_http_error(503)]

    lookup = repo.lookup(['AAPL'])

    assert lookup.failures[0].reason == 'http_error'
    assert lookup.failures[0].detail == 'HTTP 503'
    assert lookup.failures[0].attempts == 2

# ** test: lookup_malformed_json
@pytest.mark.parametrize('body', [b'not json', b'{"chart": {"result": [{}]}}', b'{"chart": {"result": null, "error": null}}'])
def test_lookup_malformed_json(repo: YahooChartPriceRepository, urlopen: mock.Mock, body: bytes) -> None:
    '''
    Test that a malformed body is a bad_payload failure.

    :param repo: The repository.
    :type repo: YahooChartPriceRepository
    :param urlopen: The patched urlopen.
    :type urlopen: mock.Mock
    :param body: The malformed response body.
    :type body: bytes
    '''

    urlopen.return_value = make_response(body)

    lookup = repo.lookup(['AAPL'])

    assert lookup.symbols == {}
    assert lookup.failures[0].reason == 'bad_payload'

# ** test: lookup_not_found_body
def test_lookup_not_found_body(repo: YahooChartPriceRepository, urlopen: mock.Mock) -> None:
    '''
    Test that a Not Found chart error body is a not_found failure.

    :param repo: The repository.
    :type repo: YahooChartPriceRepository
    :param urlopen: The patched urlopen.
    :type urlopen: mock.Mock
    '''

    urlopen.return_value = make_response(b'{"chart": {"result": null, "error": {"code": "Not Found", "description": "No data found"}}}')

    lookup = repo.lookup(['ZZZZQ'])

    assert lookup.failures[0].reason == 'not_found'
    assert lookup.failures[0].detail == 'No data found'

# ** test: lookup_many
def test_lookup_many(repo: YahooChartPriceRepository, urlopen: mock.Mock) -> None:
    '''
    Test that a batch returns every id as a result or a failure, and one failure does not fail the batch.

    :param repo: The repository.
    :type repo: YahooChartPriceRepository
    :param urlopen: The patched urlopen.
    :type urlopen: mock.Mock
    '''

    urlopen.side_effect = [make_response(read_payload('spy')), make_http_error(404), make_response(read_payload('tcehy'))]

    lookup = repo.lookup(['SPY', 'ZZZZQ', 'TCEHY', 'SPY'])

    assert list(lookup.symbols) == ['SPY', 'TCEHY']
    assert [failure.symbol_id for failure in lookup.failures] == ['ZZZZQ']
    assert urlopen.call_count == 3

# ** test: lookup_connection_error_then_success
@pytest.mark.parametrize('error', [
    http_client.RemoteDisconnected('Remote end closed connection without response'),
    ConnectionResetError('Connection reset by peer'),
    http_client.IncompleteRead(b'partial'),
])
def test_lookup_connection_error_then_success(repo: YahooChartPriceRepository,
                                              urlopen: mock.Mock,
                                              error: Exception) -> None:
    '''
    Test that a dropped or truncated response is retried and does not abort the lookup.

    :param repo: The repository.
    :type repo: YahooChartPriceRepository
    :param urlopen: The patched urlopen.
    :type urlopen: mock.Mock
    :param error: The connection-level error raised on the first attempt.
    :type error: Exception
    '''

    urlopen.side_effect = [error, make_response(read_payload('aapl'))]

    lookup = repo.lookup(['AAPL'])

    assert lookup.symbols['AAPL'].exchange == 'NASDAQ'
    assert lookup.failures == []
    assert urlopen.call_count == 2

# ** test: lookup_connection_error_exhausted
def test_lookup_connection_error_exhausted(repo: YahooChartPriceRepository, urlopen: mock.Mock) -> None:
    '''
    Test that repeated connection errors become an http_error failure while the rest of the batch resolves.

    :param repo: The repository.
    :type repo: YahooChartPriceRepository
    :param urlopen: The patched urlopen.
    :type urlopen: mock.Mock
    '''

    urlopen.side_effect = [
        http_client.RemoteDisconnected('closed'),
        ConnectionResetError('reset'),
        make_response(read_payload('spy')),
    ]

    lookup = repo.lookup(['AAPL', 'SPY'])

    assert list(lookup.symbols) == ['SPY']
    assert lookup.failures[0].symbol_id == 'AAPL'
    assert lookup.failures[0].reason == 'http_error'
    assert lookup.failures[0].attempts == 2

# ** test: get_quotes_recorded_payload
def test_get_quotes_recorded_payload(repo: YahooChartPriceRepository, urlopen: mock.Mock) -> None:
    '''
    Test that a recorded success payload yields a float-priced quote and the symbol from the same response.

    :param repo: The repository.
    :type repo: YahooChartPriceRepository
    :param urlopen: The patched urlopen.
    :type urlopen: mock.Mock
    '''

    meta = json.loads(read_payload('aapl'))['chart']['result'][0]['meta']
    urlopen.return_value = make_response(read_payload('aapl'))

    quote_set = repo.get_quotes(['AAPL'])
    quote = quote_set.quotes['AAPL']

    assert isinstance(quote.price, float)
    assert quote.price == meta['regularMarketPrice']
    assert quote.previous_close == meta['chartPreviousClose']
    assert quote.change_pct == round((meta['regularMarketPrice'] - meta['chartPreviousClose']) / meta['chartPreviousClose'] * 100, 4)
    assert quote.market_time == datetime.fromtimestamp(meta['regularMarketTime'], tz=timezone.utc).isoformat()
    assert quote.currency == 'USD'
    assert quote.source == 'yahoo_chart'
    assert quote_set.symbols['AAPL'].exchange == 'NASDAQ'
    assert quote_set.failures == []
    assert quote_set.fetched_at

# ** test: get_quotes_carries_symbol_warnings
def test_get_quotes_carries_symbol_warnings(repo: YahooChartPriceRepository, urlopen: mock.Mock) -> None:
    '''
    Test that an unmapped exchange is a soft warning on the quote set, not a failure.

    :param repo: The repository.
    :type repo: YahooChartPriceRepository
    :param urlopen: The patched urlopen.
    :type urlopen: mock.Mock
    '''

    urlopen.return_value = make_response(read_payload('tcehy'))

    quote_set = repo.get_quotes(['TCEHY'])

    assert 'TCEHY' in quote_set.quotes
    assert [(w.reason, w.detail) for w in quote_set.warnings] == [('unmapped_exchange', 'PNK')]
    assert quote_set.failures == []

# ** test: get_quotes_failures
@pytest.mark.parametrize('side_effect, reason, attempts', [
    ([make_http_error(404)], 'not_found', 1),
    ([make_http_error(500), make_http_error(502)], 'http_error', 2),
    ([socket.timeout('timed out'), socket.timeout('timed out')], 'timeout', 2),
])
def test_get_quotes_failures(repo: YahooChartPriceRepository,
                             urlopen: mock.Mock,
                             side_effect: List[Any],
                             reason: str,
                             attempts: int) -> None:
    '''
    Test that provider failures become named quote failures with their attempt counts.

    :param repo: The repository.
    :type repo: YahooChartPriceRepository
    :param urlopen: The patched urlopen.
    :type urlopen: mock.Mock
    :param side_effect: The urlopen outcomes in order.
    :type side_effect: List[Any]
    :param reason: The expected failure reason.
    :type reason: str
    :param attempts: The expected attempt count.
    :type attempts: int
    '''

    urlopen.side_effect = side_effect

    quote_set = repo.get_quotes(['AAPL'])

    assert quote_set.quotes == {}
    assert quote_set.failures[0].reason == reason
    assert quote_set.failures[0].attempts == attempts

# ** test: get_quotes_malformed_json
def test_get_quotes_malformed_json(repo: YahooChartPriceRepository, urlopen: mock.Mock) -> None:
    '''
    Test that malformed JSON is a bad_payload failure.

    :param repo: The repository.
    :type repo: YahooChartPriceRepository
    :param urlopen: The patched urlopen.
    :type urlopen: mock.Mock
    '''

    urlopen.return_value = make_response(b'{not json')

    quote_set = repo.get_quotes(['AAPL'])

    assert quote_set.failures[0].reason == 'bad_payload'

# ** test: get_quotes_missing_price
@pytest.mark.parametrize('price', [None, 'n/a', True, float('nan')])
def test_get_quotes_missing_price(repo: YahooChartPriceRepository, urlopen: mock.Mock, price: Any) -> None:
    '''
    Test that a payload without a numeric price is a bad_payload failure.

    :param repo: The repository.
    :type repo: YahooChartPriceRepository
    :param urlopen: The patched urlopen.
    :type urlopen: mock.Mock
    :param price: The replacement price value.
    :type price: Any
    '''

    payload = json.loads(read_payload('aapl'))
    payload['chart']['result'][0]['meta']['regularMarketPrice'] = price
    urlopen.return_value = make_response(json.dumps(payload).encode())

    quote_set = repo.get_quotes(['AAPL'])

    assert quote_set.quotes == {}
    assert quote_set.failures[0].reason == 'bad_payload'

# ** test: get_quotes_timeout_then_success
def test_get_quotes_timeout_then_success(repo: YahooChartPriceRepository, urlopen: mock.Mock) -> None:
    '''
    Test that a timeout followed by success yields a quote, proving the single retry.

    :param repo: The repository.
    :type repo: YahooChartPriceRepository
    :param urlopen: The patched urlopen.
    :type urlopen: mock.Mock
    '''

    urlopen.side_effect = [socket.timeout('timed out'), make_response(read_payload('spy'))]

    quote_set = repo.get_quotes(['SPY'])

    assert quote_set.quotes['SPY'].source == 'yahoo_chart'
    assert quote_set.failures == []
    assert urlopen.call_count == 2

# ** test: get_quotes_every_id_once
def test_get_quotes_every_id_once(repo: YahooChartPriceRepository, urlopen: mock.Mock) -> None:
    '''
    Test that every requested id appears exactly once, in quotes or in failures.

    :param repo: The repository.
    :type repo: YahooChartPriceRepository
    :param urlopen: The patched urlopen.
    :type urlopen: mock.Mock
    '''

    urlopen.side_effect = [make_response(read_payload('aapl')), make_http_error(404), make_response(read_payload('spy'))]

    quote_set = repo.get_quotes(['AAPL', 'ZZZZQ', 'SPY', 'AAPL'])
    seen = list(quote_set.quotes) + [failure.symbol_id for failure in quote_set.failures]

    assert sorted(seen) == ['AAPL', 'SPY', 'ZZZZQ']
    assert urlopen.call_count == 3

# ** test: init_clamps_negative_retries
def test_init_clamps_negative_retries() -> None:
    '''
    Test that a negative retries value still makes one attempt.
    '''

    assert YahooChartPriceRepository(retries='-1').retries == 0

# ** test: get_quotes_unusable_previous_close
@pytest.mark.parametrize('previous_close', ['250.0', True, float('nan'), -50.0, 0])
def test_get_quotes_unusable_previous_close(repo: YahooChartPriceRepository,
                                            urlopen: mock.Mock,
                                            previous_close: Any) -> None:
    '''
    Test that an unusable previous close leaves previous_close and change_pct empty but keeps the quote.

    :param repo: The repository.
    :type repo: YahooChartPriceRepository
    :param urlopen: The patched urlopen.
    :type urlopen: mock.Mock
    :param previous_close: The replacement previous close value.
    :type previous_close: Any
    '''

    payload = json.loads(read_payload('aapl'))
    payload['chart']['result'][0]['meta']['chartPreviousClose'] = previous_close
    urlopen.return_value = make_response(json.dumps(payload).encode())

    quote = repo.get_quotes(['AAPL']).quotes['AAPL']

    assert quote.previous_close is None
    assert quote.change_pct is None

# ** test: init_source_default
def test_init_source_default() -> None:
    '''
    Test that the default source matches the catalogued Yahoo chart provider id and can be overridden.
    '''

    assert YahooChartPriceRepository().source == a.YAHOO_CHART_PROVIDER_ID
    assert YahooChartPriceRepository(source='yahoo_alt').source == 'yahoo_alt'
