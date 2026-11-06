"""Tiferet Stocks Watchlist Repository Integration Tests"""

# *** imports

# ** core
import json
from pathlib import Path

# ** infra
import pytest
import yaml
from pydantic import ValidationError
from tiferet import use_tester
from tiferet.interfaces import ServiceError

# ** app
from tiferet_stocks.interfaces import WatchlistService
from tiferet_stocks.mappers import WatchlistAggregate
from tiferet_stocks.repos.watchlist import WatchlistConfigRepository

# *** tests

# ** test: missing_file_reads_do_not_create_storage
@pytest.mark.parametrize('extension', ['yml', 'yaml', 'json'])
def test_missing_file_reads_do_not_create_storage(tmp_path: Path, extension: str) -> None:
    '''
    Missing files and parents remain absent during reads and idempotent delete.

    :param tmp_path: The temporary directory.
    :type tmp_path: Path
    :param extension: The supported file format.
    :type extension: str
    '''

    path = tmp_path / 'missing' / f'watchlists.{extension}'
    repo = WatchlistConfigRepository(watchlist_config=str(path))

    assert isinstance(repo, WatchlistService)
    assert repo.get('missing') is None
    assert repo.list() == []
    repo.delete('missing')
    assert not path.exists()
    assert not path.parent.exists()

# ** test: first_save_and_round_trip
@pytest.mark.parametrize('extension', ['yml', 'yaml', 'json'])
def test_first_save_and_round_trip(tmp_path: Path, extension: str) -> None:
    '''
    First save creates storage and preserves ordered ids, offsets and Unicode.

    :param tmp_path: The temporary directory.
    :type tmp_path: Path
    :param extension: The supported file format.
    :type extension: str
    '''

    path = tmp_path / 'new' / f'watchlists.{extension}'
    repo = WatchlistConfigRepository(watchlist_config=str(path))
    watchlist = WatchlistAggregate(id='etfs', name='Broad ETFs', description='Caf\u00e9', symbol_ids=['SPY', 'QQQ', 'XLK'])
    watchlist.upsert(at='2026-10-26T18:00:00-07:00')
    repo.save(watchlist)
    original_bytes = path.read_bytes()
    original_mtime = path.stat().st_mtime_ns

    assert repo.get('etfs') == watchlist
    assert repo.list() == [watchlist]
    assert repo.get('absent') is None
    assert path.read_bytes() == original_bytes
    assert path.stat().st_mtime_ns == original_mtime

    data = yaml.safe_load(path.read_text())
    assert 'id' not in data['watchlists']['etfs']
    assert data['watchlists']['etfs']['symbol_ids'] == ['SPY', 'QQQ', 'XLK']
    assert data['watchlists']['etfs']['description'] == 'Caf\u00e9'

# ** test: save_replace_delete_preserves_other_data
@pytest.mark.parametrize('extension', ['yml', 'json'])
def test_save_replace_delete_preserves_other_data(tmp_path: Path, extension: str) -> None:
    '''
    Replacing and deleting one watchlist retains other bodies and root nodes.

    :param tmp_path: The temporary directory.
    :type tmp_path: Path
    :param extension: The supported file format.
    :type extension: str
    '''

    path = tmp_path / f'watchlists.{extension}'
    document = {
        'metadata': {'owner': 'example'},
        'watchlists': {
            'one': {'name': 'One', 'symbol_ids': ['SPY']},
            'two': {'name': 'Two', 'symbol_ids': ['QQQ', 'XLK']},
        },
    }
    content = json.dumps(document) if extension == 'json' else yaml.safe_dump(document)
    path.write_text(content)
    repo = WatchlistConfigRepository(watchlist_config=str(path))
    replacement = WatchlistAggregate(id='one', name='Replaced', symbol_ids=[])
    repo.save(replacement)

    data = yaml.safe_load(path.read_text())
    assert data['metadata'] == document['metadata']
    assert data['watchlists']['two'] == document['watchlists']['two']
    assert repo.get('one') == replacement
    assert data['watchlists']['one'] == {'name': 'Replaced', 'symbol_ids': []}

    repo.delete('one')

    assert repo.get('one') is None
    assert repo.get('two').symbol_ids == ['QQQ', 'XLK']
    assert yaml.safe_load(path.read_text())['metadata'] == document['metadata']

    original_bytes = path.read_bytes()
    repo.delete('absent')
    assert path.read_bytes() == original_bytes

# ** test: starter_and_reference_configuration
def test_starter_and_reference_configuration() -> None:
    '''
    Keep the starter empty and the reference service format-neutral.
    '''

    root = Path(__file__).resolve().parents[2]
    config = yaml.safe_load((root / 'config.yml').read_text())
    service = config['services']['watchlist_service']

    assert service['module_path'] == 'tiferet_stocks.repos.watchlist'
    assert service['class_name'] == 'WatchlistConfigRepository'
    assert service['params']['watchlist_config'] == 'data/watchlists.yml'
    assert yaml.safe_load((root / 'data/watchlists.yml').read_text()) == {'watchlists': {}}

# ** test: unsupported_extension_is_not_empty
@pytest.mark.parametrize('operation', ['get', 'list', 'save', 'delete'])
def test_unsupported_extension_is_not_empty(tmp_path: Path, operation: str) -> None:
    '''
    Even a missing path with an unsupported extension remains a core error.

    :param tmp_path: The temporary directory.
    :type tmp_path: Path
    :param operation: The repository operation to exercise.
    :type operation: str
    '''

    path = tmp_path / 'missing' / 'watchlists.txt'
    repo = WatchlistConfigRepository(watchlist_config=str(path))
    args = {'get': ('one',), 'list': (), 'save': (WatchlistAggregate(id='one', name='One'),), 'delete': ('one',)}

    with pytest.raises(ServiceError) as raised:
        getattr(repo, operation)(*args[operation])

    assert raised.value.error_code == 'UNSUPPORTED_CONFIG_FILE_TYPE'
    assert not path.parent.exists()

# ** test: malformed_documents_are_not_overwritten
@pytest.mark.parametrize('extension, content', [('yml', 'watchlists: ['), ('json', '{invalid')])
@pytest.mark.parametrize('operation', ['get', 'list', 'save', 'delete'])
def test_malformed_documents_are_not_overwritten(tmp_path: Path,
                                                extension: str,
                                                content: str,
                                                operation: str) -> None:
    '''
    Parse failures propagate on reads and writes without erasing stored bytes.

    :param tmp_path: The temporary directory.
    :type tmp_path: Path
    :param extension: The file format.
    :type extension: str
    :param content: The malformed file content.
    :type content: str
    :param operation: The repository operation to exercise.
    :type operation: str
    '''

    path = tmp_path / f'watchlists.{extension}'
    path.write_text(content)
    repo = WatchlistConfigRepository(watchlist_config=str(path))
    args = {'get': ('one',), 'list': (), 'save': (WatchlistAggregate(id='one', name='One'),), 'delete': ('one',)}

    with pytest.raises(ServiceError):
        getattr(repo, operation)(*args[operation])

    assert path.read_text() == content

# ** test: invalid_watchlist_is_not_an_absent_key
def test_invalid_watchlist_is_not_an_absent_key(tmp_path: Path) -> None:
    '''
    An empty invalid body is validated rather than mistaken for a missing key.

    :param tmp_path: The temporary directory.
    :type tmp_path: Path
    '''

    path = tmp_path / 'watchlists.yml'
    path.write_text('watchlists:\n  broken: {}\n')
    repo = WatchlistConfigRepository(watchlist_config=str(path))

    with pytest.raises(ValidationError):
        repo.get('broken')
    with pytest.raises(ValidationError):
        repo.list()

# ** test: access_failure_is_not_empty
def test_access_failure_is_not_empty(tmp_path: Path, monkeypatch) -> None:
    '''
    A permission failure in the absence check propagates instead of returning emptiness.

    :param tmp_path: The temporary directory.
    :type tmp_path: Path
    :param monkeypatch: The scoped patch fixture.
    :type monkeypatch: pytest.MonkeyPatch
    '''

    path = tmp_path / 'watchlists.yml'
    repo = WatchlistConfigRepository(watchlist_config=str(path))

    with monkeypatch.context() as patch:
        patch.setattr(Path, 'stat', lambda self: (_ for _ in ()).throw(PermissionError('denied')))
        with pytest.raises(PermissionError, match='denied'):
            repo.list()

    assert not path.exists()

# ** test: document_key_owns_identity
def test_document_key_owns_identity(tmp_path: Path) -> None:
    '''
    An accidental id in a body cannot replace its document key.

    :param tmp_path: The temporary directory.
    :type tmp_path: Path
    '''

    path = tmp_path / 'watchlists.yml'
    path.write_text('watchlists:\n  correct:\n    id: wrong\n    name: Example\n    symbol_ids: []\n')
    repo = WatchlistConfigRepository(watchlist_config=str(path))

    assert repo.get('correct').id == 'correct'
    assert repo.list()[0].id == 'correct'

# *** testers

# ** tester: test_watchlist_config_repository
@use_tester(
    type='repo',
    target_cls=WatchlistConfigRepository,
    config_parameter='watchlist_config',
    exists_cases=[],
    get_cases=[
        ('etfs', {
            'id': 'etfs',
            'name': 'Broad ETFs',
            'description': 'Ordered holdings',
            'created_at': '2026-11-06T14:00:00-07:00',
            'updated_at': '2026-11-06T14:30:00-07:00',
            'symbol_ids': ['SPY', 'QQQ', 'XLK'],
        }),
        ('absent', None),
    ],
    list_ids=['etfs'],
    delete_ids=['etfs'],
    aggregate_module_path='tiferet_stocks.mappers.watchlist',
    aggregate_class_name='WatchlistAggregate',
    aggregate_sample_data={
        'id': 'etfs',
        'name': 'Broad ETFs',
        'description': 'Ordered holdings',
        'created_at': '2026-11-06T14:00:00-07:00',
        'updated_at': '2026-11-06T14:30:00-07:00',
        'symbol_ids': ['SPY', 'QQQ', 'XLK'],
    },
    equality_fields=['id', 'name', 'description', 'created_at', 'updated_at', 'symbol_ids'],
)
class TestWatchlistConfigRepository:
    '''
    Bind meaningful CRUD assertions to both formats without an exists contract.
    '''

    # * test: persisted_crud
    @pytest.mark.parametrize('extension', ['yml', 'json'])
    def test_persisted_crud(self, test_ctx, session, tmp_path: Path, extension: str):
        '''
        Exercise released repository assertions against independent on-disk files.

        :param test_ctx: The bound repository assertion context.
        :type test_ctx: RepoTesterContext
        :param session: The released test session.
        :type session: TestSessionContext
        :param tmp_path: The isolated storage directory.
        :type tmp_path: Path
        :param extension: The supported persistence format.
        :type extension: str
        :return: None.
        :rtype: None
        '''

        # Construct through the explicit configuration parameter without creating storage.
        config_file = str(tmp_path / f'watchlists.{extension}')
        test_ctx.assert_new(config_file=config_file)
        repo = test_ctx.make_target(config_file=config_file)
        assert not Path(config_file).exists()

        # Nonempty declared cases exercise save, present/missing get and list.
        test_ctx.assert_save(repo)
        test_ctx.assert_get(repo)
        test_ctx.assert_list(repo)

        # Delete each declared identifier twice; no exists method is invoked.
        test_ctx.assert_delete(repo)
        assert repo.list() == []
