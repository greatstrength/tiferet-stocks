"""Tiferet Stocks Symbol Repositories"""

# *** imports

# ** core
from pathlib import Path
from typing import Any, Dict, List

# ** infra
from tiferet.repos.core import ConfigurationRepository

# ** app
from .. import assets as a
from ..interfaces import SymbolAliasService, SymbolLookupService
from ..mappers import SymbolAlias, SymbolLookup
from .yahoo import YahooChartClient

# *** repos

# ** repo: symbol_alias_repository
class SymbolAliasRepository(SymbolAliasService, ConfigurationRepository):
    '''
    Reads provider ticker aliases from the aliases list in one YAML or JSON symbols file.
    Reads never create storage; a missing file, a missing aliases list, or a provider with no rows is an empty map.
    '''

    # * init
    def __init__(self, symbol_config: str = a.symbol.DEFAULT_SYMBOL_CONFIG_FILE, encoding: str = 'utf-8') -> None:
        '''
        Select the symbols file and its encoding.

        :param symbol_config: The YAML or JSON configuration path; defaults to the packaged default path, data/symbols.yml, which a client application may override.
        :type symbol_config: str
        :param encoding: The file encoding.
        :type encoding: str
        '''

        # Delegate file format and serialization policy to core.
        ConfigurationRepository.__init__(self, config_file=symbol_config, encoding=encoding)

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
        return self._load() or {}

    # * method: get_aliases
    def get_aliases(self, provider: str) -> List[SymbolAlias]:
        '''
        Return every configured alias row for one provider, in file order, with no validation or collapsing.

        :param provider: The provider id, such as yahoo_chart.
        :type provider: str
        :return: The aliases for that provider, one per row, in file order.
        :rtype: List[SymbolAlias]
        '''

        # Read the aliases list without touching filesystem state.
        rows = self._read_document().get('aliases') or []

        # Keep every row for the requested provider; the alias events check and key them.
        return [SymbolAlias.model_validate(row) for row in rows if row.get('provider') == provider]

# ** repo: yahoo_chart_symbol_repository
class YahooChartSymbolRepository(YahooChartClient, SymbolLookupService):
    '''
    Symbol lookup backed by the Yahoo chart endpoint. It is alias-free: it takes whatever id it is given and does not raise.
    '''

    # * method: lookup
    def lookup(self, ids: List[str]) -> SymbolLookup:
        '''
        Look up each requested symbol id with the Yahoo chart endpoint.

        :param ids: The requested symbol ids (tickers).
        :type ids: List[str]
        :return: The symbols by requested id, with warnings and failures; a 404 is a failure record.
        :rtype: SymbolLookup
        '''

        # Fetch and translate each distinct id in request order.
        symbols, warnings, failures = {}, [], []
        for symbol_id in dict.fromkeys(ids):
            result, failure, _ = self.fetch_chart(symbol_id)
            if failure:
                failures.append(failure)
                continue
            symbol, symbol_warnings = self.translate_symbol(symbol_id, result['meta'])
            symbols[symbol_id] = symbol
            warnings.extend(symbol_warnings)

        # Return the lookup answer.
        return SymbolLookup(symbols=symbols, warnings=warnings, failures=failures)
