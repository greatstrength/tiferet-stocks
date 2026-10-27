"""Tiferet Stocks Symbol Domain Tests"""

# *** imports

# ** infra
import pytest
from pydantic import ValidationError
from tiferet import use_tester

# ** app
from tiferet_stocks.domain import (
    ASSET_TYPES,
    EXCHANGES,
    NOT_FOUND,
    UNMAPPED_EXCHANGE,
    QuoteFailure,
    Symbol,
    SymbolLookup,
    SymbolWarning,
)

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

    assert set(Symbol.model_fields) == {'id', 'exchange', 'name', 'asset_type', 'currency'}
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

# *** testers

# ** tester: test_symbol
@use_tester(
    type='domain',
    target_cls=Symbol,
    sample_data={'id': 'AAPL', 'exchange': 'NASDAQ', 'name': 'Apple Inc.', 'asset_type': 'equity', 'currency': 'USD'},
    equality_fields=['id', 'exchange', 'name', 'asset_type', 'currency'],
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
