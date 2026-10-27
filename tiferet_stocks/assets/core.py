"""Tiferet Stocks Assets Core

Service, event, provider and feature ids used to wire the package in
configuration.
"""

# *** constants (ids_services)

# ** constant: symbol_lookup_service_id
SYMBOL_LOOKUP_SERVICE_ID = 'symbol_lookup_service'

# ** constant: price_service_id
PRICE_SERVICE_ID = 'price_service'

# *** constants (ids_events)

# ** constant: get_symbol_event_id
GET_SYMBOL_EVENT_ID = 'get_symbol_event'

# ** constant: resolve_symbols_event_id
RESOLVE_SYMBOLS_EVENT_ID = 'resolve_symbols_event'

# ** constant: list_exchanges_event_id
LIST_EXCHANGES_EVENT_ID = 'list_exchanges_event'

# ** constant: get_quotes_event_id
GET_QUOTES_EVENT_ID = 'get_quotes_event'

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
