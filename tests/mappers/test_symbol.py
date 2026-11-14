"""Tiferet Stocks Symbol Mapper Tests"""

# *** imports

# ** core
import inspect

# ** infra
import pytest
from pydantic import ValidationError
from tiferet import use_tester
from tiferet.domain import ModelError

# ** app
from tiferet_stocks.domain import YAHOO_CHART, SymbolAlias
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
    assert symbol.aliases == []

# ** test: symbol_aggregate_rejects_unsettable_attributes
def test_symbol_aggregate_rejects_unsettable_attributes() -> None:
    '''
    Test that a symbol aggregate rejects set_attribute for every field except id.
    '''

    symbol = SymbolAggregate(id='AAPL', exchange='NASDAQ')

    with pytest.raises(ModelError):
        symbol.set_attribute('exchange', 'NYSE')
    with pytest.raises(ModelError):
        symbol.set_attribute('name', 'Apple')
    with pytest.raises(ModelError):
        symbol.set_attribute('aliases', [])

# ** test: apply_alias_sets_id_from_provider_ticker
def test_apply_alias_sets_id_from_provider_ticker() -> None:
    '''
    Test that apply_alias sets id from the provider ticker to the canonical id.
    '''

    alias = SymbolAlias(provider=YAHOO_CHART, provider_ticker='BRK-B', canonical_id='BRK.B')
    symbol = SymbolAggregate(id='BRK-B', aliases=[alias])

    symbol.apply_alias(alias)

    assert symbol.id == 'BRK.B'
    assert symbol.aliases == [alias]

# ** test: apply_alias_keeps_canonical_id
def test_apply_alias_keeps_canonical_id() -> None:
    '''
    Test that apply_alias leaves id unchanged when it is already the canonical id.
    '''

    alias = SymbolAlias(provider=YAHOO_CHART, provider_ticker='BRK-B', canonical_id='BRK.B')
    symbol = SymbolAggregate(id='BRK.B', aliases=[alias])

    symbol.apply_alias(alias)

    assert symbol.id == 'BRK.B'

# ** test: apply_alias_rejects_alias_not_in_collection
def test_apply_alias_rejects_alias_not_in_collection() -> None:
    '''
    Test that apply_alias rejects an alias that is not in the collection.
    '''

    alias = SymbolAlias(provider=YAHOO_CHART, provider_ticker='BRK-B', canonical_id='BRK.B')
    symbol = SymbolAggregate(id='BRK-B')

    with pytest.raises(ModelError) as caught:
        symbol.apply_alias(alias)

    assert caught.value.error_code == 'ALIAS_NOT_IN_COLLECTION'
    assert symbol.id == 'BRK-B'

# ** test: set_alias_then_apply_alias
def test_set_alias_then_apply_alias() -> None:
    '''
    Test that set_alias places the value object on the collection, and apply_alias then sets id.
    '''

    alias = SymbolAlias(provider=YAHOO_CHART, provider_ticker='BRK-B', canonical_id='BRK.B')
    symbol = SymbolAggregate(id='BRK-B')

    symbol.set_alias(alias)
    assert symbol.aliases == [alias]
    assert symbol.id == 'BRK-B'

    symbol.apply_alias(alias)
    assert symbol.id == 'BRK.B'

# ** test: set_alias_overwrites_same_provider
def test_set_alias_overwrites_the_alias_for_the_same_provider() -> None:
    '''
    Test that set_alias replaces the alias the symbol already has for the provider, so X1 then X2 for BRK.B leaves X2.
    '''

    first = SymbolAlias(provider=YAHOO_CHART, provider_ticker='X1', canonical_id='BRK.B')
    second = SymbolAlias(provider=YAHOO_CHART, provider_ticker='X2', canonical_id='BRK.B')
    symbol = SymbolAggregate(id='BRK.B')

    symbol.set_alias(first)
    symbol.set_alias(second)

    assert symbol.aliases == [second]

# ** test: set_alias_rejects_alias_for_another_symbol
def test_set_alias_rejects_alias_for_another_symbol() -> None:
    '''
    Test that set_alias rejects an alias that does not belong to this symbol.
    '''

    alias = SymbolAlias(provider=YAHOO_CHART, provider_ticker='BRK-B', canonical_id='BRK.B')
    symbol = SymbolAggregate(id='AAPL')

    with pytest.raises(ModelError) as caught:
        symbol.set_alias(alias)

    assert caught.value.error_code == 'ALIAS_NOT_FOR_SYMBOL'
    assert symbol.aliases == []

# ** test: only_apply_alias_sets_id
def test_only_apply_alias_sets_id() -> None:
    '''
    Test that apply_alias is the only SymbolAggregate method that sets id.
    '''

    apply_source = inspect.getsource(SymbolAggregate.apply_alias)
    assert "set_attribute('id'" in apply_source

    for name, value in vars(SymbolAggregate).items():
        if name == 'apply_alias' or not callable(value):
            continue
        source = inspect.getsource(value)
        assert "set_attribute('id'" not in source
        assert 'set_attribute("id"' not in source

# *** testers

# ** tester: test_symbol_aggregate
@use_tester(
    type='aggregate',
    target_cls=SymbolAggregate,
    sample_data={'id': 'AAPL', 'exchange': 'NASDAQ', 'name': 'Apple Inc.', 'asset_type': 'equity', 'currency': 'USD'},
    equality_fields=['id', 'exchange', 'name', 'asset_type', 'currency', 'aliases'],
    set_attribute_params=[
        ('exchange', 'NYSE', 'ATTRIBUTE_NOT_SETTABLE'),
        ('name', 'Apple', 'ATTRIBUTE_NOT_SETTABLE'),
    ],
)
class TestSymbolAggregate:
    '''
    Bound aggregate tester for SymbolAggregate: constructible, with id set only by apply_alias.
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
        Reject attribute changes that are not on the allow-list.
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
    equality_fields=['id', 'exchange', 'name', 'asset_type', 'currency', 'aliases'],
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
