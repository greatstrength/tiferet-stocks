"""Tiferet Stocks Assets Core

Service, event, provider and feature ids used to wire the package in
configuration.
"""

# *** constants (ids_services)

# ** constant: symbol_lookup_service_id
SYMBOL_LOOKUP_SERVICE_ID = 'symbol_lookup_service'

# *** constants (ids_events)

# ** constant: get_symbol_event_id
GET_SYMBOL_EVENT_ID = 'get_symbol_event'

# ** constant: resolve_symbols_event_id
RESOLVE_SYMBOLS_EVENT_ID = 'resolve_symbols_event'

# ** constant: list_exchanges_event_id
LIST_EXCHANGES_EVENT_ID = 'list_exchanges_event'

# *** constants (ids_providers)

# ** constant: yahoo_chart_provider_id
YAHOO_CHART_PROVIDER_ID = 'yahoo_chart'

# *** constants (ids_features)

# ** constant: symbols_get_feature_id
SYMBOLS_GET_FEATURE_ID = 'symbols.get'

# ** constant: symbols_resolve_feature_id
SYMBOLS_RESOLVE_FEATURE_ID = 'symbols.resolve'

# ** constant: exchanges_list_feature_id
EXCHANGES_LIST_FEATURE_ID = 'exchanges.list'
