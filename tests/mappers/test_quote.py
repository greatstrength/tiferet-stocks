"""Tiferet Stocks Quote Mapper Tests"""

# *** imports

# ** app
from tiferet_stocks.domain import Quote, QuoteList
from tiferet_stocks.mappers import QuoteListAggregate

# *** tests

# ** test: quote_list_aggregate_is_quote_list
def test_quote_list_aggregate_is_quote_list() -> None:
    '''
    Test that the provider aggregate is a QuoteList with no settable attributes.
    '''

    quotes = QuoteListAggregate(quotes=[Quote(symbol_id='SPY', price=680.0, source='static')])

    assert isinstance(quotes, QuoteList)
    assert QuoteListAggregate._SETTABLE_ATTRIBUTES == set()
    assert quotes.get_quote('SPY').price == 680.0
