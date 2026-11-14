"""Tiferet Stocks Recorded Yahoo Responses"""

# *** imports

# ** core
from email.message import Message
import io
import json
from pathlib import Path
from typing import Any, Callable, Dict, List
from unittest import mock
from urllib import error as url_error
from urllib import parse

# *** constants

# ** constant: payloads_path
PAYLOADS_PATH = Path(__file__).resolve().parent / 'payloads'

# ** constant: recorded_cookie
RECORDED_COOKIE = 'A3=d=recorded-anonymous-cookie'

# ** constant: recorded_crumb
RECORDED_CRUMB = 'recorded.crumb'

# *** functions

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
def make_http_error(url: str, code: int, headers: Dict[str, str] | None = None, body: bytes = b'') -> url_error.HTTPError:
    '''
    Build an HTTP error with the given status, headers and body.

    :param url: The request URL.
    :type url: str
    :param code: The HTTP status code.
    :type code: int
    :param headers: Response headers, such as Set-Cookie.
    :type headers: Dict[str, str] | None
    :param body: The response body.
    :type body: bytes
    :return: The HTTP error.
    :rtype: url_error.HTTPError
    '''

    # Use a real message object so get_all works like a live response.
    message = Message()
    for key, value in (headers or {}).items():
        message[key] = value
    return url_error.HTTPError(url, code, 'error', message, io.BytesIO(body))

# ** function: batch_quote_body
def batch_quote_body(tickers: List[str], rows: List[Dict[str, Any]] | None = None) -> bytes:
    '''
    Serve the recorded batch quote response for the requested tickers, omitting tickers Yahoo did not return.

    :param tickers: The requested provider tickers.
    :type tickers: List[str]
    :param rows: Replacement result rows; defaults to the recorded rows (AAPL, BRK-B, SPY, FRSXX, recorded 2026-11-14).
    :type rows: List[Dict[str, Any]] | None
    :return: The response body.
    :rtype: bytes
    '''

    # Filter the recorded rows to the request, in request order.
    if rows is None:
        rows = json.loads((PAYLOADS_PATH / 'quote_batch.json').read_text())['quoteResponse']['result']
    by_symbol = {row['symbol']: row for row in rows}
    result = [by_symbol[ticker.upper()] for ticker in tickers if ticker.upper() in by_symbol]
    return json.dumps({'quoteResponse': {'result': result, 'error': None}}).encode()

# ** function: recorded_yahoo
def recorded_yahoo(requested: List[str] | None = None,
                   chart_tickers: tuple = ('BRK-B', 'AAPL', 'SPY'),
                   rows: List[Dict[str, Any]] | None = None) -> Callable:
    '''
    Build a urlopen stand-in for the Yahoo session, batch quote and chart endpoints, from recorded bodies.

    :param requested: A list that collects one entry per request: 'cookie', 'crumb', 'quote:<tickers>' or the chart ticker.
    :type requested: List[str] | None
    :param chart_tickers: The tickers with recorded chart bodies; any other chart ticker is an HTTP 404.
    :type chart_tickers: tuple
    :param rows: Replacement batch quote rows.
    :type rows: List[Dict[str, Any]] | None
    :return: The urlopen stand-in.
    :rtype: Callable
    '''

    # Route by endpoint; nothing reaches the network.
    requested = requested if requested is not None else []
    def urlopen(req, timeout=None):
        url = parse.urlsplit(req.full_url)
        if url.netloc == 'fc.yahoo.com':
            requested.append('cookie')
            raise make_http_error(req.full_url, 404, {'Set-Cookie': f'{RECORDED_COOKIE}; Domain=.yahoo.com; Path=/; Secure; HttpOnly'})
        assert url.netloc == 'query1.finance.yahoo.com', 'Unexpected endpoint'
        if url.path == '/v1/test/getcrumb':
            requested.append('crumb')
            assert req.get_header('Cookie') == RECORDED_COOKIE
            return make_response(RECORDED_CRUMB.encode())
        if url.path == '/v7/finance/quote':
            query = parse.parse_qs(url.query)
            requested.append('quote:' + query['symbols'][0])
            assert query['crumb'] == [RECORDED_CRUMB] and req.get_header('Cookie') == RECORDED_COOKIE
            return make_response(batch_quote_body(query['symbols'][0].split(','), rows))
        ticker = parse.unquote(url.path.rsplit('/', 1)[-1])
        requested.append(ticker)
        if ticker not in chart_tickers:
            raise make_http_error(req.full_url, 404)
        name = ticker.lower() + ('_history' if 'period1=' in url.query else '')
        return make_response((PAYLOADS_PATH / f'{name}.json').read_bytes())

    # Return the stand-in.
    return urlopen
