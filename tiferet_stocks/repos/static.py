"""Tiferet Stocks Static Price Repository"""

# *** imports

# ** core
import json
import math
from datetime import datetime, timezone
from typing import Any, Dict, List

# ** infra
import yaml  # declared in pyproject; also a tiferet dependency

# ** app
from ..interfaces import PriceService
from ..mappers import (
    NOT_FOUND,
    BAD_PAYLOAD,
    derive_change_pct,
    Quote,
    QuoteFailure,
    QuoteSet,
)

# *** constants

# ** constant: default_source
DEFAULT_SOURCE = 'static'

# *** functions

# ** function: usable_number
def usable_number(value: Any) -> bool:
    '''
    Check that a value is a finite int or float and not a bool.

    :param value: The value to check.
    :type value: Any
    :return: True when the value is a usable number.
    :rtype: bool
    '''

    # Reject bools, non-numbers and NaN or infinite values.
    return not isinstance(value, bool) and isinstance(value, (int, float)) and math.isfinite(value)

# *** repos

# ** repo: static_price_repository
class StaticPriceRepository(PriceService):
    '''
    Read-only price provider that serves fixed prices from a dict or a JSON or YAML fixture, for tests.
    '''

    # * attribute: prices
    prices: Dict[str, Dict[str, Any]]

    # * init
    def __init__(self,
                 prices: Dict[str, Dict[str, Any]] = None,
                 fixture_path: str = None,
                 encoding: str = 'utf-8',
                 source: str = DEFAULT_SOURCE) -> None:
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
        '''

        # Store the provider id and start from the given prices.
        self.source = source
        self.prices = dict(prices or {})

        # Merge prices from the fixture file, if one is given; YAML also reads JSON.
        if fixture_path:
            with open(fixture_path, 'r', encoding=encoding) as file:
                data = json.load(file) if fixture_path.endswith('.json') else yaml.safe_load(file)
            self.prices.update((data or {}).get('prices', data or {}))

    # * method: get_quotes
    def get_quotes(self, symbols: List[str]) -> QuoteSet:
        '''
        Get the fixed quote for each requested symbol id.

        :param symbols: The requested symbol ids (tickers).
        :type symbols: List[str]
        :return: The quotes by requested id, with a not_found failure for each unknown id.
        :rtype: QuoteSet
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

        # Return the quote set.
        return QuoteSet(
            quotes=quotes,
            failures=failures,
            fetched_at=datetime.now(timezone.utc).isoformat(),
        )
