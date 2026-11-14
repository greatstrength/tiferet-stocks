"""Tiferet Stocks Symbol Alias Acceptance Tests"""

# *** imports

# ** core
from pathlib import Path
from unittest import mock

# ** infra
import pytest
import yaml
from tiferet import App, TiferetAPIError

# ** app
from tiferet_stocks import assets as a
from tests.repos.yahoo_recorded import recorded_yahoo

# *** constants

# ** constant: root_path
ROOT_PATH = Path(__file__).resolve().parents[1]

# ** constant: payloads_path
PAYLOADS_PATH = ROOT_PATH / 'tests' / 'repos' / 'payloads'

# *** fixtures

# ** fixture: reference
@pytest.fixture
def reference(monkeypatch):
    '''
    The reference client session, run from the checkout so data/symbols.yml is the alias seed, with the network
    replaced by recorded responses.

    :param monkeypatch: The pytest monkeypatch fixture.
    :type monkeypatch: pytest.MonkeyPatch
    '''

    # Run from the checkout and record every provider ticker requested.
    monkeypatch.chdir(ROOT_PATH)
    requested = []
    with mock.patch('urllib.request.urlopen', side_effect=recorded_yahoo(requested)):
        yield App('stocks_client', app_config=str(ROOT_PATH / 'config.yml')), requested

# *** tests

# ** test: symbols_get_brk_b
def test_symbols_get_brk_b(reference) -> None:
    '''
    Test that symbols.get for BRK.B requests BRK-B and returns the symbol keyed and identified as BRK.B.

    :param reference: The reference session and requested tickers.
    :type reference: tuple
    '''

    app, requested = reference

    lookup = app.run('symbols.get', data={'id': 'BRK.B', 'exchange': 'NYSE'})

    assert requested == ['BRK-B']
    assert list(lookup.symbols) == ['BRK.B']
    assert lookup.symbols['BRK.B'].id == 'BRK.B'
    assert lookup.symbols['BRK.B'].exchange == 'NYSE'
    assert lookup.failures == []

# ** test: symbols_resolve_brk_b
def test_symbols_resolve_brk_b(reference) -> None:
    '''
    Test that symbols.resolve applies the alias for BRK.B, leaves AAPL unchanged and reports an unknown ticker as data.

    :param reference: The reference session and requested tickers.
    :type reference: tuple
    '''

    app, requested = reference

    lookup = app.run('symbols.resolve', data={'ids': ['BRK.B', 'AAPL', 'ZZZZQ']})

    assert requested == ['BRK-B', 'AAPL', 'ZZZZQ']
    assert list(lookup.symbols) == ['BRK.B', 'AAPL']
    assert lookup.symbols['AAPL'].id == 'AAPL'
    assert [(f.symbol_id, f.reason, f.detail) for f in lookup.failures] == [('ZZZZQ', 'not_found', 'HTTP 404')]

# ** test: symbols_get_unknown_raises
def test_symbols_get_unknown_raises(reference) -> None:
    '''
    Test that symbols.get for an unknown ticker raises the catalogued SYMBOL_NOT_FOUND after the alias step.

    :param reference: The reference session and requested tickers.
    :type reference: tuple
    '''

    app, requested = reference

    with pytest.raises(TiferetAPIError) as exc_info:
        app.run('symbols.get', data={'id': 'ZZZZQ'})

    assert requested == ['ZZZZQ']
    assert exc_info.value.error_code == 'SYMBOL_NOT_FOUND'
    assert exc_info.value.message == 'Symbol not found: ZZZZQ.'

# ** test: quotes_get_brk_b
def test_quotes_get_brk_b(reference) -> None:
    '''
    Test that quotes.get for BRK.B and AAPL succeeds under the canonical ids.

    :param reference: The reference session and requested tickers.
    :type reference: tuple
    '''

    app, requested = reference

    quotations = app.run('quotes.get', data={'symbols': ['BRK.B', 'AAPL', 'ZZZZQ']})

    assert requested == ['cookie', 'crumb', 'quote:BRK-B,AAPL,ZZZZQ']
    assert [quote.symbol_id for quote in quotations.quotes] == ['BRK.B', 'AAPL']
    assert quotations.get_quote('BRK.B').symbol_id == 'BRK.B'
    assert quotations.get_quote('BRK.B').price == 592.94
    assert quotations.get_quote('BRK.B').source == 'yahoo_quote'
    assert quotations.get_quote('AAPL').symbol_id == 'AAPL'
    assert quotations.symbols['BRK.B'].id == 'BRK.B'
    assert [(f.symbol_id, f.reason) for f in quotations.failures] == [('ZZZZQ', 'not_found')]

# ** test: quotes_history_brk_b
def test_quotes_history_brk_b(reference) -> None:
    '''
    Test that quotes.history for BRK.B is fetched as BRK-B and its bars come back under BRK.B.

    :param reference: The reference session and requested tickers.
    :type reference: tuple
    '''

    app, requested = reference

    bars = app.run('quotes.history', data={'symbol': 'BRK.B', 'start': '2026-10-20', 'end': '2026-10-22'})

    assert requested == ['BRK-B']
    assert [bar.date for bar in bars] == ['2026-10-20', '2026-10-21', '2026-10-22']
    assert {bar.symbol_id for bar in bars} == {'BRK.B'}

# ** test: existing_raises_unchanged
def test_existing_raises_unchanged(reference) -> None:
    '''
    Test that QUOTES_UNAVAILABLE and HISTORY_UNAVAILABLE are unchanged for an unknown ticker.

    :param reference: The reference session and requested tickers.
    :type reference: tuple
    '''

    app, _ = reference

    with pytest.raises(TiferetAPIError) as quotes:
        app.run('quotes.get', data={'symbols': ['ZZZZQ']})
    with pytest.raises(TiferetAPIError) as history:
        app.run('quotes.history', data={'symbol': 'ZZZZQ', 'start': '2026-10-20', 'end': '2026-10-22'})

    assert quotes.value.error_code == 'QUOTES_UNAVAILABLE'
    assert history.value.error_code == 'HISTORY_UNAVAILABLE'
    assert history.value.message == 'No price history is available for ZZZZQ: not_found.'

# ** test: missing_seed_uses_yahoo_defaults
def test_missing_seed_uses_yahoo_defaults(tmp_path, monkeypatch) -> None:
    '''
    Test that with no local seed file nothing is configured: session start succeeds, nothing is created, and the events
    send BRK.B as BRK-B through the Yahoo default alias.

    :param tmp_path: A temporary directory holding only a copy of the reference config.
    :type tmp_path: pathlib.Path
    :param monkeypatch: The pytest monkeypatch fixture.
    :type monkeypatch: pytest.MonkeyPatch
    '''

    (tmp_path / 'config.yml').write_bytes((ROOT_PATH / 'config.yml').read_bytes())
    monkeypatch.chdir(tmp_path)
    requested = []
    with mock.patch('urllib.request.urlopen', side_effect=recorded_yahoo(requested)):
        app = App('stocks_client', app_config=str(tmp_path / 'config.yml'))
        quotations = app.run('quotes.get', data={'symbols': ['BRK.B']})

    assert requested == ['cookie', 'crumb', 'quote:BRK-B']
    assert quotations.get_quote('BRK.B').price == 592.94
    assert not (tmp_path / 'data').exists()

# ** test: alias_artifact_wired_independently
def test_alias_artifact_wired_independently(tmp_path, monkeypatch) -> None:
    '''
    Test that pointing only the alias artifact at another file changes aliasing with no change to the lookup or price
    services.

    :param tmp_path: A temporary directory.
    :type tmp_path: pathlib.Path
    :param monkeypatch: The pytest monkeypatch fixture.
    :type monkeypatch: pytest.MonkeyPatch
    '''

    # Copy the reference config and change only the alias artifact's path.
    config = yaml.safe_load((ROOT_PATH / 'config.yml').read_text())
    reference = yaml.safe_load((ROOT_PATH / 'config.yml').read_text())
    (tmp_path / 'aliases.yml').write_text(yaml.safe_dump({'aliases': [{'provider': 'yahoo_chart', 'provider_ticker': 'AAPL', 'canonical_id': 'APPLE'}]}))
    config['services'][a.SYMBOL_ALIAS_SERVICE_ID]['params'] = {'symbol_config': str(tmp_path / 'aliases.yml')}
    (tmp_path / 'config.yml').write_text(yaml.safe_dump(config, sort_keys=False))
    monkeypatch.chdir(tmp_path)

    # Quote the new canonical id through the unchanged price service.
    requested = []
    with mock.patch('urllib.request.urlopen', side_effect=recorded_yahoo(requested)):
        quotations = App('stocks_client', app_config=str(tmp_path / 'config.yml')).run('quotes.get', data={'symbols': ['APPLE']})

    assert requested == ['cookie', 'crumb', 'quote:AAPL']
    assert quotations.get_quote('APPLE').symbol_id == 'APPLE'
    for service_id in (a.SYMBOL_LOOKUP_SERVICE_ID, a.PRICE_SERVICE_ID):
        assert config['services'][service_id] == reference['services'][service_id]

# ** test: app_configured_ticker_replaces_default
def test_app_configured_ticker_replaces_yahoo_default(tmp_path, monkeypatch) -> None:
    '''
    Test that through the programmatic App a symbols file sending BRK.B as BRKB.X replaces the Yahoo default in both
    directions: BRKB.X goes out, BRK-B is never sent for BRK.B, and a raw BRK-B request stays BRK-B.

    :param tmp_path: A temporary directory holding a copy of the reference config and the symbols file.
    :type tmp_path: pathlib.Path
    :param monkeypatch: The pytest monkeypatch fixture.
    :type monkeypatch: pytest.MonkeyPatch
    '''

    (tmp_path / 'config.yml').write_bytes((ROOT_PATH / 'config.yml').read_bytes())
    (tmp_path / 'data').mkdir()
    (tmp_path / 'data' / 'symbols.yml').write_text(yaml.safe_dump({'aliases': [{'provider': 'yahoo_chart', 'provider_ticker': 'BRKB.X', 'canonical_id': 'BRK.B'}]}))
    monkeypatch.chdir(tmp_path)
    requested = []
    with mock.patch('urllib.request.urlopen', side_effect=recorded_yahoo(requested)):
        quotations = App('stocks_client', app_config=str(tmp_path / 'config.yml')).run('quotes.get', data={'symbols': ['BRK.B', 'BRK-B']})

    assert requested == ['cookie', 'crumb', 'quote:BRKB.X,BRK-B']
    assert [quote.symbol_id for quote in quotations.quotes] == ['BRK-B']
    assert [(failure.symbol_id, failure.reason) for failure in quotations.failures] == [('BRK.B', 'not_found')]
