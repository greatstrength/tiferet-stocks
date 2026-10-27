"""Tiferet Stocks Static Price Repository"""

# *** imports

# ** core
import json
from datetime import datetime, timezone
from typing import Any, Dict, List

# ** infra
import yaml

# ** app
from ..assets import STATIC_PROVIDER_ID
from ..interfaces import PriceService
from ..mappers import (
    NOT_FOUND,
    derive_change_pct,
    Quote,
    QuoteFailure,
    QuoteSet,
)

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
                 encoding: str = 'utf-8') -> None:
        '''
        Initialize the static price repository.

        :param prices: Price data by symbol id, each with price and optional previous_close, market_time and currency.
        :type prices: Dict[str, Dict[str, Any]]
        :param fixture_path: A JSON or YAML fixture file holding the same price data, read once.
        :type fixture_path: str
        :param encoding: The fixture file encoding.
        :type encoding: str
        '''

        # Start from the given prices.
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
            quotes[symbol_id] = Quote(
                symbol_id=symbol_id,
                price=data['price'],
                previous_close=data.get('previous_close'),
                change_pct=derive_change_pct(data['price'], data.get('previous_close')),
                market_time=data.get('market_time'),
                currency=data.get('currency', 'USD'),
                source=STATIC_PROVIDER_ID,
            )

        # Return the quote set.
        return QuoteSet(
            quotes=quotes,
            failures=failures,
            fetched_at=datetime.now(timezone.utc).isoformat(),
        )
