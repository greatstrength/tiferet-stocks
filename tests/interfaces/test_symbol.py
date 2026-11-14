"""Tiferet Stocks Symbol Interface Tests"""

# *** imports

# ** core
from typing import List

# ** infra
import pytest

# ** app
from tiferet_stocks.domain import YAHOO_CHART, SymbolAlias
from tiferet_stocks.interfaces import SymbolAliasService, SymbolLookupService

# *** classes

# ** class: brk_alias_service
class BrkAliasService(SymbolAliasService):
    '''
    An alias service that returns the BRK.B Yahoo alias for yahoo_chart only.
    '''

    # * method: get_aliases
    def get_aliases(self, provider: str) -> List[SymbolAlias]:
        '''
        Return the BRK.B Yahoo alias row when the provider is yahoo_chart, otherwise no rows.

        :param provider: The provider id.
        :type provider: str
        :return: The alias rows for that provider.
        :rtype: List[SymbolAlias]
        '''

        # Return data only; an unknown provider has no rows, not a raise.
        if provider != YAHOO_CHART:
            return []
        return [SymbolAlias(provider=YAHOO_CHART, provider_ticker='BRK-B', canonical_id='BRK.B')]

# *** tests

# ** test: symbol_alias_service_is_not_lookup_service
def test_symbol_alias_service_is_not_lookup_service() -> None:
    '''
    Test that alias loading is a separate service, not a method on SymbolLookupService.
    '''

    assert not hasattr(SymbolLookupService, 'get_aliases')
    assert not issubclass(SymbolAliasService, SymbolLookupService)
    assert 'lookup' not in SymbolAliasService.__dict__

# ** test: symbol_alias_service_requires_get_aliases
def test_symbol_alias_service_requires_get_aliases() -> None:
    '''
    Test that SymbolAliasService cannot be instantiated without get_aliases.
    '''

    with pytest.raises(TypeError):
        SymbolAliasService()

# ** test: get_aliases_returns_rows
def test_get_aliases_returns_rows() -> None:
    '''
    Test that an implementation returns List[SymbolAlias], one per configured row.
    '''

    service = BrkAliasService()
    aliases = service.get_aliases(YAHOO_CHART)

    assert [alias.provider_ticker for alias in aliases] == ['BRK-B']
    assert aliases[0].canonical_id == 'BRK.B'
    assert aliases[0].provider == YAHOO_CHART
    assert service.get_aliases('unknown') == []
