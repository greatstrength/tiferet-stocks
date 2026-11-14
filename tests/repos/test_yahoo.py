"""Tiferet Stocks Yahoo Repository Tests"""

# *** imports

# ** core
from email.message import Message
import io
import json
import os
from datetime import datetime, timezone
import socket
from typing import Any, List
from unittest import mock
from urllib import error as url_error
from urllib import parse

# ** infra
import pytest

# ** app
from tiferet_stocks import assets as a
from tiferet_stocks.mappers import PriceHistoryAggregate, QuoteListAggregate
from tiferet_stocks.repos.yahoo import (
    YAHOO_ASSET_TYPE_MAP,
    YAHOO_EXCHANGE_MAP,
    YahooChartPriceRepository,
)
from tests.repos.yahoo_recorded import (
    RECORDED_COOKIE,
    RECORDED_CRUMB,
    recorded_yahoo,
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
def make_http_error(code: int, body: bytes = b'', headers: dict | None = None) -> url_error.HTTPError:
    '''
    Build an HTTP error with the given status code, body and headers.

    :param code: The HTTP status code.
    :type code: int
    :param body: The response body.
    :type body: bytes
    :param headers: The response headers.
    :type headers: dict | None
    :return: The HTTP error.
    :rtype: url_error.HTTPError
    '''

    # Build and return the error with a real header message.
    message = Message()
    for key, value in (headers or {}).items():
        message[key] = value
    return url_error.HTTPError('https://example.test', code, 'error', message, io.BytesIO(body))

# ** function: batch_rows
def batch_rows(**changes: dict) -> List[dict]:
    '''
    Read the recorded batch quote rows, with field changes applied per ticker.

    :param changes: Field values to replace, by ticker.
    :type changes: dict
    :return: The result rows.
    :rtype: List[dict]
    '''

    # Copy the recorded rows and apply each change.
    rows = json.loads(read_payload('quote_batch'))['quoteResponse']['result']
    for row in rows:
        row.update(changes.get(row['symbol'].replace('-', '_'), {}))
    return rows

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

# ** test: get_quotes_one_batch_request
def test_get_quotes_one_batch_request(repo: YahooChartPriceRepository, urlopen: mock.Mock) -> None:
    '''
    Test that a list of symbols is quoted in one batch request, in request order, from the recorded response.

    :param repo: The repository.
    :type repo: YahooChartPriceRepository
    :param urlopen: The patched urlopen.
    :type urlopen: mock.Mock
    '''

    requested = []
    urlopen.side_effect = recorded_yahoo(requested)
    rows = {row['symbol']: row for row in json.loads(read_payload('quote_batch'))['quoteResponse']['result']}

    quotes = repo.get_quotes(['AAPL', 'BRK-B', 'SPY', 'FRSXX'])

    assert requested == ['cookie', 'crumb', 'quote:AAPL,BRK-B,SPY,FRSXX']
    assert isinstance(quotes, QuoteListAggregate)
    assert [quote.symbol_id for quote in quotes.quotes] == ['AAPL', 'BRK-B', 'SPY', 'FRSXX']
    aapl = quotes.get_quote('AAPL')
    assert isinstance(aapl.price, float)
    assert aapl.price == rows['AAPL']['regularMarketPrice']
    assert aapl.previous_close == rows['AAPL']['regularMarketPreviousClose']
    assert aapl.change_pct == round((aapl.price - aapl.previous_close) / aapl.previous_close * 100, 4)
    assert aapl.market_time == datetime.fromtimestamp(rows['AAPL']['regularMarketTime'], tz=timezone.utc).isoformat()
    assert aapl.currency == 'USD'
    assert aapl.source == 'yahoo_quote'
    assert quotes.get_quote('FRSXX').previous_close is None
    assert [(symbol_id, symbol.exchange, symbol.asset_type) for symbol_id, symbol in quotes.symbols.items()] == [
        ('AAPL', 'NASDAQ', 'equity'),
        ('BRK-B', 'NYSE', 'equity'),
        ('SPY', 'NYSE_ARCA', 'etf'),
        ('FRSXX', None, 'money_market_fund'),
    ]
    assert quotes.symbols['AAPL'].name == rows['AAPL']['longName']
    assert quotes.warnings == []
    assert quotes.failures == []
    assert quotes.fetched_at

# ** test: get_quotes_omitted_ticker_not_found
def test_get_quotes_omitted_ticker_not_found(repo: YahooChartPriceRepository, urlopen: mock.Mock) -> None:
    '''
    Test that a ticker Yahoo omits is a not_found failure, every id appears once, and nothing raises.

    :param repo: The repository.
    :type repo: YahooChartPriceRepository
    :param urlopen: The patched urlopen.
    :type urlopen: mock.Mock
    '''

    requested = []
    urlopen.side_effect = recorded_yahoo(requested)

    quotes = repo.get_quotes(['AAPL', 'ZZZZQ', 'SPY', 'AAPL'])

    assert requested[-1] == 'quote:AAPL,ZZZZQ,SPY'
    assert [quote.symbol_id for quote in quotes.quotes] == ['AAPL', 'SPY']
    assert [(f.symbol_id, f.reason, f.attempts) for f in quotes.failures] == [('ZZZZQ', 'not_found', 1)]

# ** test: get_quotes_matches_ticker_case
def test_get_quotes_matches_ticker_case(repo: YahooChartPriceRepository, urlopen: mock.Mock) -> None:
    '''
    Test that a lower-case request matches Yahoo's upper-case row and keeps the requested id on the quote.

    :param repo: The repository.
    :type repo: YahooChartPriceRepository
    :param urlopen: The patched urlopen.
    :type urlopen: mock.Mock
    '''

    urlopen.side_effect = recorded_yahoo()

    quotes = repo.get_quotes(['aapl'])

    assert quotes.get_quote('aapl') is not None
    assert quotes.symbols['aapl'].id == 'AAPL'

# ** test: get_quotes_empty_request
def test_get_quotes_empty_request(repo: YahooChartPriceRepository, urlopen: mock.Mock) -> None:
    '''
    Test that an empty request returns an empty quote list without any request, including the session.

    :param repo: The repository.
    :type repo: YahooChartPriceRepository
    :param urlopen: The patched urlopen.
    :type urlopen: mock.Mock
    '''

    quotes = repo.get_quotes([])

    assert quotes.quotes == [] and quotes.failures == []
    urlopen.assert_not_called()

# ** test: get_quotes_reuses_session
def test_get_quotes_reuses_session(repo: YahooChartPriceRepository, urlopen: mock.Mock) -> None:
    '''
    Test that the cookie and crumb are fetched once and reused, so a second crumb is not requested in the same window.

    :param repo: The repository.
    :type repo: YahooChartPriceRepository
    :param urlopen: The patched urlopen.
    :type urlopen: mock.Mock
    '''

    requested = []
    urlopen.side_effect = recorded_yahoo(requested)

    repo.get_quotes(['AAPL'])
    repo.get_quotes(['SPY'])

    assert requested == ['cookie', 'crumb', 'quote:AAPL', 'quote:SPY']
    assert repo.session.cookie == RECORDED_COOKIE
    assert repo.session.crumb == RECORDED_CRUMB

# ** test: get_quotes_rejected_session_reopened
def test_get_quotes_rejected_session_reopened(repo: YahooChartPriceRepository, urlopen: mock.Mock) -> None:
    '''
    Test that a 401 on the quote request drops the session and the retry opens a new one.

    :param repo: The repository.
    :type repo: YahooChartPriceRepository
    :param urlopen: The patched urlopen.
    :type urlopen: mock.Mock
    '''

    requested = []
    recorded = recorded_yahoo(requested)
    rejected = []
    def urlopen_once_unauthorized(req, timeout=None):
        if '/v7/finance/quote' in req.full_url and not rejected:
            rejected.append(req.full_url)
            requested.append('quote:401')
            raise make_http_error(401, read_payload('quote_unauthorized'))
        return recorded(req, timeout)
    urlopen.side_effect = urlopen_once_unauthorized

    quotes = repo.get_quotes(['AAPL'])

    assert requested == ['cookie', 'crumb', 'quote:401', 'cookie', 'crumb', 'quote:AAPL']
    assert quotes.get_quote('AAPL') is not None
    assert quotes.failures == []

# ** test: get_quotes_batch_failures
@pytest.mark.parametrize('failure, reason, detail, attempts', [
    (lambda: make_http_error(500), 'http_error', 'HTTP 500', 2),
    (lambda: socket.timeout('timed out'), 'timeout', 'No response within 5.0 seconds', 2),
    (lambda: url_error.URLError(socket.timeout('timed out')), 'timeout', 'No response within 5.0 seconds', 2),
    (lambda: url_error.URLError('connection refused'), 'http_error', 'connection refused', 2),
    (lambda: make_http_error(401), 'http_error', 'HTTP 401', 2),
    (lambda: make_http_error(429), 'http_error', 'HTTP 429', 1),
])
def test_get_quotes_batch_failures(repo: YahooChartPriceRepository,
                                   urlopen: mock.Mock,
                                   failure: Any,
                                   reason: str,
                                   detail: str,
                                   attempts: int) -> None:
    '''
    Test that a batch-level failure after retries is recorded on every requested id; rate limiting is not retried.

    :param repo: The repository.
    :type repo: YahooChartPriceRepository
    :param urlopen: The patched urlopen.
    :type urlopen: mock.Mock
    :param failure: Builds the error each quote request raises.
    :type failure: Any
    :param reason: The expected failure reason.
    :type reason: str
    :param detail: The expected failure detail.
    :type detail: str
    :param attempts: The expected attempt count.
    :type attempts: int
    '''

    requested = []
    recorded = recorded_yahoo(requested)
    def urlopen_failing_quote(req, timeout=None):
        if '/v7/finance/quote' in req.full_url:
            requested.append('quote')
            raise failure()
        return recorded(req, timeout)
    urlopen.side_effect = urlopen_failing_quote

    quotes = repo.get_quotes(['AAPL', 'SPY'])

    assert quotes.quotes == []
    assert [(f.symbol_id, f.reason, f.detail, f.attempts) for f in quotes.failures] == [
        ('AAPL', reason, detail, attempts),
        ('SPY', reason, detail, attempts),
    ]
    assert requested.count('quote') == attempts

# ** test: get_quotes_session_failures
@pytest.mark.parametrize('cookie_headers, crumb, reason, detail, quote_attempts', [
    ({}, b'recorded.crumb', 'http_error', 'Session cookie: no cookie was set.', 0),
    ({'Set-Cookie': 'A3=d=recorded-anonymous-cookie; Path=/'}, make_http_error(429), 'http_error', 'Session crumb: HTTP 429', 0),
    ({'Set-Cookie': 'A3=d=recorded-anonymous-cookie; Path=/'}, b'{"finance":{"error":"Unauthorized"}}', 'bad_payload', 'Session crumb: unreadable crumb response.', 0),
])
def test_get_quotes_session_failures(repo: YahooChartPriceRepository,
                                     urlopen: mock.Mock,
                                     cookie_headers: dict,
                                     crumb: Any,
                                     reason: str,
                                     detail: str,
                                     quote_attempts: int) -> None:
    '''
    Test that a session that cannot open becomes a failure on every id and makes no quote request.

    :param repo: The repository.
    :type repo: YahooChartPriceRepository
    :param urlopen: The patched urlopen.
    :type urlopen: mock.Mock
    :param cookie_headers: The cookie host response headers.
    :type cookie_headers: dict
    :param crumb: The crumb body, or the error the crumb request raises.
    :type crumb: Any
    :param reason: The expected failure reason.
    :type reason: str
    :param detail: The expected failure detail.
    :type detail: str
    :param quote_attempts: The expected number of quote requests.
    :type quote_attempts: int
    '''

    requested = []
    def urlopen_session(req, timeout=None):
        url = parse.urlsplit(req.full_url)
        if url.netloc == 'fc.yahoo.com':
            requested.append('cookie')
            raise make_http_error(404, headers=cookie_headers)
        if url.path == '/v1/test/getcrumb':
            requested.append('crumb')
            if isinstance(crumb, Exception):
                raise crumb
            return make_response(crumb)
        requested.append('quote')
        raise AssertionError('quote requested without a session')
    urlopen.side_effect = urlopen_session

    quotes = repo.get_quotes(['AAPL'])

    assert [(f.reason, f.detail) for f in quotes.failures] == [(reason, detail)]
    assert requested.count('quote') == quote_attempts
    assert not repo.session.is_open()

# ** test: get_quotes_rate_limited_crumb_not_retried
def test_get_quotes_rate_limited_crumb_not_retried(repo: YahooChartPriceRepository, urlopen: mock.Mock) -> None:
    '''
    Test that a 429 on the crumb is not retried within the same call.

    :param repo: The repository.
    :type repo: YahooChartPriceRepository
    :param urlopen: The patched urlopen.
    :type urlopen: mock.Mock
    '''

    requested = []
    recorded = recorded_yahoo(requested)
    def urlopen_rate_limited(req, timeout=None):
        if '/v1/test/getcrumb' in req.full_url:
            requested.append('crumb:429')
            raise make_http_error(429)
        return recorded(req, timeout)
    urlopen.side_effect = urlopen_rate_limited

    quotes = repo.get_quotes(['AAPL'])

    assert requested == ['cookie', 'crumb:429']
    assert quotes.failures[0].attempts == 1

# ** test: get_quotes_timeout_then_success
def test_get_quotes_timeout_then_success(repo: YahooChartPriceRepository, urlopen: mock.Mock) -> None:
    '''
    Test that a timed-out batch is retried as a whole and keeps the open session.

    :param repo: The repository.
    :type repo: YahooChartPriceRepository
    :param urlopen: The patched urlopen.
    :type urlopen: mock.Mock
    '''

    requested = []
    recorded = recorded_yahoo(requested)
    timed_out = []
    def urlopen_timeout_once(req, timeout=None):
        if '/v7/finance/quote' in req.full_url and not timed_out:
            timed_out.append(req.full_url)
            requested.append('quote:timeout')
            raise socket.timeout('timed out')
        return recorded(req, timeout)
    urlopen.side_effect = urlopen_timeout_once

    quotes = repo.get_quotes(['AAPL', 'SPY'])

    assert requested == ['cookie', 'crumb', 'quote:timeout', 'quote:AAPL,SPY']
    assert [quote.symbol_id for quote in quotes.quotes] == ['AAPL', 'SPY']
    assert quotes.failures == []

# ** test: get_quotes_malformed_json
@pytest.mark.parametrize('body', [b'{not json', b'{"quoteResponse": null}', b'{"finance": {}}', b'{"quoteResponse": {"result": 5}}'])
def test_get_quotes_malformed_json(repo: YahooChartPriceRepository, urlopen: mock.Mock, body: bytes) -> None:
    '''
    Test that an unreadable batch body is a bad_payload failure on every requested id.

    :param repo: The repository.
    :type repo: YahooChartPriceRepository
    :param urlopen: The patched urlopen.
    :type urlopen: mock.Mock
    :param body: The replacement quote body.
    :type body: bytes
    '''

    recorded = recorded_yahoo()
    def urlopen_malformed(req, timeout=None):
        if '/v7/finance/quote' in req.full_url:
            return make_response(body)
        return recorded(req, timeout)
    urlopen.side_effect = urlopen_malformed

    quotes = repo.get_quotes(['AAPL', 'SPY'])

    assert [(f.symbol_id, f.reason) for f in quotes.failures] == [('AAPL', 'bad_payload'), ('SPY', 'bad_payload')]

# ** test: get_quotes_missing_price
@pytest.mark.parametrize('price', [None, 'n/a', True, float('nan')])
def test_get_quotes_missing_price(repo: YahooChartPriceRepository, urlopen: mock.Mock, price: Any) -> None:
    '''
    Test that a present row without a numeric price is a bad_payload failure for that id only.

    :param repo: The repository.
    :type repo: YahooChartPriceRepository
    :param urlopen: The patched urlopen.
    :type urlopen: mock.Mock
    :param price: The replacement price value.
    :type price: Any
    '''

    urlopen.side_effect = recorded_yahoo(rows=batch_rows(AAPL={'regularMarketPrice': price}))

    quotes = repo.get_quotes(['AAPL', 'SPY'])

    assert [quote.symbol_id for quote in quotes.quotes] == ['SPY']
    assert [(f.symbol_id, f.reason) for f in quotes.failures] == [('AAPL', 'bad_payload')]

# ** test: get_quotes_carries_symbol_warnings
def test_get_quotes_carries_symbol_warnings(repo: YahooChartPriceRepository, urlopen: mock.Mock) -> None:
    '''
    Test that an unmapped exchange is a soft warning on the quote list, not a failure.

    :param repo: The repository.
    :type repo: YahooChartPriceRepository
    :param urlopen: The patched urlopen.
    :type urlopen: mock.Mock
    '''

    urlopen.side_effect = recorded_yahoo(rows=batch_rows(AAPL={'exchange': 'PNK'}))

    quotes = repo.get_quotes(['AAPL'])

    assert quotes.get_quote('AAPL') is not None
    assert [(w.reason, w.detail) for w in quotes.warnings] == [('unmapped_exchange', 'PNK')]
    assert quotes.failures == []

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

    urlopen.side_effect = recorded_yahoo(rows=batch_rows(AAPL={'regularMarketPreviousClose': previous_close}))

    quote = repo.get_quotes(['AAPL']).get_quote('AAPL')

    assert quote.previous_close is None
    assert quote.change_pct is None

# ** test: init_source_default
def test_init_source_default() -> None:
    '''
    Test that the default source is the catalogued Yahoo quote provider id, distinct from the alias provider id, and can be overridden.
    '''

    assert YahooChartPriceRepository().source == a.YAHOO_QUOTE_PROVIDER_ID == 'yahoo_quote'
    assert a.YAHOO_CHART_PROVIDER_ID == 'yahoo_chart'
    assert YahooChartPriceRepository(source='yahoo_alt').source == 'yahoo_alt'

# ** test: init_session_params
def test_init_session_params() -> None:
    '''
    Test that the batch quote, cookie and crumb URLs default to the verified endpoints and can be configured.
    '''

    repo = YahooChartPriceRepository()
    assert repo.batch_quote_url == 'https://query1.finance.yahoo.com/v7/finance/quote?symbols={symbols}&crumb={crumb}'
    assert repo.session.cookie_url == 'https://fc.yahoo.com'
    assert repo.session.crumb_url == 'https://query1.finance.yahoo.com/v1/test/getcrumb'
    assert repo.quote_url.startswith('https://query1.finance.yahoo.com/v8/finance/chart/')
    custom = YahooChartPriceRepository(timeout='3', batch_quote_url='https://q.test/{symbols}/{crumb}', cookie_url='https://c.test', crumb_url='https://k.test')
    assert (custom.batch_quote_url, custom.session.cookie_url, custom.session.crumb_url, custom.session.timeout) == ('https://q.test/{symbols}/{crumb}', 'https://c.test', 'https://k.test', 3.0)

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

    urlopen.side_effect = recorded_yahoo(rows=batch_rows(AAPL={'regularMarketTime': market_time}))

    quotes = repo.get_quotes(['AAPL', 'SPY'])

    assert quotes.get_quote('AAPL').market_time is None
    assert quotes.get_quote('SPY').market_time is not None
    assert quotes.failures == []

# ** test: get_quotes_source_override
def test_get_quotes_source_override(urlopen: mock.Mock) -> None:
    '''
    Test that a configured source reaches each quote.

    :param urlopen: The patched urlopen.
    :type urlopen: mock.Mock
    '''

    urlopen.side_effect = recorded_yahoo()

    quotes = YahooChartPriceRepository(source='alt').get_quotes(['AAPL'])

    assert quotes.get_quote('AAPL').source == 'alt'

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

# ** test: get_history_recorded_brk_b
def test_get_history_recorded_brk_b(repo: YahooChartPriceRepository, urlopen: mock.Mock) -> None:
    '''
    Test that the recorded BRK-B history payload yields bars under the provider ticker, oldest first.

    :param repo: The repository.
    :type repo: YahooChartPriceRepository
    :param urlopen: The patched urlopen.
    :type urlopen: mock.Mock
    '''

    urlopen.return_value = make_response(read_payload('brk-b_history'))

    history = repo.get_history('BRK-B', '2026-10-20', '2026-10-22')

    assert history.failure is None
    assert [bar.date for bar in history.bars] == ['2026-10-20', '2026-10-21', '2026-10-22']
    bar = history.bars[0]
    assert bar.symbol_id == 'BRK-B'
    assert all(isinstance(value, float) for value in (bar.open, bar.high, bar.low, bar.close, bar.adj_close))
    assert isinstance(bar.volume, int) and not isinstance(bar.volume, bool)
    assert bar.close == 539.8200073242188
    assert bar.volume == 5311100
    assert 'BRK-B' in urlopen.call_args[0][0].full_url

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
