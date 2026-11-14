"""Tiferet Stocks Symbol Mappers"""

# *** imports

# ** core
from typing import Any, ClassVar, Dict

# ** infra
from tiferet.domain import ModelError
from tiferet.mappers import Aggregate, TransferObject

# ** app
from ..domain import Symbol, SymbolAlias

# *** mappers

# ** mapper: symbol_aggregate
class SymbolAggregate(Symbol, Aggregate):
    '''
    An aggregate representation of a symbol.
    '''

    # * attribute: _SETTABLE_ATTRIBUTES
    _SETTABLE_ATTRIBUTES: ClassVar[set] = {'id'}

    # * method: add_alias
    def add_alias(self, alias: SymbolAlias) -> None:
        '''
        Add a SymbolAlias to the restricted collection.

        :param alias: The alias to add.
        :type alias: SymbolAlias
        :return: None
        :rtype: None
        '''

        # Reject a second alias for a provider that is already on the symbol.
        if any(existing.provider == alias.provider for existing in self.aliases):
            ModelError.raise_error(
                'ALIAS_PROVIDER_EXISTS',
                message=f'A symbol accepts at most one alias per provider: {alias.provider}.',
                model=self,
            )

        # Reject an alias that does not belong to this symbol.
        if alias.canonical_id != self.id and alias.provider_ticker != self.id:
            ModelError.raise_error(
                'ALIAS_NOT_FOR_SYMBOL',
                message=f'Alias for {alias.canonical_id} does not belong to symbol {self.id}.',
                model=self,
            )

        # Copy and reassign so field validation runs before state changes.
        aliases = list(self.aliases)
        aliases.append(alias)
        self.aliases = aliases

    # * method: apply_alias
    def apply_alias(self, alias: SymbolAlias) -> None:
        '''
        Check the alias against the collection and set id to the canonical symbol id.

        Only this method may set id after construction.

        :param alias: The alias to apply.
        :type alias: SymbolAlias
        :return: None
        :rtype: None
        '''

        # The alias must already be in the restricted collection.
        if alias not in self.aliases:
            ModelError.raise_error(
                'ALIAS_NOT_IN_COLLECTION',
                message=f'Alias for {alias.canonical_id} is not in the symbol collection.',
                model=self,
            )

        # The alias must belong: at inbound apply the current id is the provider ticker.
        if alias.canonical_id != self.id and alias.provider_ticker != self.id:
            ModelError.raise_error(
                'ALIAS_NOT_FOR_SYMBOL',
                message=f'Alias for {alias.canonical_id} does not belong to symbol {self.id}.',
                model=self,
            )

        # Set id through the allow-list; no other method uses this entry.
        self.set_attribute('id', alias.canonical_id)

# ** mapper: symbol_yahoo_object
class SymbolYahooObject(Symbol, TransferObject):
    '''
    A Yahoo chart representation of a symbol, built from already-translated exchange ids and asset types.
    '''

    # * attribute: _ROLES
    _ROLES: ClassVar[Dict[str, Dict[str, Any]]] = {
        'to_model': {},
        'to_data': {},
    }

    # * method: map
    def map(self, **overrides) -> SymbolAggregate:
        '''
        Maps the Yahoo symbol data to a symbol aggregate.

        :param overrides: Additional keyword arguments.
        :type overrides: dict
        :return: A new symbol aggregate.
        :rtype: SymbolAggregate
        '''

        # Map to the symbol aggregate.
        return super().map(SymbolAggregate, **overrides)
