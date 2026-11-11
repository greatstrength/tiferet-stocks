"""Tiferet Stocks CLI Presentation Tests"""

# *** imports

# ** infra
import pytest
from tiferet.contexts.cli import CliRequestContext
from tiferet.domain.cli import CliOutputRecord, CliRecordList

# ** app
from tiferet_stocks.contexts.cli import StocksCliRequestContext, build_symbol_rows
from tiferet_stocks.domain import PriceBar, Quote, QuoteFailure, Quotations, Symbol, SymbolLookup, SymbolWarning, Watchlist

# *** tests

# ** test: quote_rows_retain_complete_records
def test_quote_rows_retain_complete_records() -> None:
    '''
    Keep quote fields, provider identity, metadata and repeated warning/failure details.

    :return: None; assertions enforce the contract.
    :rtype: None
    '''

    result = Quotations(
        quotes={'SPY': Quote(symbol_id='DIFFERENT', price=600.5, previous_close=600.0, change_pct=0.0833, market_time='2026-11-06T14:00:00-07:00', currency='USD', source='static')},
        symbols={'SPY': Symbol(id='DIFFERENT', name='Example', exchange='NYSE_ARCA', asset_type='etf', currency='CAD')},
        failures=[QuoteFailure(symbol_id='SPY', reason='timeout', detail='first', attempts=2), QuoteFailure(symbol_id='SPY', reason='http_error', detail='second', attempts=1), QuoteFailure(symbol_id='BAD', reason='not_found', detail='absent')],
        warnings=[SymbolWarning(symbol_id='SPY', reason='unmapped_exchange', detail='PNK'), SymbolWarning(symbol_id='SPY', reason='unmapped_asset_type', detail='OTHER')],
        fetched_at='2026-11-06T14:00:00-07:00',
    )
    before = result.model_dump()
    rows = build_symbol_rows(result)

    assert [row['symbol_id'] for row in rows] == ['SPY', 'BAD']
    row = rows[0]
    assert row['status'] == 'partial'
    assert row['quote_symbol_id'] == 'DIFFERENT'
    assert row['symbol_id'] == 'SPY'
    assert row['currency'] == 'USD'
    assert row['symbol_currency'] == 'CAD'
    for key, value in result.quotes['SPY'].model_dump(exclude_none=True).items():
        assert row['quote_symbol_id' if key == 'symbol_id' else key] == value
    for key, value in result.symbols['SPY'].model_dump(exclude_none=True).items():
        assert row['resolved_symbol_id' if key == 'id' else f'symbol_{key}'] == value
    for label, records in [('failure', result.failures[:2]), ('warning', result.warnings)]:
        for number, record in enumerate(records, start=1):
            for key, value in record.model_dump(exclude_none=True).items():
                assert row[f'{label}_{number}_{key}'] == value
    assert row['fetched_at'] == result.fetched_at
    assert row['failure_count'] == row['warning_count'] == 2
    assert rows[1]['failure_1_detail'] == 'absent'
    assert rows[1]['status'] == 'failed'
    assert result.model_dump() == before

    # Exercise the final native renderer as well as the complete intermediate rows.
    request = StocksCliRequestContext()
    request.set_result(result)
    rendered = request.handle_response().format_output()
    for column in ['failure_2_reason', 'failure_2_detail', 'failure_2_attempts', 'warning_2_reason', 'warning_2_detail']:
        assert column in rendered
    for detail in ['first', 'second', 'absent', 'unmapped_exchange', 'unmapped_asset_type', 'PNK', 'OTHER']:
        assert detail in rendered
    assert request.result is result
    assert result.model_dump() == before

# ** test: lookup_rows_include_warning_only_and_failure_only_symbols
def test_lookup_rows_include_warning_only_and_failure_only_symbols() -> None:
    '''
    Preserve every named result even when no success record exists for that id.

    :return: None; assertions enforce the contract.
    :rtype: None
    '''

    result = SymbolLookup(
        symbols={'SPY': Symbol(id='SPY', name='Example')},
        failures=[QuoteFailure(symbol_id='BAD', reason='not_found', detail='missing')],
        warnings=[SymbolWarning(symbol_id='WARN', reason='unmapped_exchange', detail='PNK')],
    )
    rows = build_symbol_rows(result)

    assert [row['symbol_id'] for row in rows] == ['SPY', 'BAD', 'WARN']
    assert [row['status'] for row in rows] == ['ok', 'failed', 'warning']
    assert rows[1]['failure_1_reason'] == 'not_found'
    assert rows[2]['warning_1_reason'] == 'unmapped_exchange'
    assert rows[2]['warning_1_detail'] == 'PNK'

# ** test: native_symbol_tables_preserve_raw_result
@pytest.mark.parametrize('result', [
    Quotations(quotes={'SPY': Quote(symbol_id='SPY', price=600.0, source='static')}, failures=[QuoteFailure(symbol_id='BAD', reason='not_found')]),
    SymbolLookup(symbols={'SPY': Symbol(id='SPY')}, warnings=[SymbolWarning(symbol_id='SPY', reason='unmapped_exchange', detail='PNK')]),
    Quotations(),
    SymbolLookup(),
])
def test_native_symbol_tables_preserve_raw_result(result) -> None:
    '''
    Return native table models without modifying or replacing library answers.

    :param result: A quote or lookup answer.
    :type result: Quotations | SymbolLookup

    :return: None; assertions enforce the contract.
    :rtype: None
    '''

    request = StocksCliRequestContext(feature_id='quotes.get')
    request.set_result(result)
    before = result.model_dump()
    output = request.handle_response()

    assert isinstance(output, CliRecordList)
    assert request.result is result
    assert result.model_dump() == before
    text = output.format_output()
    if result.failures:
        assert 'BAD' in text and 'not_found' in text
    if result.warnings:
        assert 'PNK' in text and 'unmapped_exchange' in text

# ** test: other_outputs_match_native_core
@pytest.mark.parametrize('result', [
    [PriceBar(symbol_id='SPY', date='2026-11-06', open=1.0, high=2.0, low=0.5, close=1.5)],
    ['NYSE', 'NASDAQ'],
    Watchlist(id='one', name='One', symbol_ids=['SPY', 'QQQ']),
    [Watchlist(id='one', name='One')],
    [],
    'deleted',
])
def test_other_outputs_match_native_core(result) -> None:
    '''
    Leave history, exchanges, watchlists, empty results and primitive output native.

    :param result: A non-symbol-answer feature result.
    :type result: Any

    :return: None; assertions enforce the contract.
    :rtype: None
    '''

    native = CliRequestContext()
    adapted = StocksCliRequestContext()
    native.set_result(result)
    adapted.set_result(result)
    expected = native.handle_response()
    actual = adapted.handle_response()

    assert type(actual) is type(expected)
    if isinstance(actual, (CliOutputRecord, CliRecordList)):
        assert actual.format_output() == expected.format_output()
    else:
        assert actual == expected
    assert adapted.result is result
