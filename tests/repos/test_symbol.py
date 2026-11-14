"""Tiferet Stocks Symbol Repository Tests"""

# *** imports

# ** core
import io
import json
import os
import socket
from http import client as http_client
from pathlib import Path
from typing import Any
from unittest import mock
from urllib import error as url_error

# ** infra
import pytest
from pydantic import ValidationError
from tiferet.interfaces import ServiceError

# ** app
from tiferet_stocks.interfaces import SymbolAliasService, SymbolLookupService
from tiferet_stocks.repos.symbol import SymbolAliasRepository, YahooChartSymbolRepository
from tiferet_stocks.repos.yahoo import YahooChartClient, YahooChartPriceRepository

# *** constants

# ** constant: payloads_path
PAYLOADS_PATH = os.path.join(os.path.dirname(__file__), 'payloads')

# ** constant: seed_path
SEED_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'data', 'symbols.yml')

# *** functions

# ** function: read_payload
def read_payload(name: str) -> bytes:
    '''
    Read a recorded Yahoo chart response.

    :param name: The payload file name without extension.
    :type name: str
    :return: The raw response body.
    :rtype: bytes
    '''

    # Read and return the recorded body.
    with open(os.path.join(PAYLOADS_PATH, f'{name}.json'), 'rb') as file:
        return file.read()

# ** function: make_response
def make_response(body: bytes) -> Any:
    '''
    Wrap a body as a context-managed urlopen response.

    :param body: The response body.
    :type body: bytes
    :return: A mock response.
    :rtype: Any
    '''

    # Build a context manager that yields a readable body.
    response = mock.MagicMock()
    response.__enter__.return_value = io.BytesIO(body)
    return response

# ** function: make_http_error
def make_http_error(code: int) -> url_error.HTTPError:
    '''
    Build an HTTP error with the given status code.

    :param code: The HTTP status code.
    :type code: int
    :return: The HTTP error.
    :rtype: url_error.HTTPError
    '''

    # Build and return the error.
    return url_error.HTTPError('https://example.test', code, 'error', {}, io.BytesIO(b''))

# *** fixtures

# ** fixture: lookup_repo
@pytest.fixture
def lookup_repo() -> YahooChartSymbolRepository:
    '''
    A Yahoo symbol repository with configuration-style string parameters.
    '''

    return YahooChartSymbolRepository(timeout='5', retries='1')

# ** fixture: urlopen
@pytest.fixture
def urlopen():
    '''
    Patch urlopen so no test touches the network.
    '''

    with mock.patch('urllib.request.urlopen') as patched:
        yield patched

# *** tests

# ** test: alias_repo_reads_seed
def test_alias_repo_reads_seed() -> None:
    '''
    Test that the reference seed holds the BRK.B Yahoo alias, keyed by provider ticker.
    '''

    repo = SymbolAliasRepository(symbol_config=SEED_PATH)
    aliases = repo.get_aliases('yahoo_chart')

    assert isinstance(repo, SymbolAliasService)
    assert aliases['BRK-B'].provider == 'yahoo_chart'
    assert aliases['BRK-B'].provider_ticker == 'BRK-B'
    assert aliases['BRK-B'].canonical_id == 'BRK.B'

# ** test: alias_repo_filters_by_provider
@pytest.mark.parametrize('extension', ['yml', 'json'])
def test_alias_repo_filters_by_provider(tmp_path: Path, extension: str) -> None:
    '''
    Test that get_aliases returns only the requested provider's rows, keyed by provider ticker, in YAML or JSON.

    :param tmp_path: The temporary directory.
    :type tmp_path: Path
    :param extension: The file format.
    :type extension: str
    '''

    path = tmp_path / f'symbols.{extension}'
    path.write_text(json.dumps({'aliases': [
        {'provider': 'yahoo_chart', 'provider_ticker': 'BRK-B', 'canonical_id': 'BRK.B'},
        {'provider': 'yahoo_chart', 'provider_ticker': 'BF-B', 'canonical_id': 'BF.B'},
        {'provider': 'other', 'provider_ticker': 'BRK/B', 'canonical_id': 'BRK.B'},
    ]}))
    repo = SymbolAliasRepository(symbol_config=str(path))

    aliases = repo.get_aliases('yahoo_chart')

    assert list(aliases) == ['BRK-B', 'BF-B']
    assert aliases['BF-B'].canonical_id == 'BF.B'
    assert repo.get_aliases('other_provider') == {}

# ** test: alias_repo_empty_documents
@pytest.mark.parametrize('content', ['', 'other: {}\n', 'aliases:\n', 'aliases: []\n'])
def test_alias_repo_empty_documents(tmp_path: Path, content: str) -> None:
    '''
    Test that an empty document, or one with no aliases rows, is an empty map.

    :param tmp_path: The temporary directory.
    :type tmp_path: Path
    :param content: The document content.
    :type content: str
    '''

    path = tmp_path / 'symbols.yml'
    path.write_text(content)

    assert SymbolAliasRepository(symbol_config=str(path)).get_aliases('yahoo_chart') == {}
    assert path.read_text() == content

# ** test: alias_repo_missing_file_is_empty
@pytest.mark.parametrize('extension', ['yml', 'yaml', 'json'])
def test_alias_repo_missing_file_is_empty(tmp_path: Path, extension: str) -> None:
    '''
    Test that a missing file and parent are an empty map, do not raise, and are not created.

    :param tmp_path: The temporary directory.
    :type tmp_path: Path
    :param extension: The supported file format.
    :type extension: str
    '''

    path = tmp_path / 'missing' / f'symbols.{extension}'

    assert SymbolAliasRepository(symbol_config=str(path)).get_aliases('yahoo_chart') == {}
    assert not path.exists()
    assert not path.parent.exists()

# ** test: alias_repo_unsupported_extension
def test_alias_repo_unsupported_extension(tmp_path: Path) -> None:
    '''
    Test that an unsupported extension stays a core error, even for a missing file.

    :param tmp_path: The temporary directory.
    :type tmp_path: Path
    '''

    path = tmp_path / 'symbols.txt'

    with pytest.raises(ServiceError) as raised:
        SymbolAliasRepository(symbol_config=str(path)).get_aliases('yahoo_chart')

    assert raised.value.error_code == 'UNSUPPORTED_CONFIG_FILE_TYPE'

# ** test: alias_repo_malformed_document
@pytest.mark.parametrize('extension, content', [('yml', 'aliases: ['), ('json', '{invalid')])
def test_alias_repo_malformed_document(tmp_path: Path, extension: str, content: str) -> None:
    '''
    Test that a parse failure stays a core error and is not turned into empty data.

    :param tmp_path: The temporary directory.
    :type tmp_path: Path
    :param extension: The file format.
    :type extension: str
    :param content: The malformed file content.
    :type content: str
    '''

    path = tmp_path / f'symbols.{extension}'
    path.write_text(content)

    with pytest.raises(ServiceError):
        SymbolAliasRepository(symbol_config=str(path)).get_aliases('yahoo_chart')

    assert path.read_text() == content

# ** test: alias_repo_invalid_row
def test_alias_repo_invalid_row(tmp_path: Path) -> None:
    '''
    Test that an invalid row for the requested provider is validated rather than dropped.

    :param tmp_path: The temporary directory.
    :type tmp_path: Path
    '''

    path = tmp_path / 'symbols.yml'
    path.write_text('aliases:\n  - provider: yahoo_chart\n    provider_ticker: BRK-B\n')

    with pytest.raises(ValidationError):
        SymbolAliasRepository(symbol_config=str(path)).get_aliases('yahoo_chart')

# ** test: alias_repo_access_failure_is_not_empty
def test_alias_repo_access_failure_is_not_empty(tmp_path: Path, monkeypatch) -> None:
    '''
    Test that a permission failure in the absence check propagates instead of returning emptiness.

    :param tmp_path: The temporary directory.
    :type tmp_path: Path
    :param monkeypatch: The scoped patch fixture.
    :type monkeypatch: pytest.MonkeyPatch
    '''

    path = tmp_path / 'symbols.yml'
    repo = SymbolAliasRepository(symbol_config=str(path))

    with monkeypatch.context() as patch:
        patch.setattr(Path, 'stat', lambda self: (_ for _ in ()).throw(PermissionError('denied')))
        with pytest.raises(PermissionError, match='denied'):
            repo.get_aliases('yahoo_chart')

    assert not path.exists()

# ** test: symbol_repo_shares_chart_client
def test_symbol_repo_shares_chart_client(lookup_repo: YahooChartSymbolRepository) -> None:
    '''
    Test that the Yahoo symbol repository uses the shared chart client and converts string parameters, and that the
    price repository no longer implements symbol lookup.

    :param lookup_repo: The Yahoo symbol repository.
    :type lookup_repo: YahooChartSymbolRepository
    '''

    assert isinstance(lookup_repo, SymbolLookupService)
    assert isinstance(lookup_repo, YahooChartClient)
    assert issubclass(YahooChartPriceRepository, YahooChartClient)
    assert not issubclass(YahooChartPriceRepository, SymbolLookupService)
    assert not hasattr(YahooChartPriceRepository, 'lookup')
    assert lookup_repo.timeout == 5.0
    assert lookup_repo.retries == 1

# ** test: lookup_takes_the_id_it_is_given
def test_lookup_takes_the_id_it_is_given(lookup_repo: YahooChartSymbolRepository, urlopen: mock.Mock) -> None:
    '''
    Test that the Yahoo symbol repository requests the id as given, with no alias of its own.

    :param lookup_repo: The Yahoo symbol repository.
    :type lookup_repo: YahooChartSymbolRepository
    :param urlopen: The patched urlopen.
    :type urlopen: mock.Mock
    '''

    urlopen.side_effect = make_http_error(404)

    lookup = lookup_repo.lookup(['BRK.B'])

    assert '/chart/BRK.B?' in urlopen.call_args[0][0].full_url
    assert lookup.symbols == {}
    assert [(f.symbol_id, f.reason, f.detail) for f in lookup.failures] == [('BRK.B', 'not_found', 'HTTP 404')]

# ** test: lookup_recorded_payloads
@pytest.mark.parametrize('symbol_id, exchange, asset_type', [
    ('AAPL', 'NASDAQ', 'equity'),
    ('QQQ', 'NASDAQ', 'etf'),
    ('PLUG', 'NASDAQ', 'equity'),
    ('IBM', 'NYSE', 'equity'),
    ('SPY', 'NYSE_ARCA', 'etf'),
    ('XLK', 'NYSE_ARCA', 'etf'),
    ('ARKK', 'CBOE_BZX', 'etf'),
    ('IMO', 'NYSE_AMERICAN', 'equity'),
    ('BRK-B', 'NYSE', 'equity'),
])
def test_lookup_recorded_payloads(lookup_repo: YahooChartSymbolRepository,
                                  urlopen: mock.Mock,
                                  symbol_id: str,
                                  exchange: str,
                                  asset_type: str) -> None:
    '''
    Test that recorded payloads translate to domain exchange ids and asset types with no warning.

    :param lookup_repo: The Yahoo symbol repository.
    :type lookup_repo: YahooChartSymbolRepository
    :param urlopen: The patched urlopen.
    :type urlopen: mock.Mock
    :param symbol_id: The requested symbol id.
    :type symbol_id: str
    :param exchange: The expected exchange id.
    :type exchange: str
    :param asset_type: The expected asset type.
    :type asset_type: str
    '''

    urlopen.return_value = make_response(read_payload(symbol_id.lower()))

    lookup = lookup_repo.lookup([symbol_id])

    assert lookup.symbols[symbol_id].exchange == exchange
    assert lookup.symbols[symbol_id].asset_type == asset_type
    assert lookup.warnings == []
    assert lookup.failures == []

# ** test: lookup_unmapped_exchange
def test_lookup_unmapped_exchange(lookup_repo: YahooChartSymbolRepository, urlopen: mock.Mock) -> None:
    '''
    Test that an unmapped exchange code gives an empty exchange and one warning carrying the raw code.

    :param lookup_repo: The Yahoo symbol repository.
    :type lookup_repo: YahooChartSymbolRepository
    :param urlopen: The patched urlopen.
    :type urlopen: mock.Mock
    '''

    urlopen.return_value = make_response(read_payload('tcehy'))

    lookup = lookup_repo.lookup(['TCEHY'])

    assert lookup.symbols['TCEHY'].exchange is None
    assert lookup.symbols['TCEHY'].asset_type == 'equity'
    assert len(lookup.warnings) == 1
    assert lookup.warnings[0].reason == 'unmapped_exchange'
    assert lookup.warnings[0].detail == 'PNK'
    assert lookup.failures == []

# ** test: lookup_money_market_fund
def test_lookup_money_market_fund(lookup_repo: YahooChartSymbolRepository, urlopen: mock.Mock) -> None:
    '''
    Test that a money market fund gets an empty exchange and no warning.

    :param lookup_repo: The Yahoo symbol repository.
    :type lookup_repo: YahooChartSymbolRepository
    :param urlopen: The patched urlopen.
    :type urlopen: mock.Mock
    '''

    urlopen.return_value = make_response(read_payload('frsxx'))

    lookup = lookup_repo.lookup(['FRSXX'])

    assert lookup.symbols['FRSXX'].exchange is None
    assert lookup.symbols['FRSXX'].asset_type == 'money_market_fund'
    assert lookup.warnings == []

# ** test: lookup_unmapped_asset_type
def test_lookup_unmapped_asset_type(lookup_repo: YahooChartSymbolRepository, urlopen: mock.Mock) -> None:
    '''
    Test that an unmapped instrument type gives an empty asset type and an unmapped_asset_type warning.

    :param lookup_repo: The Yahoo symbol repository.
    :type lookup_repo: YahooChartSymbolRepository
    :param urlopen: The patched urlopen.
    :type urlopen: mock.Mock
    '''

    payload = json.loads(read_payload('aapl'))
    payload['chart']['result'][0]['meta']['instrumentType'] = 'FUTURE'
    urlopen.return_value = make_response(json.dumps(payload).encode())

    lookup = lookup_repo.lookup(['AAPL'])

    assert lookup.symbols['AAPL'].asset_type is None
    assert lookup.symbols['AAPL'].exchange == 'NASDAQ'
    assert [(w.reason, w.detail) for w in lookup.warnings] == [('unmapped_asset_type', 'FUTURE')]

# ** test: lookup_not_found
def test_lookup_not_found(lookup_repo: YahooChartSymbolRepository, urlopen: mock.Mock) -> None:
    '''
    Test that a 404 is a not_found failure after one attempt, with no retry.

    :param lookup_repo: The Yahoo symbol repository.
    :type lookup_repo: YahooChartSymbolRepository
    :param urlopen: The patched urlopen.
    :type urlopen: mock.Mock
    '''

    urlopen.side_effect = make_http_error(404)

    lookup = lookup_repo.lookup(['ZZZZQ'])

    assert lookup.symbols == {}
    assert lookup.failures[0].reason == 'not_found'
    assert lookup.failures[0].attempts == 1
    assert urlopen.call_count == 1

# ** test: lookup_timeout_then_success
def test_lookup_timeout_then_success(lookup_repo: YahooChartSymbolRepository, urlopen: mock.Mock) -> None:
    '''
    Test that a timeout followed by success returns the symbol, proving the single retry.

    :param lookup_repo: The Yahoo symbol repository.
    :type lookup_repo: YahooChartSymbolRepository
    :param urlopen: The patched urlopen.
    :type urlopen: mock.Mock
    '''

    urlopen.side_effect = [socket.timeout('timed out'), make_response(read_payload('aapl'))]

    lookup = lookup_repo.lookup(['AAPL'])

    assert lookup.symbols['AAPL'].exchange == 'NASDAQ'
    assert lookup.failures == []
    assert urlopen.call_count == 2

# ** test: lookup_timeout_exhausted
def test_lookup_timeout_exhausted(lookup_repo: YahooChartSymbolRepository, urlopen: mock.Mock) -> None:
    '''
    Test that two timeouts give a timeout failure with two attempts.

    :param lookup_repo: The Yahoo symbol repository.
    :type lookup_repo: YahooChartSymbolRepository
    :param urlopen: The patched urlopen.
    :type urlopen: mock.Mock
    '''

    urlopen.side_effect = [url_error.URLError(socket.timeout('timed out')), socket.timeout('timed out')]

    lookup = lookup_repo.lookup(['AAPL'])

    assert lookup.failures[0].reason == 'timeout'
    assert lookup.failures[0].attempts == 2

# ** test: lookup_http_error
def test_lookup_http_error(lookup_repo: YahooChartSymbolRepository, urlopen: mock.Mock) -> None:
    '''
    Test that repeated server errors give an http_error failure carrying the status.

    :param lookup_repo: The Yahoo symbol repository.
    :type lookup_repo: YahooChartSymbolRepository
    :param urlopen: The patched urlopen.
    :type urlopen: mock.Mock
    '''

    urlopen.side_effect = [make_http_error(500), make_http_error(503)]

    lookup = lookup_repo.lookup(['AAPL'])

    assert lookup.failures[0].reason == 'http_error'
    assert lookup.failures[0].detail == 'HTTP 503'
    assert lookup.failures[0].attempts == 2

# ** test: lookup_malformed_json
@pytest.mark.parametrize('body', [b'not json', b'{"chart": {"result": [{}]}}', b'{"chart": {"result": null, "error": null}}'])
def test_lookup_malformed_json(lookup_repo: YahooChartSymbolRepository, urlopen: mock.Mock, body: bytes) -> None:
    '''
    Test that a malformed body is a bad_payload failure.

    :param lookup_repo: The Yahoo symbol repository.
    :type lookup_repo: YahooChartSymbolRepository
    :param urlopen: The patched urlopen.
    :type urlopen: mock.Mock
    :param body: The malformed response body.
    :type body: bytes
    '''

    urlopen.return_value = make_response(body)

    lookup = lookup_repo.lookup(['AAPL'])

    assert lookup.symbols == {}
    assert lookup.failures[0].reason == 'bad_payload'

# ** test: lookup_not_found_body
def test_lookup_not_found_body(lookup_repo: YahooChartSymbolRepository, urlopen: mock.Mock) -> None:
    '''
    Test that a Not Found chart error body is a not_found failure.

    :param lookup_repo: The Yahoo symbol repository.
    :type lookup_repo: YahooChartSymbolRepository
    :param urlopen: The patched urlopen.
    :type urlopen: mock.Mock
    '''

    urlopen.return_value = make_response(b'{"chart": {"result": null, "error": {"code": "Not Found", "description": "No data found"}}}')

    lookup = lookup_repo.lookup(['ZZZZQ'])

    assert lookup.failures[0].reason == 'not_found'
    assert lookup.failures[0].detail == 'No data found'

# ** test: lookup_many
def test_lookup_many(lookup_repo: YahooChartSymbolRepository, urlopen: mock.Mock) -> None:
    '''
    Test that a batch returns every id as a result or a failure, and one failure does not fail the batch.

    :param lookup_repo: The Yahoo symbol repository.
    :type lookup_repo: YahooChartSymbolRepository
    :param urlopen: The patched urlopen.
    :type urlopen: mock.Mock
    '''

    urlopen.side_effect = [make_response(read_payload('spy')), make_http_error(404), make_response(read_payload('tcehy'))]

    lookup = lookup_repo.lookup(['SPY', 'ZZZZQ', 'TCEHY', 'SPY'])

    assert list(lookup.symbols) == ['SPY', 'TCEHY']
    assert [failure.symbol_id for failure in lookup.failures] == ['ZZZZQ']
    assert urlopen.call_count == 3

# ** test: lookup_connection_error_then_success
@pytest.mark.parametrize('error', [
    http_client.RemoteDisconnected('Remote end closed connection without response'),
    ConnectionResetError('Connection reset by peer'),
    http_client.IncompleteRead(b'partial'),
])
def test_lookup_connection_error_then_success(lookup_repo: YahooChartSymbolRepository,
                                              urlopen: mock.Mock,
                                              error: Exception) -> None:
    '''
    Test that a dropped or truncated response is retried and does not abort the lookup.

    :param lookup_repo: The Yahoo symbol repository.
    :type lookup_repo: YahooChartSymbolRepository
    :param urlopen: The patched urlopen.
    :type urlopen: mock.Mock
    :param error: The connection-level error raised on the first attempt.
    :type error: Exception
    '''

    urlopen.side_effect = [error, make_response(read_payload('aapl'))]

    lookup = lookup_repo.lookup(['AAPL'])

    assert lookup.symbols['AAPL'].exchange == 'NASDAQ'
    assert lookup.failures == []
    assert urlopen.call_count == 2

# ** test: lookup_connection_error_exhausted
def test_lookup_connection_error_exhausted(lookup_repo: YahooChartSymbolRepository, urlopen: mock.Mock) -> None:
    '''
    Test that repeated connection errors become an http_error failure while the rest of the batch resolves.

    :param lookup_repo: The Yahoo symbol repository.
    :type lookup_repo: YahooChartSymbolRepository
    :param urlopen: The patched urlopen.
    :type urlopen: mock.Mock
    '''

    urlopen.side_effect = [
        http_client.RemoteDisconnected('closed'),
        ConnectionResetError('reset'),
        make_response(read_payload('spy')),
    ]

    lookup = lookup_repo.lookup(['AAPL', 'SPY'])

    assert list(lookup.symbols) == ['SPY']
    assert lookup.failures[0].symbol_id == 'AAPL'
    assert lookup.failures[0].reason == 'http_error'
    assert lookup.failures[0].attempts == 2
