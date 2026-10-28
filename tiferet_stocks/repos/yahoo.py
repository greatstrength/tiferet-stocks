"""Tiferet Stocks Yahoo Chart Repository"""

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
from ..interfaces import PriceService, SymbolLookupService
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
    QuotationsAggregate,
    PriceBar,
    PriceHistoryAggregate,
    SymbolLookup,
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

# ** constant: default_source
DEFAULT_SOURCE = 'yahoo_chart'

# ** constant: user_agent
USER_AGENT = 'Mozilla/5.0 (compatible; tiferet-stocks)'

# *** repos

# ** repo: yahoo_chart_price_repository
class YahooChartPriceRepository(SymbolLookupService, PriceService):
    '''
    Market data provider backed by the Yahoo chart endpoint.
    '''

    # * attribute: quote_url
    quote_url: str

    # * attribute: history_url
    history_url: str

    # * attribute: timeout
    timeout: float

    # * attribute: retries
    retries: int

    # * init
    def __init__(self,
                 quote_url: str = DEFAULT_QUOTE_URL,
                 timeout: str = DEFAULT_TIMEOUT,
                 retries: str = DEFAULT_RETRIES,
                 source: str = DEFAULT_SOURCE,
                 history_url: str = DEFAULT_HISTORY_URL) -> None:
        '''
        Initialize the Yahoo chart repository.

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
        '''

        # Store the endpoint and convert the numeric parameters.
        self.quote_url = quote_url
        self.timeout = float(timeout)
        self.retries = max(0, int(retries))
        self.source = source
        self.history_url = history_url

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

    # * method: lookup
    def lookup(self, ids: List[str]) -> SymbolLookup:
        '''
        Look up each requested symbol id with the Yahoo chart endpoint.

        :param ids: The requested symbol ids (tickers).
        :type ids: List[str]
        :return: The symbols by requested id, with warnings and failures.
        :rtype: SymbolLookup
        '''

        # Fetch and translate each distinct id in request order.
        symbols, warnings, failures = {}, [], []
        for symbol_id in dict.fromkeys(ids):
            result, failure, _ = self.fetch_chart(symbol_id)
            if failure:
                failures.append(failure)
                continue
            symbol, symbol_warnings = self.translate_symbol(symbol_id, result['meta'])
            symbols[symbol_id] = symbol
            warnings.extend(symbol_warnings)

        # Return the lookup answer.
        return SymbolLookup(symbols=symbols, warnings=warnings, failures=failures)

    # * method: translate_quote
    def translate_quote(self,
                        symbol_id: str,
                        meta: Dict[str, Any],
                        attempts: int) -> Tuple[Quote | None, QuoteFailure | None]:
        '''
        Translate chart metadata into a quote.

        :param symbol_id: The requested symbol id (ticker).
        :type symbol_id: str
        :param meta: The chart result metadata.
        :type meta: Dict[str, Any]
        :param attempts: The number of attempts made for the symbol.
        :type attempts: int
        :return: The quote and no failure, or no quote and the failure.
        :rtype: Tuple[Quote | None, QuoteFailure | None]
        '''

        # A quote needs a numeric price.
        price = meta.get('regularMarketPrice')
        if not usable_number(price):
            return None, QuoteFailure(symbol_id=symbol_id, reason=BAD_PAYLOAD, detail='Chart metadata has no usable regularMarketPrice.', attempts=attempts)

        # Derive the change from a usable previous close.
        previous_close = meta.get('chartPreviousClose')
        if not usable_number(previous_close) or previous_close <= 0:
            previous_close = None
        change_pct = derive_change_pct(price, previous_close)

        # Convert the market time from epoch seconds to ISO 8601 UTC; an unusable or out-of-range value leaves it empty.
        market_time = meta.get('regularMarketTime')
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
            currency=meta.get('currency'),
            source=self.source,
        ), None

    # * method: get_quotes
    def get_quotes(self, symbols: List[str]) -> QuotationsAggregate:
        '''
        Get the latest quote for each requested symbol id from the Yahoo chart endpoint.

        :param symbols: The requested symbol ids (tickers).
        :type symbols: List[str]
        :return: The quotes by requested id, with symbols, warnings and failures.
        :rtype: QuotationsAggregate
        '''

        # Record when the request started.
        fetched_at = datetime.now(timezone.utc).isoformat()

        # Fetch each distinct id once and translate its quote and symbol.
        quotes, symbol_map, warnings, failures = {}, {}, [], []
        for symbol_id in dict.fromkeys(symbols):
            result, failure, attempts = self.fetch_chart(symbol_id)
            if failure:
                failures.append(failure)
                continue
            quote, failure = self.translate_quote(symbol_id, result['meta'], attempts)
            if failure:
                failures.append(failure)
                continue
            symbol, symbol_warnings = self.translate_symbol(symbol_id, result['meta'])
            quotes[symbol_id] = quote
            symbol_map[symbol_id] = symbol
            warnings.extend(symbol_warnings)

        # Return the quotations.
        return QuotationsAggregate(
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
