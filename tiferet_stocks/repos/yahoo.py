"""Tiferet Stocks Yahoo Repository"""

# *** imports

# ** core
import json
from datetime import date, datetime, timezone
import socket
from http import client as http_client
from typing import Any, Dict, List, Tuple
from urllib import error as url_error
from urllib import parse, request

# ** app
from ..interfaces import PriceService
from ..mappers import (
    NYSE,
    NASDAQ,
    NYSE_ARCA,
    CBOE_BZX,
    NYSE_AMERICAN,
    EQUITY,
    ETF,
    MUTUAL_FUND,
    MONEY_MARKET_FUND,
    FUND_ASSET_TYPES,
    NOT_FOUND,
    HTTP_ERROR,
    TIMEOUT,
    BAD_PAYLOAD,
    UNMAPPED_EXCHANGE,
    UNMAPPED_ASSET_TYPE,
    derive_change_pct,
    usable_number,
    Quote,
    QuoteFailure,
    QuoteListAggregate,
    PriceBar,
    PriceHistoryAggregate,
    SymbolWarning,
    SymbolAggregate,
    SymbolYahooObject,
)

# *** constants

# ** constant: yahoo_exchange_map
YAHOO_EXCHANGE_MAP = {
    'NYQ': NYSE,
    'NMS': NASDAQ,
    'NGM': NASDAQ,
    'NCM': NASDAQ,
    'PCX': NYSE_ARCA,
    'BTS': CBOE_BZX,
    'ASE': NYSE_AMERICAN,
}

# ** constant: yahoo_asset_type_map
YAHOO_ASSET_TYPE_MAP = {
    'EQUITY': EQUITY,
    'ETF': ETF,
    'MONEYMARKET': MONEY_MARKET_FUND,
    'MUTUALFUND': MUTUAL_FUND,
}

# ** constant: default_quote_url
DEFAULT_QUOTE_URL = 'https://query1.finance.yahoo.com/v8/finance/chart/{symbol}?range=1d&interval=1d'

# ** constant: default_history_url
DEFAULT_HISTORY_URL = 'https://query1.finance.yahoo.com/v8/finance/chart/{symbol}?period1={period1}&period2={period2}&interval=1d'

# ** constant: day_seconds
DAY_SECONDS = 86400

# ** constant: default_timeout
DEFAULT_TIMEOUT = '10'

# ** constant: default_retries
DEFAULT_RETRIES = '1'

# ** constant: default_batch_quote_url
DEFAULT_BATCH_QUOTE_URL = 'https://query1.finance.yahoo.com/v7/finance/quote?symbols={symbols}&crumb={crumb}'

# ** constant: default_cookie_url
DEFAULT_COOKIE_URL = 'https://fc.yahoo.com'

# ** constant: default_crumb_url
DEFAULT_CRUMB_URL = 'https://query1.finance.yahoo.com/v1/test/getcrumb'

# ** constant: default_source
DEFAULT_SOURCE = 'yahoo_quote'

# ** constant: rate_limited_status
RATE_LIMITED_STATUS = 429

# ** constant: session_rejected_statuses
SESSION_REJECTED_STATUSES = (401, 403)

# ** constant: user_agent
USER_AGENT = 'Mozilla/5.0 (compatible; tiferet-stocks)'

# *** functions

# ** function: describe_request_error
def describe_request_error(error: Exception, timeout: float) -> Tuple[str, str, int | None]:
    '''
    Name a failed Yahoo request as a quote failure reason, detail and HTTP status.

    :param error: The exception raised by the request.
    :type error: Exception
    :param timeout: The request timeout in seconds, for the detail text.
    :type timeout: float
    :return: The failure reason, its detail and the HTTP status when there is one.
    :rtype: Tuple[str, str, int | None]
    '''

    # An HTTP status is an http_error carrying its code.
    if isinstance(error, url_error.HTTPError):
        return HTTP_ERROR, f'HTTP {error.code}', error.code

    # A timeout, raised directly or wrapped in a URLError, is a timeout.
    reason = error.reason if isinstance(error, url_error.URLError) else error
    if isinstance(reason, (socket.timeout, TimeoutError)):
        return TIMEOUT, f'No response within {timeout} seconds', None

    # Anything else is a request error.
    if isinstance(error, url_error.URLError):
        return HTTP_ERROR, str(error.reason), None
    return HTTP_ERROR, str(error) or type(error).__name__, None

# *** classes

# ** class: yahoo_anonymous_session
class YahooAnonymousSession(object):
    '''
    The repository's own anonymous Yahoo session: an A3 cookie and a crumb, fetched once and reused.
    It is not a user account, it never raises, and nothing outside the Yahoo repository sees it.
    '''

    # * attribute: cookie_url
    cookie_url: str

    # * attribute: crumb_url
    crumb_url: str

    # * attribute: timeout
    timeout: float

    # * attribute: cookie
    cookie: str | None

    # * attribute: crumb
    crumb: str | None

    # * init
    def __init__(self, cookie_url: str = DEFAULT_COOKIE_URL, crumb_url: str = DEFAULT_CRUMB_URL, timeout: float = 10.0) -> None:
        '''
        Initialize an empty session.

        :param cookie_url: The URL whose response sets the anonymous cookie.
        :type cookie_url: str
        :param crumb_url: The URL that returns a crumb for that cookie.
        :type crumb_url: str
        :param timeout: The request timeout in seconds.
        :type timeout: float
        '''

        # Start with no cookie or crumb; the first quote request opens the session.
        self.cookie_url = cookie_url
        self.crumb_url = crumb_url
        self.timeout = float(timeout)
        self.cookie = None
        self.crumb = None

    # * method: is_open
    def is_open(self) -> bool:
        '''
        Check whether the session holds a cookie and a crumb.

        :return: True when both are held.
        :rtype: bool
        '''

        # Both parts are needed for a quote request.
        return bool(self.cookie and self.crumb)

    # * method: reset
    def reset(self) -> None:
        '''
        Forget the cookie and crumb, so the next request opens a new session.

        :return: None.
        :rtype: None
        '''

        # Drop both parts together.
        self.cookie = None
        self.crumb = None

    # * method: open
    def open(self) -> Tuple[str, str, int | None] | None:
        '''
        Open the session if it is not already open; an open session is reused without any request.

        :return: None when the session is open, otherwise the failure reason, detail and HTTP status.
        :rtype: Tuple[str, str, int | None] | None
        '''

        # Reuse a held cookie and crumb; a second crumb fetch in the same window can be rate limited.
        if self.is_open():
            return None

        # The cookie host answers with Set-Cookie, often on an error status.
        try:
            with request.urlopen(request.Request(self.cookie_url, headers={'User-Agent': USER_AGENT}), timeout=self.timeout) as response:
                headers = response.headers
        except url_error.HTTPError as error:
            headers = error.headers
        except (http_client.HTTPException, OSError) as error:
            reason, detail, status = describe_request_error(error, self.timeout)
            return reason, f'Session cookie: {detail}', status
        cookies = [value.split(';', 1)[0].strip() for value in (headers.get_all('Set-Cookie') if headers else None) or []]
        cookie = '; '.join(value for value in cookies if value)
        if not cookie:
            return HTTP_ERROR, 'Session cookie: no cookie was set.', None

        # Ask for a crumb under that cookie.
        try:
            with request.urlopen(self.build_request(self.crumb_url, cookie), timeout=self.timeout) as response:
                crumb = response.read().decode('utf-8', 'replace').strip()
        except (http_client.HTTPException, OSError) as error:
            reason, detail, status = describe_request_error(error, self.timeout)
            return reason, f'Session crumb: {detail}', status
        if not crumb or any(character.isspace() or character in '<{' for character in crumb):
            return BAD_PAYLOAD, 'Session crumb: unreadable crumb response.', None

        # Hold both for reuse.
        self.cookie, self.crumb = cookie, crumb
        return None

    # * method: build_request
    def build_request(self, url: str, cookie: str = None) -> request.Request:
        '''
        Build a request that carries the session cookie.

        :param url: The full request URL.
        :type url: str
        :param cookie: The cookie header value; defaults to the held cookie.
        :type cookie: str
        :return: The request.
        :rtype: request.Request
        '''

        # Send the shared User-Agent and the anonymous cookie.
        return request.Request(url, headers={'User-Agent': USER_AGENT, 'Cookie': cookie or self.cookie or ''})

# ** class: yahoo_chart_client
class YahooChartClient(object):
    '''
    Shared Yahoo chart endpoint client: fetches and parses chart results and translates their metadata into symbols.
    Used by the Yahoo price repository and the Yahoo symbol repository; it takes whatever id it is given and does not raise.
    '''

    # * attribute: quote_url
    quote_url: str

    # * attribute: timeout
    timeout: float

    # * attribute: retries
    retries: int

    # * init
    def __init__(self,
                 quote_url: str = DEFAULT_QUOTE_URL,
                 timeout: str = DEFAULT_TIMEOUT,
                 retries: str = DEFAULT_RETRIES) -> None:
        '''
        Initialize the Yahoo chart client.

        :param quote_url: The chart endpoint URL template, with a {symbol} placeholder.
        :type quote_url: str
        :param timeout: The request timeout in seconds; configuration may pass a string.
        :type timeout: str
        :param retries: The number of retries per symbol after a failed attempt; configuration may pass a string.
        :type retries: str
        '''

        # Store the endpoint and convert the numeric parameters.
        self.quote_url = quote_url
        self.timeout = float(timeout)
        self.retries = max(0, int(retries))

    # * method: fetch_chart
    def fetch_chart(self, symbol_id: str, url: str = None) -> Tuple[Dict[str, Any] | None, QuoteFailure | None, int]:
        '''
        Fetch the chart result for one symbol, retrying transient failures.

        :param symbol_id: The requested symbol id (ticker).
        :type symbol_id: str
        :param url: The full request URL; defaults to the quote URL for the symbol.
        :type url: str
        :return: The chart result or the failure, with the number of attempts made.
        :rtype: Tuple[Dict[str, Any] | None, QuoteFailure | None, int]
        '''

        # Build the request for the symbol.
        url = url or self.quote_url.format(symbol=parse.quote(symbol_id))
        req = request.Request(url, headers={'User-Agent': USER_AGENT})

        # Try the request once plus the configured retries.
        reason, detail, attempts = HTTP_ERROR, None, 0
        for _ in range(self.retries + 1):
            attempts += 1

            # Read the response body; a 404 is final, other failures are retried.
            try:
                with request.urlopen(req, timeout=self.timeout) as response:
                    body = response.read()
            except url_error.HTTPError as error:
                if error.code == 404:
                    return None, QuoteFailure(symbol_id=symbol_id, reason=NOT_FOUND, detail='HTTP 404', attempts=attempts), attempts
                reason, detail = HTTP_ERROR, f'HTTP {error.code}'
                continue
            except (socket.timeout, TimeoutError):
                reason, detail = TIMEOUT, f'No response within {self.timeout} seconds'
                continue
            except url_error.URLError as error:
                if isinstance(error.reason, (socket.timeout, TimeoutError)):
                    reason, detail = TIMEOUT, f'No response within {self.timeout} seconds'
                else:
                    reason, detail = HTTP_ERROR, str(error.reason)
                continue
            except (http_client.HTTPException, OSError) as error:
                reason, detail = HTTP_ERROR, str(error) or type(error).__name__
                continue

            # Parse the chart result; a malformed body is final.
            result, failure = self.parse_chart(symbol_id, body, attempts)
            return result, failure, attempts

        # Every attempt failed; return the last failure.
        return None, QuoteFailure(symbol_id=symbol_id, reason=reason, detail=detail, attempts=attempts), attempts

    # * method: parse_chart
    def parse_chart(self,
                    symbol_id: str,
                    body: bytes,
                    attempts: int) -> Tuple[Dict[str, Any] | None, QuoteFailure | None]:
        '''
        Parse a chart response body into its first result.

        :param symbol_id: The requested symbol id (ticker).
        :type symbol_id: str
        :param body: The raw response body.
        :type body: bytes
        :param attempts: The number of attempts made so far.
        :type attempts: int
        :return: The chart result and no failure, or no result and the failure.
        :rtype: Tuple[Dict[str, Any] | None, QuoteFailure | None]
        '''

        # Decode the body as JSON.
        try:
            chart = json.loads(body)['chart']
        except (ValueError, KeyError, TypeError) as error:
            return None, QuoteFailure(symbol_id=symbol_id, reason=BAD_PAYLOAD, detail=f'Unreadable chart response: {error}', attempts=attempts)

        # An empty result with an error body means the symbol is unknown.
        results = chart.get('result') if isinstance(chart, dict) else None
        if not results:
            error = (chart.get('error') or {}) if isinstance(chart, dict) else {}
            if error.get('code') == 'Not Found':
                return None, QuoteFailure(symbol_id=symbol_id, reason=NOT_FOUND, detail=error.get('description'), attempts=attempts)
            return None, QuoteFailure(symbol_id=symbol_id, reason=BAD_PAYLOAD, detail='Chart response has no result.', attempts=attempts)

        # The result must carry its metadata.
        result = results[0]
        if not isinstance(result, dict) or not isinstance(result.get('meta'), dict):
            return None, QuoteFailure(symbol_id=symbol_id, reason=BAD_PAYLOAD, detail='Chart result has no metadata.', attempts=attempts)

        # Return the chart result.
        return result, None

    # * method: translate_symbol
    def translate_symbol(self, symbol_id: str, meta: Dict[str, Any]) -> Tuple[SymbolAggregate, List[SymbolWarning]]:
        '''
        Translate chart metadata into a symbol, mapping Yahoo codes to domain ids.

        :param symbol_id: The requested symbol id (ticker).
        :type symbol_id: str
        :param meta: The chart result metadata.
        :type meta: Dict[str, Any]
        :return: The symbol aggregate and any warnings.
        :rtype: Tuple[SymbolAggregate, List[SymbolWarning]]
        '''

        # Map the instrument type, warning when it is unknown.
        warnings = []
        instrument_type = meta.get('instrumentType')
        asset_type = YAHOO_ASSET_TYPE_MAP.get(instrument_type)
        if asset_type is None:
            warnings.append(SymbolWarning(symbol_id=symbol_id, reason=UNMAPPED_ASSET_TYPE, detail=instrument_type))

        # Funds get no exchange by rule; other listings map their code or warn.
        exchange_code = meta.get('exchangeName')
        exchange = None
        if asset_type not in FUND_ASSET_TYPES:
            exchange = YAHOO_EXCHANGE_MAP.get(exchange_code)
            if exchange is None:
                warnings.append(SymbolWarning(symbol_id=symbol_id, reason=UNMAPPED_EXCHANGE, detail=exchange_code))

        # Build the symbol from the translated values only.
        symbol = SymbolYahooObject(
            id=meta.get('symbol') or symbol_id,
            exchange=exchange,
            name=meta.get('longName') or meta.get('shortName'),
            asset_type=asset_type,
            currency=meta.get('currency') or 'USD',
        ).map()

        # Return the symbol and its warnings.
        return symbol, warnings

# *** repos

# ** repo: yahoo_chart_price_repository
class YahooChartPriceRepository(YahooChartClient, PriceService):
    '''
    Price provider backed by Yahoo: quotes from the batch quote endpoint in one request, history from the chart endpoint one symbol at a time.
    It is alias-free: it takes whatever id it is given.
    '''

    # * attribute: history_url
    history_url: str

    # * attribute: source
    source: str

    # * attribute: batch_quote_url
    batch_quote_url: str

    # * attribute: session
    session: YahooAnonymousSession

    # * init
    def __init__(self,
                 quote_url: str = DEFAULT_QUOTE_URL,
                 timeout: str = DEFAULT_TIMEOUT,
                 retries: str = DEFAULT_RETRIES,
                 source: str = DEFAULT_SOURCE,
                 history_url: str = DEFAULT_HISTORY_URL,
                 batch_quote_url: str = DEFAULT_BATCH_QUOTE_URL,
                 cookie_url: str = DEFAULT_COOKIE_URL,
                 crumb_url: str = DEFAULT_CRUMB_URL) -> None:
        '''
        Initialize the Yahoo price repository.

        :param quote_url: The chart endpoint URL template, with a {symbol} placeholder.
        :type quote_url: str
        :param timeout: The request timeout in seconds; configuration may pass a string.
        :type timeout: str
        :param retries: The number of retries per symbol after a failed attempt; configuration may pass a string.
        :type retries: str
        :param source: The provider id stamped on each quote.
        :type source: str
        :param history_url: The daily chart endpoint URL template, with {symbol}, {period1} and {period2} placeholders.
        :type history_url: str
        :param batch_quote_url: The batch quote endpoint URL template, with {symbols} and {crumb} placeholders.
        :type batch_quote_url: str
        :param cookie_url: The URL whose response sets the anonymous session cookie.
        :type cookie_url: str
        :param crumb_url: The URL that returns the session crumb.
        :type crumb_url: str
        '''

        # Set up the shared chart client, then the price-only parameters.
        YahooChartClient.__init__(self, quote_url=quote_url, timeout=timeout, retries=retries)
        self.source = source
        self.history_url = history_url
        self.batch_quote_url = batch_quote_url

        # The anonymous session lives with the repository and is reused across calls.
        self.session = YahooAnonymousSession(cookie_url=cookie_url, crumb_url=crumb_url, timeout=self.timeout)

    # * method: translate_quote
    def translate_quote(self,
                        symbol_id: str,
                        row: Dict[str, Any],
                        attempts: int) -> Tuple[Quote | None, QuoteFailure | None]:
        '''
        Translate one batch quote row into a quote.

        :param symbol_id: The requested symbol id (ticker).
        :type symbol_id: str
        :param row: The batch quote result row for the symbol.
        :type row: Dict[str, Any]
        :param attempts: The number of attempts made for the batch.
        :type attempts: int
        :return: The quote and no failure, or no quote and the failure.
        :rtype: Tuple[Quote | None, QuoteFailure | None]
        '''

        # A quote needs a numeric price.
        price = row.get('regularMarketPrice')
        if not usable_number(price):
            return None, QuoteFailure(symbol_id=symbol_id, reason=BAD_PAYLOAD, detail='Quote row has no usable regularMarketPrice.', attempts=attempts)

        # Derive the change from a usable previous close.
        previous_close = row.get('regularMarketPreviousClose')
        if not usable_number(previous_close) or previous_close <= 0:
            previous_close = None
        change_pct = derive_change_pct(price, previous_close)

        # Convert the market time from epoch seconds to ISO 8601 UTC; an unusable or out-of-range value leaves it empty.
        market_time = row.get('regularMarketTime')
        try:
            market_time = datetime.fromtimestamp(market_time, tz=timezone.utc).isoformat() if usable_number(market_time) else None
        except (OverflowError, OSError, ValueError):
            market_time = None

        # Return the quote.
        return Quote(
            symbol_id=symbol_id,
            price=price,
            previous_close=previous_close,
            change_pct=change_pct,
            market_time=market_time,
            currency=row.get('currency'),
            source=self.source,
        ), None

    # * method: fetch_quotes
    def fetch_quotes(self, symbol_ids: List[str]) -> Tuple[bytes | None, Tuple[str, str] | None, int]:
        '''
        Fetch the batch quote body for every requested id in one request, retrying the whole batch.

        :param symbol_ids: The distinct requested symbol ids, in request order.
        :type symbol_ids: List[str]
        :return: The response body or the batch failure reason and detail, with the number of attempts made.
        :rtype: Tuple[bytes | None, Tuple[str, str] | None, int]
        '''

        # Try once plus the configured retries; every attempt covers the whole batch.
        failure, attempts = (HTTP_ERROR, None), 0
        for _ in range(self.retries + 1):
            attempts += 1

            # Open, or reuse, the anonymous session; a rate-limited session request is not retried.
            opened = self.session.open()
            if opened:
                reason, detail, status = opened
                failure = (reason, detail)
                if status == RATE_LIMITED_STATUS:
                    break
                continue

            # One request for the whole list.
            url = self.batch_quote_url.format(
                symbols=parse.quote(','.join(symbol_ids), safe=','),
                crumb=parse.quote(self.session.crumb, safe=''),
            )
            try:
                with request.urlopen(self.session.build_request(url), timeout=self.timeout) as response:
                    return response.read(), None, attempts
            except (http_client.HTTPException, OSError) as error:
                reason, detail, status = describe_request_error(error, self.timeout)
                failure = (reason, detail)

            # A rejected session is dropped and reopened on the next attempt; rate limiting is not retried.
            if status in SESSION_REJECTED_STATUSES:
                self.session.reset()
            if status == RATE_LIMITED_STATUS:
                break

        # Every attempt failed; return the last failure.
        return None, failure, attempts

    # * method: get_quotes
    def get_quotes(self, symbols: List[str]) -> QuoteListAggregate:
        '''
        Get the latest quote for each requested symbol id from the Yahoo batch quote endpoint, in one request.

        :param symbols: The requested symbol ids (tickers).
        :type symbols: List[str]
        :return: The quotes in request order, with symbols, warnings and a failure for every id that produced no quote.
        :rtype: QuoteListAggregate
        '''

        # Record when the request started; an empty request makes no network call.
        fetched_at = datetime.now(timezone.utc).isoformat()
        symbol_ids = list(dict.fromkeys(symbols))
        if not symbol_ids:
            return QuoteListAggregate(fetched_at=fetched_at)

        # A batch-level failure is recorded on every requested id.
        body, failure, attempts = self.fetch_quotes(symbol_ids)
        if failure:
            reason, detail = failure
            return QuoteListAggregate(
                failures=[QuoteFailure(symbol_id=symbol_id, reason=reason, detail=detail, attempts=attempts) for symbol_id in symbol_ids],
                fetched_at=fetched_at,
            )

        # An unreadable body is a bad_payload failure on every requested id.
        try:
            results = json.loads(body)['quoteResponse']['result']
            rows = {str(row['symbol']).upper(): row for row in results if isinstance(row, dict) and row.get('symbol')}
        except (ValueError, KeyError, TypeError) as error:
            return QuoteListAggregate(
                failures=[QuoteFailure(symbol_id=symbol_id, reason=BAD_PAYLOAD, detail=f'Unreadable quote response: {error}', attempts=attempts) for symbol_id in symbol_ids],
                fetched_at=fetched_at,
            )

        # Translate each requested id in order; an id Yahoo omitted is not_found, never dropped.
        quotes, symbol_map, warnings, failures = [], {}, [], []
        for symbol_id in symbol_ids:
            row = rows.get(symbol_id.upper())
            if row is None:
                failures.append(QuoteFailure(symbol_id=symbol_id, reason=NOT_FOUND, detail='Not in the quote response.', attempts=attempts))
                continue
            quote, quote_failure = self.translate_quote(symbol_id, row, attempts)
            if quote_failure:
                failures.append(quote_failure)
                continue

            # The batch row carries the same symbol details as chart metadata, under its own field names.
            symbol, symbol_warnings = self.translate_symbol(symbol_id, {
                'symbol': row.get('symbol'),
                'instrumentType': row.get('quoteType'),
                'exchangeName': row.get('exchange'),
                'longName': row.get('longName'),
                'shortName': row.get('shortName'),
                'currency': row.get('currency'),
            })
            quotes.append(quote)
            symbol_map[symbol_id] = symbol
            warnings.extend(symbol_warnings)

        # Return the quote list.
        return QuoteListAggregate(
            quotes=quotes,
            symbols=symbol_map,
            warnings=warnings,
            failures=failures,
            fetched_at=fetched_at,
        )

    # * method: translate_history
    def translate_history(self,
                          symbol_id: str,
                          result: Dict[str, Any],
                          start: str,
                          end: str,
                          attempts: int) -> Tuple[List[PriceBar], QuoteFailure | None]:
        '''
        Translate a daily chart result into bars within the range, oldest first.

        :param symbol_id: The requested symbol id (ticker).
        :type symbol_id: str
        :param result: The chart result.
        :type result: Dict[str, Any]
        :param start: The first day, as an ISO 8601 date (inclusive).
        :type start: str
        :param end: The last day, as an ISO 8601 date (inclusive).
        :type end: str
        :param attempts: The number of attempts made for the symbol.
        :type attempts: int
        :return: The bars and no failure, or no bars and the failure.
        :rtype: Tuple[List[PriceBar], QuoteFailure | None]
        '''

        # A range with no trading days has no timestamps; that is an empty answer, not a failure.
        timestamps = result.get('timestamp') or []
        if not timestamps:
            return [], None
        if not isinstance(timestamps, list):
            return [], QuoteFailure(symbol_id=symbol_id, reason=BAD_PAYLOAD, detail='Chart result has no timestamp list.', attempts=attempts)

        # The bar series must line up with the timestamps.
        indicators = result.get('indicators') if isinstance(result.get('indicators'), dict) else {}
        quote_list = indicators.get('quote') or [{}]
        adj_list = indicators.get('adjclose') or [{}]
        series = quote_list[0] if isinstance(quote_list, list) else None
        adj_series = adj_list[0] if isinstance(adj_list, list) else None
        if not isinstance(series, dict) or not isinstance(adj_series, dict):
            return [], QuoteFailure(symbol_id=symbol_id, reason=BAD_PAYLOAD, detail='Chart result has no daily series.', attempts=attempts)
        columns = {name: series.get(name) for name in ('open', 'high', 'low', 'close', 'volume')}
        columns['adj_close'] = adj_series.get('adjclose')
        for name, values in columns.items():
            if values is not None and (not isinstance(values, list) or len(values) != len(timestamps)):
                return [], QuoteFailure(symbol_id=symbol_id, reason=BAD_PAYLOAD, detail=f'Daily series {name} does not match the timestamps.', attempts=attempts)
        if any(columns[name] is None for name in ('open', 'high', 'low', 'close')):
            return [], QuoteFailure(symbol_id=symbol_id, reason=BAD_PAYLOAD, detail='Daily series is missing a price column.', attempts=attempts)

        # Date each bar in the exchange time zone.
        offset = result['meta'].get('gmtoffset')
        offset = offset if usable_number(offset) else 0

        # Build a bar for each day in range; Yahoo pads halted days with nulls, which are skipped, and a repeated day keeps its last bar.
        bars = {}
        for index, stamp in enumerate(timestamps):
            try:
                day = datetime.fromtimestamp(stamp + offset, tz=timezone.utc).date().isoformat() if usable_number(stamp) else None
            except (OverflowError, OSError, ValueError):
                day = None
            if day is None:
                return [], QuoteFailure(symbol_id=symbol_id, reason=BAD_PAYLOAD, detail='Daily series has an unusable timestamp.', attempts=attempts)
            if not start <= day <= end:
                continue
            prices = {name: columns[name][index] for name in ('open', 'high', 'low', 'close')}
            if all(value is None for value in prices.values()):
                continue
            if not all(usable_number(value) for value in prices.values()):
                return [], QuoteFailure(symbol_id=symbol_id, reason=BAD_PAYLOAD, detail=f'Daily series has an unusable price for {day}.', attempts=attempts)
            adj_close = columns['adj_close'][index] if columns['adj_close'] else None
            volume = columns['volume'][index] if columns['volume'] else None
            bars[day] = PriceBar(
                symbol_id=symbol_id,
                date=day,
                adj_close=adj_close if usable_number(adj_close) else None,
                volume=int(volume) if usable_number(volume) else None,
                **prices,
            )

        # Return the bars oldest first.
        return [bars[day] for day in sorted(bars)], None

    # * method: get_history
    def get_history(self, symbol: str, start: str, end: str) -> PriceHistoryAggregate:
        '''
        Get the daily bars for one symbol between two ISO dates, inclusive, from the Yahoo chart endpoint.

        :param symbol: The requested symbol id (ticker).
        :type symbol: str
        :param start: The first day, as an ISO 8601 date (inclusive).
        :type start: str
        :param end: The last day, as an ISO 8601 date (inclusive).
        :type end: str
        :return: The bars within the range, or the failure.
        :rtype: PriceHistoryAggregate
        '''

        # Request the UTC days of the range widened by one day on each side, so exchanges ahead of or behind UTC keep their edge days; bars are trimmed to the range by exchange date.
        period1 = int(datetime.combine(date.fromisoformat(start), datetime.min.time(), tzinfo=timezone.utc).timestamp()) - DAY_SECONDS
        period2 = int(datetime.combine(date.fromisoformat(end), datetime.min.time(), tzinfo=timezone.utc).timestamp()) + 2 * DAY_SECONDS
        url = self.history_url.format(symbol=parse.quote(symbol), period1=period1, period2=period2)

        # Fetch the daily chart and translate its bars.
        result, failure, attempts = self.fetch_chart(symbol, url)
        bars = []
        if not failure:
            bars, failure = self.translate_history(symbol, result, start, end, attempts)

        # Return the history.
        return PriceHistoryAggregate(
            symbol_id=symbol,
            start=start,
            end=end,
            bars=bars,
            failure=failure,
        )
