# TSTK1-RFP-005 CLI Command and Request Contract

Group 1 supplies the actual declarative catalog, command-id constants and request-binding parser factory. It does not yet install a console entrypoint or change response rendering; those are later conceptual commits. Existing programmatic feature signatures and results remain unchanged.

The parser delegates to released Tiferet's public parse_cli_args_handler. Its commands are the stocks commands seeded on the bootstrap cache under the ('stocks', 'cli', 'commands') prefix from `tiferet_stocks.assets.cli`, followed by any commands the app session's configured CLI service lists. No custom argparse implementation, invented dest field or private context assignment is used. Public parsing returns the same feature id and core headers, with a copied data dictionary adapting the names below.

| Command | Feature id | Parsed feature data |
|---|---|---|
| quotes get SYMBOLS+ | quotes.get | symbols list |
| quotes history SYMBOL --start DATE --end DATE | quotes.history | symbol, start, end; both date flags required |
| symbols get SYMBOL | symbols.get | public symbol becomes id |
| symbols resolve SYMBOLS+ [--expected-exchanges SYM=EXCHANGE ...] | symbols.resolve | public symbols becomes ids; expected_exchanges becomes exchanges |
| exchanges list | exchanges.list | no command-specific data |
| watchlists list | watchlists.list | no command-specific data |
| watchlists get ID | watchlists.get | id |
| watchlists create ID --name NAME [--description TEXT] [--symbol-ids SYMBOLS+] | watchlists.create | id, name, optional description and symbol_ids |
| watchlists update ID [--name NAME] [--description TEXT] | watchlists.update | id and optional supplied labels |
| watchlists delete ID | watchlists.delete | id |
| watchlists add ID SYMBOL [--index INDEX] [--create] | watchlists.add | id, symbol_id, integer index default -1, create bool default false |
| watchlists remove ID SYMBOL | watchlists.remove | id, symbol_id |
| watchlists move ID SYMBOL [--to-index INDEX] | watchlists.move | id, symbol_id, integer to_index default -1 |

Core list arguments use nargs '+' for one or more values. The optional exchange map uses core's dict interpretation of key=value tokens; omission preserves None for the existing event's optional exchanges argument. Negative -1/-2 values parse as integers; whether a value is a valid ordering request is decided by the existing watchlist feature, not duplicated in the parser. The command constants equal the already-existing feature ids.

## Validation

`tests/test_cli_catalog.py` checks the exact thirteen-command set, all argument signatures, name remapping, headers, unchanged parser inputs, scalar defaults, negative values and core parse failures. Integration cases dispatch all thirteen parsed commands through the existing App feature pipeline. Prices and daily bars use StaticPriceRepository; symbol lookups use recorded responses behind a patched urlopen and never call the network. Rejected -2 changes preserve stored bytes and retain the catalogued watchlist error code. `tests/test_cli_seed.py` checks the cache seed, asset and reference-config parity, the list-commands handler with and without configuration, the config-first session with the cached session as fallback, a config session service override, the Yahoo default aliases and a configured alias replacing one, and no-config runs in process and from the installed wheel.

## Approved later groups

Group 2 adds per-symbol presentation preserving every warning/failure without changing the library's programmatic return values. Group 3 supplies public CLI factory adaptation, CWD config.yml or explicit --config, blueprint/package registration and the console entrypoint. Group 4 adds installed-command, output/error/exit-code and full acceptance evidence. No version/dependency change or expansion to other features is part of this lane.


## Symbol presentation

Quotes and lookup answers render as native core tables with one row per encountered symbol id, including ids represented only by warnings or failures. A quote answer is a QuoteList; rows walk its quotes list by symbol_id, so a ticker the provider omitted appears as a failed row with a not_found failure. Quote scalars remain scalars; quote_symbol_id and resolved_symbol_id retain provider identity independently of the requested symbol_id. Symbol metadata uses symbol_ prefixes, and quote fetched_at is retained when present. An applied alias appears as one scalar symbol_alias_PROVIDER column holding the provider ticker (for example symbol_alias_yahoo_chart = BRK-B); the aliases list itself is not rendered as a nested cell. Numbered failure_N_* and warning_N_* columns preserve every field of every record, including repeated reasons, details and attempts; counts make omissions visible. Other responses keep core's native formatting. Presentation never replaces or modifies the library result.


## Running the installed CLI

Install the package and run `tiferet-stocks exchanges list`; no configuration file is required. The stocks `build_cache` mirrors core's admin build_cache: add_default_catalog for the stocks commands, services, constants and sessions, plus add_default_features and add_default_errors, stacked over the standard `app.build_cache`, seeding the stocks commands, features, services, the stocks_cli and stocks_client sessions, the error catalog and the Yahoo default symbol aliases from packaged Python assets. No YAML is packaged. A config.yml in the current working directory, or one named with `--config`, is optional. Configured items take precedence and the cache is the fallback. The stocks get_app_session calls core's get_app_session first without the cache, so a stocks_cli session the config declares is used and its `services` entries replace the cached services of the same id through core's build_app_service_container; only on APP_SESSION_NOT_FOUND, or FILE_NOT_FOUND for the optional default config.yml, does it call core's get_app_session with the cache. The list-commands handler returns the cached stocks commands followed by whatever the session's CLI service lists, with no merge or override rule; a missing default config.yml lists nothing extra. An explicit `--config` path that does not exist stays a FILE_NOT_FOUND fault. Core config readers all use the selected document; relative provider/watchlist paths retain CWD-relative core semantics.

`watchlists add ID SYMBOL` fails with the catalogued WATCHLIST_NOT_FOUND for a missing watchlist. With `--create`, a missing watchlist is created, named by its id, holding the one symbol; for an existing watchlist the flag changes nothing.

The stocks blueprint composes core's public get_app_session, build_app_service_container, build_service_resolver and compose_session_context factories. As core's tester CLI does, it also registers the app container with no flag so feature steps resolve the cached services without reading a DI configuration. The Yahoo default aliases follow core's multi-group asset catalog layout in `tiferet_stocks/assets/symbol.py`: the provider ticker id under `# *** constants (ids_yahoo)`, the alias data under `# *** constants (data_yahoo)` built by `create_default_symbol_alias_data(canonical_id)` in `tiferet_stocks/assets/core.py`, and `YAHOO_DEFAULT_SYMBOL_ALIASES`, keyed by provider ticker, under `# *** constants (groups)`; the data carries neither provider ticker nor provider. build_cache seeds it as the app constant `yahoo_default_symbol_aliases` under core's app constant prefix, the way core's admin build_cache seeds ADMIN_DEFAULT_CONSTANTS, and the app container injects it by name into the symbol alias service. The service hydrates each default with its provider ticker and the yahoo_chart provider, then lets symbols-file rows replace any default with the same provider ticker. It injects the request binder and stock response context, without changing core, shared domain features or private context slots. The real CliSessionContext prints responses, exits 1 for configured domain errors and uses argparse's exit 2 for command syntax errors. Missing/malformed configuration remains an infrastructure fault, not a new catalogued stocks error. `symbols get` for a ticker the provider does not know exits 1 with the catalogued SYMBOL_NOT_FOUND message; `symbols resolve` still reports such a ticker as a failure row.
