"""Tiferet Stocks Symbol Domain Tests"""

# *** imports

# ** core
from typing import Dict

# ** infra
import pytest
from pydantic import ValidationError
from tiferet import use_tester

# ** app
from tiferet_stocks.domain import (
    ASSET_TYPES,
    EXCHANGES,
    NOT_FOUND,
    PROVIDERS,
    UNMAPPED_EXCHANGE,
    YAHOO_CHART,
    PriceBar,
    Quote,
    QuoteFailure,
    Symbol,
    SymbolAlias,
    SymbolLookup,
    SymbolWarning,
    merge_symbol_aliases,
    rekey_map,
    rekey_symbol_id,
    rekey_symbol_ids,
    to_canonical_id,
    to_provider_ticker,
    to_provider_tickers,
)

# *** functions

# ** function: yahoo_brk_aliases
def yahoo_brk_aliases() -> Dict[str, SymbolAlias]:
    '''
    Return a yahoo_chart alias map for BRK.B, keyed by provider ticker.

    :return: The alias map.
    :rtype: Dict[str, SymbolAlias]
    '''

    # Build and return the map.
    alias = SymbolAlias(provider=YAHOO_CHART, provider_ticker='BRK-B', canonical_id='BRK.B')
    return {'BRK-B': alias}

# *** tests

# ** test: exchanges_constant
def test_exchanges_constant() -> None:
    '''
    Test that EXCHANGES holds the v1 exchange ids in order.
    '''

    assert EXCHANGES == ['NYSE', 'NASDAQ', 'NYSE_ARCA', 'CBOE_BZX', 'NYSE_AMERICAN']

# ** test: asset_types_constant
def test_asset_types_constant() -> None:
    '''
    Test that ASSET_TYPES holds the v1 asset types in order.
    '''

    assert ASSET_TYPES == ['equity', 'etf', 'mutual_fund', 'money_market_fund']

# ** test: symbol_accepts_every_exchange
@pytest.mark.parametrize('exchange', EXCHANGES)
def test_symbol_accepts_every_exchange(exchange: str) -> None:
    '''
    Test that a symbol accepts every exchange id in EXCHANGES.

    :param exchange: The exchange id.
    :type exchange: str
    '''

    symbol = Symbol(id='TEST', exchange=exchange)

    assert symbol.exchange == exchange

# ** test: symbol_accepts_empty_exchange
def test_symbol_accepts_empty_exchange() -> None:
    '''
    Test that a symbol accepts an empty exchange and defaults currency to USD.
    '''

    symbol = Symbol(id='FRSXX', asset_type='money_market_fund')

    assert symbol.exchange is None
    assert symbol.currency == 'USD'

# ** test: symbol_rejects_unknown_exchange
@pytest.mark.parametrize('exchange', ['PCX', 'NMS', 'NYQ', 'LSE', 'nyse'])
def test_symbol_rejects_unknown_exchange(exchange: str) -> None:
    '''
    Test that a symbol rejects any exchange outside EXCHANGES, including provider codes.

    :param exchange: The rejected exchange value.
    :type exchange: str
    '''

    with pytest.raises(ValidationError):
        Symbol(id='TEST', exchange=exchange)

# ** test: symbol_rejects_unknown_asset_type
def test_symbol_rejects_unknown_asset_type() -> None:
    '''
    Test that a symbol rejects an asset type outside ASSET_TYPES.
    '''

    with pytest.raises(ValidationError):
        Symbol(id='TEST', asset_type='EQUITY')

# ** test: symbol_has_no_provider_fields
def test_symbol_has_no_provider_fields() -> None:
    '''
    Test that a symbol has no CUSIP field and no raw provider exchange field.
    '''

    assert set(Symbol.model_fields) == {'id', 'exchange', 'name', 'asset_type', 'currency', 'aliases'}
    with pytest.raises(ValidationError):
        Symbol(id='TEST', cusip='037833100')
    with pytest.raises(ValidationError):
        Symbol(id='TEST', exchange_code='NMS')

# ** test: symbol_warning_rejects_unknown_reason
def test_symbol_warning_rejects_unknown_reason() -> None:
    '''
    Test that a symbol warning only accepts a known reason.
    '''

    warning = SymbolWarning(symbol_id='TCEHY', reason=UNMAPPED_EXCHANGE, detail='PNK')

    assert warning.detail == 'PNK'
    with pytest.raises(ValidationError):
        SymbolWarning(symbol_id='TCEHY', reason='unknown')

# ** test: symbol_lookup_defaults
def test_symbol_lookup_defaults() -> None:
    '''
    Test that an empty symbol lookup has no symbols, warnings or failures.
    '''

    lookup = SymbolLookup()

    assert lookup.symbols == {}
    assert lookup.warnings == []
    assert lookup.failures == []

# ** test: symbol_lookup_holds_results
def test_symbol_lookup_holds_results() -> None:
    '''
    Test that a symbol lookup holds symbols by id alongside failures.
    '''

    lookup = SymbolLookup(
        symbols={'AAPL': Symbol(id='AAPL', exchange='NASDAQ')},
        failures=[QuoteFailure(symbol_id='ZZZZ', reason=NOT_FOUND)],
    )

    assert lookup.symbols['AAPL'].exchange == 'NASDAQ'
    assert lookup.failures[0].symbol_id == 'ZZZZ'

# ** test: providers_constant
def test_providers_constant() -> None:
    '''
    Test that PROVIDERS holds the initial provider ids in order.
    '''

    assert PROVIDERS == ['yahoo_chart']
    assert YAHOO_CHART == 'yahoo_chart'

# ** test: symbol_alias_accepts_yahoo_chart
def test_symbol_alias_accepts_yahoo_chart() -> None:
    '''
    Test that a symbol alias accepts the yahoo_chart provider and holds both tickers.
    '''

    alias = SymbolAlias(provider=YAHOO_CHART, provider_ticker='BRK-B', canonical_id='BRK.B')

    assert alias.provider == 'yahoo_chart'
    assert alias.provider_ticker == 'BRK-B'
    assert alias.canonical_id == 'BRK.B'

# ** test: symbol_alias_rejects_unknown_provider
@pytest.mark.parametrize('provider', ['yahoo', 'YahooChart', 'YAHOO_CHART', ''])
def test_symbol_alias_rejects_unknown_provider(provider: str) -> None:
    '''
    Test that a symbol alias rejects any provider outside PROVIDERS.

    :param provider: The rejected provider value.
    :type provider: str
    '''

    with pytest.raises(ValidationError):
        SymbolAlias(provider=provider, provider_ticker='BRK-B', canonical_id='BRK.B')

# ** test: symbol_accepts_alias_for_canonical_id
def test_symbol_accepts_alias_for_canonical_id() -> None:
    '''
    Test that a symbol accepts an alias whose canonical id is the symbol id.
    '''

    alias = SymbolAlias(provider=YAHOO_CHART, provider_ticker='BRK-B', canonical_id='BRK.B')
    symbol = Symbol(id='BRK.B', aliases=[alias])

    assert symbol.aliases == [alias]

# ** test: symbol_accepts_alias_for_provider_ticker
def test_symbol_accepts_alias_for_provider_ticker() -> None:
    '''
    Test that a symbol accepts an alias whose provider ticker is the symbol id, as at inbound apply.
    '''

    alias = SymbolAlias(provider=YAHOO_CHART, provider_ticker='BRK-B', canonical_id='BRK.B')
    symbol = Symbol(id='BRK-B', aliases=[alias])

    assert symbol.aliases[0].canonical_id == 'BRK.B'

# ** test: symbol_rejects_alias_for_another_symbol
def test_symbol_rejects_alias_for_another_symbol() -> None:
    '''
    Test that a symbol rejects an alias whose canonical id and provider ticker are not this symbol.
    '''

    alias = SymbolAlias(provider=YAHOO_CHART, provider_ticker='BRK-B', canonical_id='BRK.B')

    with pytest.raises(ValidationError):
        Symbol(id='AAPL', aliases=[alias])

# ** test: symbol_rejects_second_alias_for_same_provider
def test_symbol_rejects_second_alias_for_same_provider() -> None:
    '''
    Test that a symbol rejects a second alias for a provider already on the collection.
    '''

    first = SymbolAlias(provider=YAHOO_CHART, provider_ticker='BRK-B', canonical_id='BRK.B')
    second = SymbolAlias(provider=YAHOO_CHART, provider_ticker='BRK-B', canonical_id='BRK.B')

    with pytest.raises(ValidationError):
        Symbol(id='BRK.B', aliases=[first, second])

# ** test: symbol_defaults_to_empty_aliases
def test_symbol_defaults_to_empty_aliases() -> None:
    '''
    Test that a symbol with no aliases given has an empty collection.
    '''

    symbol = Symbol(id='AAPL', exchange='NASDAQ')

    assert symbol.aliases == []

# ** test: to_provider_ticker_replaces_canonical_id
def test_to_provider_ticker_replaces_canonical_id() -> None:
    '''
    Test that the outbound helper maps a canonical id to the provider ticker.
    '''

    assert to_provider_ticker('BRK.B', yahoo_brk_aliases()) == 'BRK-B'

# ** test: to_provider_ticker_passthrough_without_alias
def test_to_provider_ticker_passthrough_without_alias() -> None:
    '''
    Test that the outbound helper passes through an id that has no alias, including an empty map.
    '''

    assert to_provider_ticker('AAPL', yahoo_brk_aliases()) == 'AAPL'
    assert to_provider_ticker('BRK.B', {}) == 'BRK.B'

# ** test: to_provider_tickers_preserves_order
def test_to_provider_tickers_preserves_order() -> None:
    '''
    Test that the outbound list helper applies the rule to each id and keeps order.
    '''

    assert to_provider_tickers(['BRK.B', 'AAPL', 'BRK.B'], yahoo_brk_aliases()) == ['BRK-B', 'AAPL', 'BRK-B']
    assert to_provider_tickers([], yahoo_brk_aliases()) == []

# ** test: to_canonical_id_replaces_provider_ticker
def test_to_canonical_id_replaces_provider_ticker() -> None:
    '''
    Test that the inbound helper maps a provider ticker to the canonical id.
    '''

    assert to_canonical_id('BRK-B', yahoo_brk_aliases()) == 'BRK.B'

# ** test: to_canonical_id_passthrough_without_alias
def test_to_canonical_id_passthrough_without_alias() -> None:
    '''
    Test that the inbound helper passes through a canonical id and an unaliased ticker.
    '''

    assert to_canonical_id('BRK.B', yahoo_brk_aliases()) == 'BRK.B'
    assert to_canonical_id('AAPL', yahoo_brk_aliases()) == 'AAPL'
    assert to_canonical_id('BRK-B', {}) == 'BRK-B'

# ** test: rekey_map_rewrites_keys
def test_rekey_map_rewrites_keys() -> None:
    '''
    Test that rekey_map rewrites provider-ticker keys to canonical ids and leaves values unchanged.
    '''

    quote = Quote(symbol_id='BRK-B', price=500.0, source='yahoo_chart')
    control = Quote(symbol_id='AAPL', price=270.0, source='yahoo_chart')
    original = {'BRK-B': quote, 'AAPL': control}

    result = rekey_map(original, yahoo_brk_aliases())

    assert list(result) == ['BRK.B', 'AAPL']
    assert result['BRK.B'] is quote
    assert result['AAPL'] is control
    assert list(original) == ['BRK-B', 'AAPL']

# ** test: rekey_symbol_id_copies_and_rewrites
def test_rekey_symbol_id_copies_and_rewrites() -> None:
    '''
    Test that rekey_symbol_id returns a copy with a canonical symbol_id and does not mutate the original.
    '''

    failure = QuoteFailure(symbol_id='BRK-B', reason=NOT_FOUND)
    warning = SymbolWarning(symbol_id='BRK-B', reason=UNMAPPED_EXCHANGE, detail='NYQ')
    quote = Quote(symbol_id='BRK-B', price=500.0, source='yahoo_chart')
    bar = PriceBar(symbol_id='BRK-B', date='2026-10-20', open=1.0, high=1.0, low=1.0, close=1.0)

    rewritten = [
        rekey_symbol_id(failure, yahoo_brk_aliases()),
        rekey_symbol_id(warning, yahoo_brk_aliases()),
        rekey_symbol_id(quote, yahoo_brk_aliases()),
        rekey_symbol_id(bar, yahoo_brk_aliases()),
    ]

    assert [item.symbol_id for item in rewritten] == ['BRK.B', 'BRK.B', 'BRK.B', 'BRK.B']
    assert failure.symbol_id == 'BRK-B'
    assert warning.symbol_id == 'BRK-B'
    assert quote.symbol_id == 'BRK-B'
    assert bar.symbol_id == 'BRK-B'
    assert rewritten[0] is not failure

# ** test: rekey_symbol_id_passthrough_without_alias
def test_rekey_symbol_id_passthrough_without_alias() -> None:
    '''
    Test that rekey_symbol_id returns the same object when the id is already canonical or has no alias.
    '''

    failure = QuoteFailure(symbol_id='AAPL', reason=NOT_FOUND)
    canonical = QuoteFailure(symbol_id='BRK.B', reason=NOT_FOUND)

    assert rekey_symbol_id(failure, yahoo_brk_aliases()) is failure
    assert rekey_symbol_id(canonical, yahoo_brk_aliases()) is canonical

# ** test: rekey_symbol_ids_rewrites_a_list
def test_rekey_symbol_ids_rewrites_a_list() -> None:
    '''
    Test that rekey_symbol_ids rewrites each symbol_id and leaves unaliased items unchanged.
    '''

    aliased = QuoteFailure(symbol_id='BRK-B', reason=NOT_FOUND)
    control = QuoteFailure(symbol_id='AAPL', reason=NOT_FOUND)

    result = rekey_symbol_ids([aliased, control], yahoo_brk_aliases())

    assert result[0].symbol_id == 'BRK.B'
    assert result[1] is control
    assert aliased.symbol_id == 'BRK-B'

# ** test: alias_helpers_do_not_raise_on_empty_input
def test_alias_helpers_do_not_raise_on_empty_input() -> None:
    '''
    Test that the helpers return empty results and do not raise when given empty input.
    '''

    aliases = yahoo_brk_aliases()

    assert to_provider_tickers([], aliases) == []
    assert rekey_map({}, aliases) == {}
    assert rekey_symbol_ids([], aliases) == []
    assert to_provider_ticker('AAPL', {}) == 'AAPL'
    assert to_canonical_id('AAPL', {}) == 'AAPL'

# ** test: merge_symbol_aliases_keeps_defaults
def test_merge_symbol_aliases_keeps_defaults_when_nothing_is_configured() -> None:
    '''
    Test that the defaults are the merged map when nothing is configured, and that the inputs are not changed.
    '''

    defaults = yahoo_brk_aliases()

    merged = merge_symbol_aliases({}, defaults)

    assert merged == yahoo_brk_aliases()
    assert merged is not defaults
    assert merge_symbol_aliases({}, {}) == {}

# ** test: merge_symbol_aliases_configured_wins
@pytest.mark.parametrize('provider_ticker, canonical_id', [
    ('BRK-B', 'FILE.B'),
    ('BRKB.X', 'BRK.B'),
])
def test_merge_symbol_aliases_configured_wins(provider_ticker: str, canonical_id: str) -> None:
    '''
    Test that a configured alias with a default's provider ticker or canonical id drops that default in both directions.

    :param provider_ticker: The configured provider ticker.
    :type provider_ticker: str
    :param canonical_id: The configured canonical id.
    :type canonical_id: str
    '''

    configured = {provider_ticker: SymbolAlias(provider=YAHOO_CHART, provider_ticker=provider_ticker, canonical_id=canonical_id)}

    merged = merge_symbol_aliases(configured, yahoo_brk_aliases())

    assert merged == configured
    assert to_provider_ticker(canonical_id, merged) == provider_ticker
    if provider_ticker != 'BRK-B':
        assert to_provider_ticker('BRK-B', merged) == 'BRK-B'
        assert to_canonical_id('BRK-B', merged) == 'BRK-B'

# ** test: merge_symbol_aliases_unrelated_defaults
def test_merge_symbol_aliases_keeps_unrelated_defaults_first() -> None:
    '''
    Test that a default no configured alias covers is kept, ahead of the configured aliases.
    '''

    configured = {'BF-B': SymbolAlias(provider=YAHOO_CHART, provider_ticker='BF-B', canonical_id='BF.B')}

    merged = merge_symbol_aliases(configured, yahoo_brk_aliases())

    assert list(merged) == ['BRK-B', 'BF-B']

# ** test: merge_symbol_aliases_later_configured_wins
def test_merge_symbol_aliases_later_configured_alias_wins_a_canonical_id() -> None:
    '''
    Test that when two configured aliases map one canonical id the later wins outbound and the earlier is dropped, so its raw ticker passes through.
    '''

    configured = {
        'X1': SymbolAlias(provider=YAHOO_CHART, provider_ticker='X1', canonical_id='BRK.B'),
        'BF-B': SymbolAlias(provider=YAHOO_CHART, provider_ticker='BF-B', canonical_id='BF.B'),
        'X2': SymbolAlias(provider=YAHOO_CHART, provider_ticker='X2', canonical_id='BRK.B'),
    }

    merged = merge_symbol_aliases(configured, yahoo_brk_aliases())

    assert list(merged) == ['BF-B', 'X2']
    assert to_provider_ticker('BRK.B', merged) == 'X2'
    assert to_provider_ticker('X1', merged) == 'X1'
    assert to_canonical_id('X1', merged) == 'X1'
    assert list(configured) == ['X1', 'BF-B', 'X2']

# *** testers

# ** tester: test_symbol
@use_tester(
    type='domain',
    target_cls=Symbol,
    sample_data={'id': 'AAPL', 'exchange': 'NASDAQ', 'name': 'Apple Inc.', 'asset_type': 'equity', 'currency': 'USD'},
    equality_fields=['id', 'exchange', 'name', 'asset_type', 'currency', 'aliases'],
)
class TestSymbol:
    '''
    Bound domain tester for Symbol.
    '''

    # * test: new
    def test_new(self, test_ctx, session):
        '''
        Construct a symbol from sample data.
        '''

        test_ctx.assert_new()
