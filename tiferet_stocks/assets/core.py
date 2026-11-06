"""Tiferet Stocks Assets Core

Service, event, provider and feature ids used to wire the package in
configuration.
"""

# *** constants (ids_services)

# ** constant: symbol_lookup_service_id
SYMBOL_LOOKUP_SERVICE_ID = 'symbol_lookup_service'

# ** constant: price_service_id
PRICE_SERVICE_ID = 'price_service'

# ** constant: watchlist_service_id
WATCHLIST_SERVICE_ID = 'watchlist_service'

# *** constants (ids_events)

# ** constant: get_symbol_event_id
GET_SYMBOL_EVENT_ID = 'get_symbol_event'

# ** constant: resolve_symbols_event_id
RESOLVE_SYMBOLS_EVENT_ID = 'resolve_symbols_event'

# ** constant: list_exchanges_event_id
LIST_EXCHANGES_EVENT_ID = 'list_exchanges_event'

# ** constant: get_quotes_event_id
GET_QUOTES_EVENT_ID = 'get_quotes_event'

# ** constant: get_history_event_id
GET_HISTORY_EVENT_ID = 'get_history_event'

# *** constants (ids_providers)

# ** constant: yahoo_chart_provider_id
YAHOO_CHART_PROVIDER_ID = 'yahoo_chart'

# ** constant: static_provider_id
STATIC_PROVIDER_ID = 'static'

# *** constants (ids_features)

# ** constant: symbols_get_feature_id
SYMBOLS_GET_FEATURE_ID = 'symbols.get'

# ** constant: symbols_resolve_feature_id
SYMBOLS_RESOLVE_FEATURE_ID = 'symbols.resolve'

# ** constant: exchanges_list_feature_id
EXCHANGES_LIST_FEATURE_ID = 'exchanges.list'

# ** constant: quotes_get_feature_id
QUOTES_GET_FEATURE_ID = 'quotes.get'

# ** constant: quotes_history_feature_id
QUOTES_HISTORY_FEATURE_ID = 'quotes.history'

# *** constants (ids_watchlist_events)

# ** constant: get_watchlist_event_id
GET_WATCHLIST_EVENT_ID = 'get_watchlist_event'

# ** constant: list_watchlists_event_id
LIST_WATCHLISTS_EVENT_ID = 'list_watchlists_event'

# ** constant: create_watchlist_event_id
CREATE_WATCHLIST_EVENT_ID = 'create_watchlist_event'

# ** constant: update_watchlist_event_id
UPDATE_WATCHLIST_EVENT_ID = 'update_watchlist_event'

# ** constant: delete_watchlist_event_id
DELETE_WATCHLIST_EVENT_ID = 'delete_watchlist_event'

# ** constant: add_watchlist_symbol_event_id
ADD_WATCHLIST_SYMBOL_EVENT_ID = 'add_watchlist_symbol_event'

# ** constant: remove_watchlist_symbol_event_id
REMOVE_WATCHLIST_SYMBOL_EVENT_ID = 'remove_watchlist_symbol_event'

# ** constant: move_watchlist_symbol_event_id
MOVE_WATCHLIST_SYMBOL_EVENT_ID = 'move_watchlist_symbol_event'

# *** constants (ids_watchlist_features)

# ** constant: watchlists_get_feature_id
WATCHLISTS_GET_FEATURE_ID = 'watchlists.get'

# ** constant: watchlists_list_feature_id
WATCHLISTS_LIST_FEATURE_ID = 'watchlists.list'

# ** constant: watchlists_create_feature_id
WATCHLISTS_CREATE_FEATURE_ID = 'watchlists.create'

# ** constant: watchlists_update_feature_id
WATCHLISTS_UPDATE_FEATURE_ID = 'watchlists.update'

# ** constant: watchlists_delete_feature_id
WATCHLISTS_DELETE_FEATURE_ID = 'watchlists.delete'

# ** constant: watchlists_add_feature_id
WATCHLISTS_ADD_FEATURE_ID = 'watchlists.add'

# ** constant: watchlists_remove_feature_id
WATCHLISTS_REMOVE_FEATURE_ID = 'watchlists.remove'

# ** constant: watchlists_move_feature_id
WATCHLISTS_MOVE_FEATURE_ID = 'watchlists.move'
