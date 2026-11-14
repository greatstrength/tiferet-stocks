"""Tiferet Stocks Symbol Repositories"""

# *** imports

# ** core
from pathlib import Path
from typing import Any, Dict, List

# ** infra
from tiferet.repos.core import ConfigurationRepository

# ** app
from ..interfaces import SymbolAliasService, SymbolLookupService
from ..mappers import YAHOO_CHART, SymbolAlias, SymbolLookup
from .yahoo import YahooChartClient

# *** repos

# ** repo: symbol_alias_repository
class SymbolAliasRepository(SymbolAliasService, ConfigurationRepository):
    '''
    Reads provider ticker aliases from the aliases list in one YAML or JSON symbols file, falling back to the injected Yahoo default aliases.
    Reads never create storage; a missing file, a missing aliases list, or a provider with no rows adds nothing.
    '''

    # * attribute: yahoo_default_symbol_aliases
    yahoo_default_symbol_aliases: Dict[str, Dict[str, Any]]

    # * init
    def __init__(self,
            symbol_config: str,
            encoding: str = 'utf-8',
            yahoo_default_symbol_aliases: Dict[str, Dict[str, Any]] = None) -> None:
        '''
        Select the symbols file, its encoding and the Yahoo default aliases.

        :param symbol_config: The YAML or JSON configuration path.
        :type symbol_config: str
        :param encoding: The file encoding.
        :type encoding: str
        :param yahoo_default_symbol_aliases: The Yahoo default alias data keyed by provider ticker, injected by the app container from the cached app constant of the same name; None adds none.
        :type yahoo_default_symbol_aliases: Dict[str, Dict[str, Any]] | None
        '''

        # Delegate file format and serialization policy to core.
        ConfigurationRepository.__init__(self, config_file=symbol_config, encoding=encoding)

        # Keep the Yahoo default aliases; their data carries neither provider ticker nor provider, which hydration supplies.
        self.yahoo_default_symbol_aliases = dict(yahoo_default_symbol_aliases or {})

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
    def get_aliases(self, provider: str) -> Dict[str, SymbolAlias]:
        '''
        Return the aliases for one provider, keyed by provider ticker.

        :param provider: The provider id, such as yahoo_chart.
        :type provider: str
        :return: The aliases for that provider, keyed by provider ticker.
        :rtype: Dict[str, SymbolAlias]
        '''

        # Start from the Yahoo defaults for the Yahoo provider, hydrating the provider ticker and provider.
        aliases = {}
        if provider == YAHOO_CHART:
            for provider_ticker, data in self.yahoo_default_symbol_aliases.items():
                aliases[provider_ticker] = SymbolAlias.model_validate({**data, 'provider_ticker': provider_ticker, 'provider': YAHOO_CHART})

        # Configured aliases from the symbols file take precedence; the defaults are only the fallback.
        for row in self._read_document().get('aliases') or []:
            if row.get('provider') == provider:
                alias = SymbolAlias.model_validate(row)
                aliases[alias.provider_ticker] = alias

        # Return the aliases keyed by provider ticker.
        return aliases

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
