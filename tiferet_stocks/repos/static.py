"""Tiferet Stocks Static Price Repository"""

# *** imports

# ** core
import csv
import json
from datetime import date, datetime, timezone
from typing import Any, Dict, List

# ** infra
# PyYAML is provided by tiferet (pyyaml>=6.0.1).
import yaml

# ** app
from ..interfaces import PriceService
from ..mappers import (
    NOT_FOUND,
    BAD_PAYLOAD,
    derive_change_pct,
    usable_number,
    Quote,
    QuoteFailure,
    QuotationsAggregate,
    PriceBar,
    PriceHistoryAggregate,
)

# *** constants

# ** constant: default_source
DEFAULT_SOURCE = 'static'

# *** repos

# ** repo: static_price_repository
class StaticPriceRepository(PriceService):
    '''
    Read-only price provider that serves fixed prices from a dict or a JSON or YAML fixture, and daily bars from a CSV fixture, for tests.
    '''

    # * attribute: prices
    prices: Dict[str, Dict[str, Any]]

    # * attribute: history
    history: Dict[str, List[Dict[str, str]]]

    # * init
    def __init__(self,
                 prices: Dict[str, Dict[str, Any]] = None,
                 fixture_path: str = None,
                 encoding: str = 'utf-8',
                 source: str = DEFAULT_SOURCE,
                 history_path: str = None) -> None:
        '''
        Initialize the static price repository.

        :param prices: Price data by symbol id, each with price and optional previous_close, market_time and currency.
        :type prices: Dict[str, Dict[str, Any]]
        :param fixture_path: A JSON or YAML fixture file holding the same price data, read once.
        :type fixture_path: str
        :param encoding: The fixture file encoding.
        :type encoding: str
        :param source: The provider id stamped on each quote.
        :type source: str
        :param history_path: A CSV fixture of daily bars with the header symbol_id,date,open,high,low,close,adj_close,volume, read once.
        :type history_path: str
        '''

        # Store the provider id and start from the given prices.
        self.source = source
        self.prices = dict(prices or {})

        # Merge prices from the fixture file, if one is given; YAML also reads JSON.
        if fixture_path:
            with open(fixture_path, 'r', encoding=encoding) as file:
                data = json.load(file) if fixture_path.endswith('.json') else yaml.safe_load(file)
            self.prices.update((data or {}).get('prices', data or {}))

        # Group the daily bar rows from the history fixture by symbol id, if one is given.
        self.history = {}
        if history_path:
            with open(history_path, 'r', encoding=encoding, newline='') as file:
                for row in csv.DictReader(file):
                    self.history.setdefault(row.get('symbol_id'), []).append(row)

    # * method: get_quotes
    def get_quotes(self, symbols: List[str]) -> QuotationsAggregate:
        '''
        Get the fixed quote for each requested symbol id.

        :param symbols: The requested symbol ids (tickers).
        :type symbols: List[str]
        :return: The quotes by requested id, with a not_found failure for each unknown id.
        :rtype: QuotationsAggregate
        '''

        # Build a quote or a not_found failure for each distinct id.
        quotes, failures = {}, []
        for symbol_id in dict.fromkeys(symbols):
            data = self.prices.get(symbol_id)
            if data is None:
                failures.append(QuoteFailure(symbol_id=symbol_id, reason=NOT_FOUND, detail='No static price for the symbol.'))
                continue

            # A row needs a usable price; otherwise report a bad_payload failure.
            price = data.get('price') if isinstance(data, dict) else None
            if not usable_number(price):
                failures.append(QuoteFailure(symbol_id=symbol_id, reason=BAD_PAYLOAD, detail='Static price row has no usable price.'))
                continue

            # Keep only a usable, positive previous close.
            previous_close = data.get('previous_close')
            if not usable_number(previous_close) or previous_close <= 0:
                previous_close = None

            # Build the quote.
            quotes[symbol_id] = Quote(
                symbol_id=symbol_id,
                price=price,
                previous_close=previous_close,
                change_pct=derive_change_pct(price, previous_close),
                market_time=data.get('market_time'),
                currency=data.get('currency', 'USD'),
                source=self.source,
            )

        # Return the quotations.
        return QuotationsAggregate(
            quotes=quotes,
            failures=failures,
            fetched_at=datetime.now(timezone.utc).isoformat(),
        )

    # * method: get_history
    def get_history(self, symbol: str, start: str, end: str) -> PriceHistoryAggregate:
        '''
        Get the fixed daily bars for one symbol between two ISO dates, inclusive, oldest first.

        :param symbol: The requested symbol id (ticker).
        :type symbol: str
        :param start: The first day, as an ISO 8601 date (inclusive).
        :type start: str
        :param end: The last day, as an ISO 8601 date (inclusive).
        :type end: str
        :return: The bars within the range, or a not_found or bad_payload failure.
        :rtype: PriceHistoryAggregate
        '''

        # An unknown symbol is a not_found failure.
        rows = self.history.get(symbol)
        if rows is None:
            failure = QuoteFailure(symbol_id=symbol, reason=NOT_FOUND, detail='No static history for the symbol.')
            return PriceHistoryAggregate(symbol_id=symbol, start=start, end=end, failure=failure)

        # Build a bar for each row in range; a row with an unusable value is a bad_payload failure.
        bars = {}
        for row in rows:
            day = row.get('date') or ''
            try:
                iso_day = date.fromisoformat(day).isoformat()
            except ValueError:
                iso_day = None
            if iso_day != day or day in bars:
                failure = QuoteFailure(symbol_id=symbol, reason=BAD_PAYLOAD, detail=f'Static history row date {day!r} is not a unique ISO 8601 date.')
                return PriceHistoryAggregate(symbol_id=symbol, start=start, end=end, failure=failure)
            if not start <= day <= end:
                continue
            try:
                prices = {name: float(row[name]) for name in ('open', 'high', 'low', 'close')}
                adj_close = float(row['adj_close']) if row.get('adj_close') else None
                volume = int(row['volume']) if row.get('volume') else None
            except (KeyError, TypeError, ValueError):
                prices = None
            if prices is None or not all(usable_number(value) for value in prices.values()) or (adj_close is not None and not usable_number(adj_close)):
                failure = QuoteFailure(symbol_id=symbol, reason=BAD_PAYLOAD, detail=f'Static history row for {day} has an unusable value.')
                return PriceHistoryAggregate(symbol_id=symbol, start=start, end=end, failure=failure)
            bars[day] = PriceBar(symbol_id=symbol, date=day, adj_close=adj_close, volume=volume, **prices)

        # Return the bars oldest first.
        return PriceHistoryAggregate(
            symbol_id=symbol,
            start=start,
            end=end,
            bars=[bars[day] for day in sorted(bars)],
        )
