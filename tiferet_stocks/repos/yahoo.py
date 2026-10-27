"""Tiferet Stocks Yahoo Chart Repository"""

# *** imports

# ** core
import json
from datetime import datetime, timezone
import socket
from http import client as http_client
from typing import Any, Dict, List, Tuple
from urllib import error as url_error
from urllib import parse, request

# ** app
from ..assets import YAHOO_CHART_PROVIDER_ID
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
    Quote,
    QuoteFailure,
    QuoteSet,
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

# ** constant: default_timeout
DEFAULT_TIMEOUT = '10'

# ** constant: default_retries
DEFAULT_RETRIES = '1'

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
        Initialize the Yahoo chart repository.

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
    def fetch_chart(self, symbol_id: str) -> Tuple[Dict[str, Any] | None, QuoteFailure | None, int]:
        '''
        Fetch the chart result for one symbol, retrying transient failures.

        :param symbol_id: The requested symbol id (ticker).
        :type symbol_id: str
        :return: The chart result or the failure, with the number of attempts made.
        :rtype: Tuple[Dict[str, Any] | None, QuoteFailure | None, int]
        '''

        # Build the request for the symbol.
        url = self.quote_url.format(symbol=parse.quote(symbol_id))
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
        if isinstance(price, bool) or not isinstance(price, (int, float)):
            return None, QuoteFailure(symbol_id=symbol_id, reason=BAD_PAYLOAD, detail='Chart metadata has no regularMarketPrice.', attempts=attempts)

        # Derive the change from a usable previous close.
        previous_close = meta.get('chartPreviousClose')
        if isinstance(previous_close, bool) or not isinstance(previous_close, (int, float)):
            previous_close = None
        change_pct = derive_change_pct(price, previous_close)

        # Convert the market time from epoch seconds to ISO 8601 UTC.
        market_time = meta.get('regularMarketTime')
        if isinstance(market_time, (int, float)) and not isinstance(market_time, bool):
            market_time = datetime.fromtimestamp(market_time, tz=timezone.utc).isoformat()
        else:
            market_time = None

        # Return the quote.
        return Quote(
            symbol_id=symbol_id,
            price=price,
            previous_close=previous_close,
            change_pct=change_pct,
            market_time=market_time,
            currency=meta.get('currency'),
            source=YAHOO_CHART_PROVIDER_ID,
        ), None

    # * method: get_quotes
    def get_quotes(self, symbols: List[str]) -> QuoteSet:
        '''
        Get the latest quote for each requested symbol id from the Yahoo chart endpoint.

        :param symbols: The requested symbol ids (tickers).
        :type symbols: List[str]
        :return: The quotes by requested id, with symbols, warnings and failures.
        :rtype: QuoteSet
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

        # Return the quote set.
        return QuoteSet(
            quotes=quotes,
            symbols=symbol_map,
            warnings=warnings,
            failures=failures,
            fetched_at=fetched_at,
        )
