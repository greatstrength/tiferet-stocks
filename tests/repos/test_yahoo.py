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
from urllib import parse

# ** infra
import pytest

# ** app
from tiferet_stocks import assets as a
from tiferet_stocks.mappers import PriceHistoryAggregate, QuotationsAggregate
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

# ** function: history_payload
def history_payload(timestamps: List[Any], closes: List[Any], gmtoffset: Any = -14400) -> bytes:
    '''
    Build a synthetic daily chart body with one price for each bar column.

    :param timestamps: The bar timestamps in epoch seconds.
    :type timestamps: List[Any]
    :param closes: The price for each bar, used for open, high, low and close.
    :type closes: List[Any]
    :param gmtoffset: The exchange offset from UTC in seconds.
    :type gmtoffset: Any
    :return: The response body.
    :rtype: bytes
    '''

    # Build and return the body.
    series = {name: list(closes) for name in ('open', 'high', 'low', 'close')}
    series['volume'] = [1000] * len(closes)
    return json.dumps({'chart': {'result': [{
        'meta': {'symbol': 'AAPL', 'gmtoffset': gmtoffset},
        'timestamp': timestamps,
        'indicators': {'quote': [series], 'adjclose': [{'adjclose': list(closes)}]},
    }], 'error': None}}).encode()

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

    quotations = repo.get_quotes(['AAPL'])
    assert isinstance(quotations, QuotationsAggregate)
    quote = quotations.quotes['AAPL']

    assert isinstance(quote.price, float)
    assert quote.price == meta['regularMarketPrice']
    assert quote.previous_close == meta['chartPreviousClose']
    assert quote.change_pct == round((meta['regularMarketPrice'] - meta['chartPreviousClose']) / meta['chartPreviousClose'] * 100, 4)
    assert quote.market_time == datetime.fromtimestamp(meta['regularMarketTime'], tz=timezone.utc).isoformat()
    assert quote.currency == 'USD'
    assert quote.source == 'yahoo_chart'
    assert quotations.symbols['AAPL'].exchange == 'NASDAQ'
    assert quotations.failures == []
    assert quotations.fetched_at

# ** test: get_quotes_carries_symbol_warnings
def test_get_quotes_carries_symbol_warnings(repo: YahooChartPriceRepository, urlopen: mock.Mock) -> None:
    '''
    Test that an unmapped exchange is a soft warning on the quotations, not a failure.

    :param repo: The repository.
    :type repo: YahooChartPriceRepository
    :param urlopen: The patched urlopen.
    :type urlopen: mock.Mock
    '''

    urlopen.return_value = make_response(read_payload('tcehy'))

    quotations = repo.get_quotes(['TCEHY'])

    assert 'TCEHY' in quotations.quotes
    assert [(w.reason, w.detail) for w in quotations.warnings] == [('unmapped_exchange', 'PNK')]
    assert quotations.failures == []

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

    quotations = repo.get_quotes(['AAPL'])

    assert quotations.quotes == {}
    assert quotations.failures[0].reason == reason
    assert quotations.failures[0].attempts == attempts

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

    quotations = repo.get_quotes(['AAPL'])

    assert quotations.failures[0].reason == 'bad_payload'

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

    quotations = repo.get_quotes(['AAPL'])

    assert quotations.quotes == {}
    assert quotations.failures[0].reason == 'bad_payload'

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

    quotations = repo.get_quotes(['SPY'])

    assert quotations.quotes['SPY'].source == 'yahoo_chart'
    assert quotations.failures == []
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

    quotations = repo.get_quotes(['AAPL', 'ZZZZQ', 'SPY', 'AAPL'])
    seen = list(quotations.quotes) + [failure.symbol_id for failure in quotations.failures]

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

# ** test: get_quotes_unusable_market_time
@pytest.mark.parametrize('market_time', [1e20, -1e20, 1e18, 3e11, float('nan'), True, 'soon'])
def test_get_quotes_unusable_market_time(repo: YahooChartPriceRepository,
                                         urlopen: mock.Mock,
                                         market_time: Any) -> None:
    '''
    Test that an unusable or out-of-range market time keeps the quote with market_time empty and keeps the rest of the batch.

    :param repo: The repository.
    :type repo: YahooChartPriceRepository
    :param urlopen: The patched urlopen.
    :type urlopen: mock.Mock
    :param market_time: The replacement market time value.
    :type market_time: Any
    '''

    payload = json.loads(read_payload('aapl'))
    payload['chart']['result'][0]['meta']['regularMarketTime'] = market_time
    urlopen.side_effect = [
        make_response(json.dumps(payload).encode()),
        make_response(read_payload('spy')),
    ]

    quotations = repo.get_quotes(['AAPL', 'SPY'])

    assert quotations.quotes['AAPL'].market_time is None
    assert quotations.quotes['SPY'].market_time is not None
    assert quotations.failures == []

# ** test: get_quotes_source_override
def test_get_quotes_source_override(urlopen: mock.Mock) -> None:
    '''
    Test that a configured source reaches each quote.

    :param urlopen: The patched urlopen.
    :type urlopen: mock.Mock
    '''

    urlopen.return_value = make_response(read_payload('aapl'))

    quotations = YahooChartPriceRepository(source='alt').get_quotes(['AAPL'])

    assert quotations.quotes['AAPL'].source == 'alt'

# ** test: get_history_recorded_payload
def test_get_history_recorded_payload(repo: YahooChartPriceRepository, urlopen: mock.Mock) -> None:
    '''
    Test that a recorded history payload yields float and int bars, oldest first, within the inclusive range.

    :param repo: The repository.
    :type repo: YahooChartPriceRepository
    :param urlopen: The patched urlopen.
    :type urlopen: mock.Mock
    '''

    urlopen.return_value = make_response(read_payload('aapl_history'))

    history = repo.get_history('AAPL', '2026-10-20', '2026-10-22')

    assert isinstance(history, PriceHistoryAggregate)
    assert history.failure is None
    assert [bar.date for bar in history.bars] == ['2026-10-20', '2026-10-21', '2026-10-22']
    bar = history.bars[0]
    assert bar.symbol_id == 'AAPL'
    assert all(isinstance(value, float) for value in (bar.open, bar.high, bar.low, bar.close, bar.adj_close))
    assert isinstance(bar.volume, int) and not isinstance(bar.volume, bool)
    assert bar.close == 339.5
    assert bar.volume == 35851400

# ** test: get_history_request_params
def test_get_history_request_params(repo: YahooChartPriceRepository, urlopen: mock.Mock) -> None:
    '''
    Test that the history request carries period1, period2 and interval=1d, widened by one UTC day on each side of the range.

    :param repo: The repository.
    :type repo: YahooChartPriceRepository
    :param urlopen: The patched urlopen.
    :type urlopen: mock.Mock
    '''

    urlopen.return_value = make_response(read_payload('aapl_history'))

    repo.get_history('AAPL', '2026-10-19', '2026-10-23')

    url = urlopen.call_args[0][0].full_url
    query = parse.parse_qs(parse.urlsplit(url).query)
    assert query['interval'] == ['1d']
    assert query['period1'] == [str(int(datetime(2026, 10, 18, tzinfo=timezone.utc).timestamp()))]
    assert query['period2'] == [str(int(datetime(2026, 10, 25, tzinfo=timezone.utc).timestamp()))]
    assert '/chart/AAPL?' in url

# ** test: get_history_empty_range
def test_get_history_empty_range(repo: YahooChartPriceRepository, urlopen: mock.Mock) -> None:
    '''
    Test that a recorded range with no trading days yields no bars and no failure.

    :param repo: The repository.
    :type repo: YahooChartPriceRepository
    :param urlopen: The patched urlopen.
    :type urlopen: mock.Mock
    '''

    urlopen.return_value = make_response(read_payload('aapl_history_empty'))

    history = repo.get_history('AAPL', '2026-10-24', '2026-10-25')

    assert history.bars == []
    assert history.failure is None

# ** test: get_history_timeout_then_success
def test_get_history_timeout_then_success(repo: YahooChartPriceRepository, urlopen: mock.Mock) -> None:
    '''
    Test that one timeout followed by success yields bars (single retry).

    :param repo: The repository.
    :type repo: YahooChartPriceRepository
    :param urlopen: The patched urlopen.
    :type urlopen: mock.Mock
    '''

    urlopen.side_effect = [socket.timeout('timed out'), make_response(read_payload('aapl_history'))]

    history = repo.get_history('AAPL', '2026-10-19', '2026-10-23')

    assert len(history.bars) == 5
    assert history.failure is None
    assert urlopen.call_count == 2

# ** test: get_history_failures
@pytest.mark.parametrize('side_effect, reason, attempts', [
    ([make_http_error(404)], 'not_found', 1),
    ([make_http_error(500), make_http_error(502)], 'http_error', 2),
    ([socket.timeout('timed out'), socket.timeout('timed out')], 'timeout', 2),
    ([make_response(b'not json')], 'bad_payload', 1),
])
def test_get_history_failures(repo: YahooChartPriceRepository,
                              urlopen: mock.Mock,
                              side_effect: List[Any],
                              reason: str,
                              attempts: int) -> None:
    '''
    Test that provider failures come back as the history failure with their reason and attempts.

    :param repo: The repository.
    :type repo: YahooChartPriceRepository
    :param urlopen: The patched urlopen.
    :type urlopen: mock.Mock
    :param side_effect: The urlopen results in order.
    :type side_effect: List[Any]
    :param reason: The expected failure reason.
    :type reason: str
    :param attempts: The expected number of attempts.
    :type attempts: int
    '''

    urlopen.side_effect = side_effect

    history = repo.get_history('AAPL', '2026-10-19', '2026-10-23')

    assert isinstance(history, PriceHistoryAggregate)
    assert history.bars == []
    assert (history.failure.reason, history.failure.attempts) == (reason, attempts)

# ** test: get_history_skips_null_bars
def test_get_history_skips_null_bars(repo: YahooChartPriceRepository, urlopen: mock.Mock) -> None:
    '''
    Test that a day Yahoo pads with null prices is skipped, and out-of-order bars are returned oldest first.

    :param repo: The repository.
    :type repo: YahooChartPriceRepository
    :param urlopen: The patched urlopen.
    :type urlopen: mock.Mock
    '''

    stamps = [1792503000, 1792416600, 1792589400]
    urlopen.return_value = make_response(history_payload(stamps, [2.0, 1.0, None]))

    history = repo.get_history('AAPL', '2026-10-19', '2026-10-23')

    assert [(bar.date, bar.close) for bar in history.bars] == [('2026-10-19', 1.0), ('2026-10-20', 2.0)]

# ** test: get_history_exchange_day
@pytest.mark.parametrize('stamp, gmtoffset, day', [
    (1792461600, -14400, '2026-10-19'),
    (1792461600, 32400, '2026-10-20'),
    (1792461600, None, '2026-10-20'),
])
def test_get_history_exchange_day(repo: YahooChartPriceRepository,
                                  urlopen: mock.Mock,
                                  stamp: int,
                                  gmtoffset: Any,
                                  day: str) -> None:
    '''
    Test that each bar is dated in the exchange time zone, falling back to UTC without an offset.

    :param repo: The repository.
    :type repo: YahooChartPriceRepository
    :param urlopen: The patched urlopen.
    :type urlopen: mock.Mock
    :param stamp: The bar timestamp (2026-10-20 02:00 UTC).
    :type stamp: int
    :param gmtoffset: The exchange offset from UTC in seconds.
    :type gmtoffset: Any
    :param day: The expected bar date.
    :type day: str
    '''

    urlopen.return_value = make_response(history_payload([stamp], [1.0], gmtoffset))

    history = repo.get_history('AAPL', '2026-10-19', '2026-10-20')

    assert [bar.date for bar in history.bars] == [day]

# ** test: get_history_malformed_series
@pytest.mark.parametrize('mutate', [
    lambda result: result['indicators']['quote'][0].update(close=[1.0]),
    lambda result: result['indicators']['quote'][0].pop('close'),
    lambda result: result.update(indicators={'quote': ['bad']}),
    lambda result: result.update(timestamp=[1e20]),
])
def test_get_history_malformed_series(repo: YahooChartPriceRepository, urlopen: mock.Mock, mutate) -> None:
    '''
    Test that a series that does not line up with its timestamps is a bad_payload failure.

    :param repo: The repository.
    :type repo: YahooChartPriceRepository
    :param urlopen: The patched urlopen.
    :type urlopen: mock.Mock
    :param mutate: A function that breaks the chart result.
    :type mutate: Callable
    '''

    payload = json.loads(history_payload([1792416600, 1792503000], [1.0, 2.0]))
    mutate(payload['chart']['result'][0])
    urlopen.return_value = make_response(json.dumps(payload).encode())

    history = repo.get_history('AAPL', '2026-10-19', '2026-10-23')

    assert history.bars == []
    assert history.failure.reason == 'bad_payload'

# ** test: init_history_url
def test_init_history_url(urlopen: mock.Mock) -> None:
    '''
    Test that history_url is overridable from configuration.

    :param urlopen: The patched urlopen.
    :type urlopen: mock.Mock
    '''

    urlopen.return_value = make_response(read_payload('aapl_history_empty'))

    YahooChartPriceRepository(history_url='https://example.test/{symbol}/{period1}/{period2}').get_history('AAPL', '2026-10-24', '2026-10-25')

    assert urlopen.call_args[0][0].full_url.startswith('https://example.test/AAPL/')

# ** test: get_history_max_end_date
def test_get_history_max_end_date(repo: YahooChartPriceRepository, urlopen: mock.Mock) -> None:
    '''
    Test that the last representable date does not overflow the request window.

    :param repo: The repository.
    :type repo: YahooChartPriceRepository
    :param urlopen: The patched urlopen.
    :type urlopen: mock.Mock
    '''

    urlopen.return_value = make_response(read_payload('aapl_history_empty'))

    history = repo.get_history('AAPL', '9999-12-30', '9999-12-31')

    assert (history.bars, history.failure) == ([], None)
    query = parse.parse_qs(parse.urlsplit(urlopen.call_args[0][0].full_url).query)
    assert query['period2'] == [str(int(datetime(9999, 12, 31, tzinfo=timezone.utc).timestamp()) + 2 * 86400)]

# ** test: get_history_ahead_of_utc_keeps_start_day
def test_get_history_ahead_of_utc_keeps_start_day(repo: YahooChartPriceRepository, urlopen: mock.Mock) -> None:
    '''
    Test that a bar on the start day of an exchange ahead of UTC, stamped on the prior UTC day, is kept.

    :param repo: The repository.
    :type repo: YahooChartPriceRepository
    :param urlopen: The patched urlopen.
    :type urlopen: mock.Mock
    '''

    # 2026-10-19 00:00 UTC minus 9 hours is 2026-10-18 15:00 UTC, which is 2026-10-19 00:00 at +09:00.
    stamp = int(datetime(2026, 10, 18, 15, tzinfo=timezone.utc).timestamp())
    urlopen.return_value = make_response(history_payload([stamp], [1.0], 32400))

    history = repo.get_history('AAPL', '2026-10-19', '2026-10-19')

    assert [bar.date for bar in history.bars] == ['2026-10-19']
    query = parse.parse_qs(parse.urlsplit(urlopen.call_args[0][0].full_url).query)
    assert int(query['period1'][0]) <= stamp

# ** test: get_history_malformed_shapes
@pytest.mark.parametrize('mutate', [
    lambda result: result.update(timestamp=5),
    lambda result: result['indicators'].update(quote={'close': [1.0, 2.0]}),
    lambda result: result['indicators'].update(adjclose={'adjclose': [1.0, 2.0]}),
])
def test_get_history_malformed_shapes(repo: YahooChartPriceRepository, urlopen: mock.Mock, mutate) -> None:
    '''
    Test that a non-list timestamp or a quote or adjclose sent as a dict is a bad_payload failure, not an exception.

    :param repo: The repository.
    :type repo: YahooChartPriceRepository
    :param urlopen: The patched urlopen.
    :type urlopen: mock.Mock
    :param mutate: A function that breaks the chart result.
    :type mutate: Callable
    '''

    payload = json.loads(history_payload([1792416600, 1792503000], [1.0, 2.0]))
    mutate(payload['chart']['result'][0])
    urlopen.return_value = make_response(json.dumps(payload).encode())

    history = repo.get_history('AAPL', '2026-10-19', '2026-10-23')

    assert history.bars == []
    assert history.failure.reason == 'bad_payload'

# ** test: get_history_unusable_timestamps
@pytest.mark.parametrize('stamp', [3e11, 1e20, True, 'NaN'])
def test_get_history_unusable_timestamps(repo: YahooChartPriceRepository, urlopen: mock.Mock, stamp: Any) -> None:
    '''
    Test that an out-of-range, boolean or non-finite timestamp is a bad_payload failure.

    :param repo: The repository.
    :type repo: YahooChartPriceRepository
    :param urlopen: The patched urlopen.
    :type urlopen: mock.Mock
    :param stamp: The timestamp ('NaN' becomes a JSON NaN).
    :type stamp: Any
    '''

    body = history_payload([1792416600, 0], [1.0, 2.0]).replace(b'0], ', (b'NaN' if stamp == 'NaN' else json.dumps(stamp).encode()) + b'], ', 1)
    urlopen.return_value = make_response(body)

    history = repo.get_history('AAPL', '2026-10-19', '2026-10-23')

    assert history.bars == []
    assert history.failure.reason == 'bad_payload'

# ** test: get_history_unusable_price
@pytest.mark.parametrize('price', [float('nan'), float('inf'), True, '1.0', None])
def test_get_history_unusable_price(repo: YahooChartPriceRepository, urlopen: mock.Mock, price: Any) -> None:
    '''
    Test that an unusable price, including one null price on an otherwise priced day, is a bad_payload failure, unlike a day padded with nulls.

    :param repo: The repository.
    :type repo: YahooChartPriceRepository
    :param urlopen: The patched urlopen.
    :type urlopen: mock.Mock
    :param price: The unusable price.
    :type price: Any
    '''

    payload = json.loads(history_payload([1792416600], [1.0]))
    payload['chart']['result'][0]['indicators']['quote'][0]['high'] = [price]
    urlopen.return_value = make_response(json.dumps(payload).encode())

    history = repo.get_history('AAPL', '2026-10-19', '2026-10-23')

    assert history.bars == []
    assert history.failure.reason == 'bad_payload'

# ** test: get_history_unusable_optional_values
@pytest.mark.parametrize('value', [float('nan'), float('inf'), True, '7'])
def test_get_history_unusable_optional_values(repo: YahooChartPriceRepository, urlopen: mock.Mock, value: Any) -> None:
    '''
    Test that an unusable adj_close or volume is dropped to None while the bar is kept.

    :param repo: The repository.
    :type repo: YahooChartPriceRepository
    :param urlopen: The patched urlopen.
    :type urlopen: mock.Mock
    :param value: The unusable value.
    :type value: Any
    '''

    payload = json.loads(history_payload([1792416600], [1.0]))
    result = payload['chart']['result'][0]
    result['indicators']['quote'][0]['volume'] = [value]
    result['indicators']['adjclose'][0]['adjclose'] = [value]
    urlopen.return_value = make_response(json.dumps(payload).encode())

    history = repo.get_history('AAPL', '2026-10-19', '2026-10-23')

    assert [(bar.adj_close, bar.volume) for bar in history.bars] == [(None, None)]

# ** test: get_history_adj_close_source
def test_get_history_adj_close_source(repo: YahooChartPriceRepository, urlopen: mock.Mock) -> None:
    '''
    Test that adj_close comes from indicators.adjclose, not the close column.

    :param repo: The repository.
    :type repo: YahooChartPriceRepository
    :param urlopen: The patched urlopen.
    :type urlopen: mock.Mock
    '''

    payload = json.loads(history_payload([1792416600], [10.0]))
    payload['chart']['result'][0]['indicators']['adjclose'][0]['adjclose'] = [9.5]
    urlopen.return_value = make_response(json.dumps(payload).encode())

    history = repo.get_history('AAPL', '2026-10-19', '2026-10-23')

    assert [(bar.close, bar.adj_close) for bar in history.bars] == [(10.0, 9.5)]

# ** test: get_history_duplicate_day_keeps_last
def test_get_history_duplicate_day_keeps_last(repo: YahooChartPriceRepository, urlopen: mock.Mock) -> None:
    '''
    Test that two timestamps on one exchange day give one bar, the last one sent.

    :param repo: The repository.
    :type repo: YahooChartPriceRepository
    :param urlopen: The patched urlopen.
    :type urlopen: mock.Mock
    '''

    urlopen.return_value = make_response(history_payload([1792416600, 1792430000], [1.0, 2.0]))

    history = repo.get_history('AAPL', '2026-10-19', '2026-10-23')

    assert [(bar.date, bar.close) for bar in history.bars] == [('2026-10-19', 2.0)]
