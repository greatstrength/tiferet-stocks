"""Tiferet Stocks Symbol Mapper Tests"""

# *** imports

# ** infra
import pytest
from pydantic import ValidationError
from tiferet import use_tester
from tiferet.domain import ModelError

# ** app
from tiferet_stocks.mappers import SymbolAggregate, SymbolYahooObject
from tiferet_stocks.repos.yahoo import YAHOO_EXCHANGE_MAP

# *** tests

# ** test: symbol_yahoo_object_rejects_unmapped_codes
@pytest.mark.parametrize('code', sorted(YAHOO_EXCHANGE_MAP))
def test_symbol_yahoo_object_rejects_unmapped_codes(code: str) -> None:
    '''
    Guard test: a Yahoo exchange code that reaches SymbolYahooObject unmapped fails validation.

    :param code: The raw Yahoo exchange code.
    :type code: str
    '''

    with pytest.raises(ValidationError):
        SymbolYahooObject(id='TEST', exchange=code)

# ** test: symbol_yahoo_object_accepts_mapped_codes
@pytest.mark.parametrize('code', sorted(YAHOO_EXCHANGE_MAP))
def test_symbol_yahoo_object_accepts_mapped_codes(code: str) -> None:
    '''
    Test that the mapped exchange id for every Yahoo code validates.

    :param code: The raw Yahoo exchange code.
    :type code: str
    '''

    symbol = SymbolYahooObject(id='TEST', exchange=YAHOO_EXCHANGE_MAP[code])

    assert symbol.exchange == YAHOO_EXCHANGE_MAP[code]

# ** test: symbol_yahoo_object_map
def test_symbol_yahoo_object_map() -> None:
    '''
    Test that a Yahoo symbol maps to a symbol aggregate with the same values.
    '''

    symbol = SymbolYahooObject(
        id='SPY',
        exchange='NYSE_ARCA',
        name='SPDR S&P 500 ETF Trust',
        asset_type='etf',
    ).map()

    assert isinstance(symbol, SymbolAggregate)
    assert symbol.exchange == 'NYSE_ARCA'
    assert symbol.asset_type == 'etf'
    assert symbol.currency == 'USD'

# ** test: symbol_aggregate_is_read_only
def test_symbol_aggregate_is_read_only() -> None:
    '''
    Test that a symbol aggregate allows no attribute changes through set_attribute.
    '''

    symbol = SymbolAggregate(id='AAPL', exchange='NASDAQ')

    with pytest.raises(ModelError):
        symbol.set_attribute('exchange', 'NYSE')

# *** testers

# ** tester: test_symbol_aggregate
@use_tester(
    type='aggregate',
    target_cls=SymbolAggregate,
    sample_data={'id': 'AAPL', 'exchange': 'NASDAQ', 'name': 'Apple Inc.', 'asset_type': 'equity', 'currency': 'USD'},
    equality_fields=['id', 'exchange', 'name', 'asset_type', 'currency'],
    set_attribute_params=[
        ('exchange', 'NYSE', 'ATTRIBUTE_NOT_SETTABLE'),
        ('name', 'Apple', 'ATTRIBUTE_NOT_SETTABLE'),
    ],
)
class TestSymbolAggregate:
    '''
    Bound aggregate tester for SymbolAggregate: constructible and read-only.
    '''

    # * test: new
    def test_new(self, test_ctx, session):
        '''
        Construct a symbol aggregate from sample data.
        '''

        test_ctx.assert_new()

    # * test: set_attribute
    def test_set_attribute(self, test_ctx, session):
        '''
        Reject every attribute change.
        '''

        test_ctx.assert_set_attribute()

# ** tester: test_symbol_yahoo_object
@use_tester(
    type='transfer_object',
    target_cls=SymbolYahooObject,
    sample_data={'id': 'SPY', 'exchange': 'NYSE_ARCA', 'name': 'SPDR S&P 500 ETF Trust', 'asset_type': 'etf', 'currency': 'USD'},
    aggregate_module_path='tiferet_stocks.mappers.symbol',
    aggregate_class_name='SymbolAggregate',
    aggregate_sample_data={'id': 'SPY', 'exchange': 'NYSE_ARCA', 'name': 'SPDR S&P 500 ETF Trust', 'asset_type': 'etf', 'currency': 'USD'},
    equality_fields=['id', 'exchange', 'name', 'asset_type', 'currency'],
)
class TestSymbolYahooObject:
    '''
    Bound transfer object tester for SymbolYahooObject.
    '''

    # * test: map
    def test_map(self, test_ctx, session):
        '''
        Map a Yahoo symbol to a symbol aggregate.
        '''

        test_ctx.assert_map()
