"""Tiferet Stocks Watchlist Configuration Repository"""

# *** imports

# ** core
from pathlib import Path
from typing import Any, Dict, List

# ** infra
from tiferet.repos.core import ConfigurationRepository

# ** app
from tiferet_stocks.interfaces import WatchlistService
from tiferet_stocks.mappers import WatchlistAggregate, WatchlistConfigObject

# *** repos

# ** repo: watchlist_config_repository
class WatchlistConfigRepository(WatchlistService, ConfigurationRepository):
    '''
    Keeps ordered watchlists in one human-readable YAML or JSON file.
    Reads never create storage; the first save creates a missing file.
    '''

    # * init
    def __init__(self, watchlist_config: str, encoding: str = 'utf-8') -> None:
        '''
        Select the watchlists file and its encoding.

        :param watchlist_config: The YAML or JSON configuration path.
        :type watchlist_config: str
        :param encoding: The file encoding.
        :type encoding: str
        '''

        # Delegate file format and serialization policy to core.
        ConfigurationRepository.__init__(self, config_file=watchlist_config, encoding=encoding)

    # * method: _read_document
    def _read_document(self) -> Dict[str, Any]:
        '''
        Read a complete document, treating only an absent file as empty.

        :return: The complete configuration document.
        :rtype: Dict[str, Any]
        '''

        # Resolve the extension first, including for a missing path.
        self._get_loader()

        # Use stat rather than exists, so permission errors cannot become empty data.
        try:
            Path(self.config_file).stat()
        except FileNotFoundError:
            return {}

        # Preserve core parse and access errors instead of replacing them with emptiness.
        return self._load()

    # * method: get
    def get(self, id: str) -> WatchlistAggregate | None:
        '''
        Read one watchlist by document key without modifying the file.

        :param id: The watchlist key.
        :type id: str
        :return: The mapped watchlist, or None when the key is absent.
        :rtype: WatchlistAggregate | None
        '''

        # Load the mapping without touching filesystem state.
        documents = self._read_document().get('watchlists', {})
        if id not in documents:
            return None

        # The document key wins over any accidental embedded id.
        return WatchlistConfigObject.model_validate({**documents[id], 'id': id}).map()

    # * method: list
    def list(self) -> List[WatchlistAggregate]:
        '''
        Read every watchlist while preserving symbol order and timestamps.

        :return: The mapped watchlists.
        :rtype: List[WatchlistAggregate]
        '''

        # Map keyed document bodies without modifying the stored document.
        documents = self._read_document().get('watchlists', {})
        return [
            WatchlistConfigObject.model_validate({**data, 'id': id}).map()
            for id, data in documents.items()
        ]

    # * method: save
    def save(self, watchlist: WatchlistAggregate) -> None:
        '''
        Save one watchlist, retaining every other document and root node.

        :param watchlist: The watchlist to create or replace.
        :type watchlist: WatchlistAggregate
        :return: None.
        :rtype: None
        '''

        # Serialize before touching the filesystem, then read the complete document.
        data = WatchlistConfigObject.from_model(watchlist).to_primitive(role=self.default_role)
        document = self._read_document()
        document.setdefault('watchlists', {})[watchlist.id] = data

        # Create storage only on save; core owns format-specific file writes.
        Path(self.config_file).parent.mkdir(parents=True, exist_ok=True)
        self._save(data=document)

    # * method: delete
    def delete(self, id: str) -> None:
        '''
        Remove one key while preserving all unrelated stored data.

        :param id: The watchlist key.
        :type id: str
        :return: None.
        :rtype: None
        '''

        # An absent key, including an absent file, requires no write.
        document = self._read_document()
        documents = document.get('watchlists', {})
        if id not in documents:
            return

        # Remove only the requested body and persist the complete document.
        documents.pop(id)
        self._save(data=document)
