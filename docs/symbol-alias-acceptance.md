# TSTK1-RFP-009 Symbol Alias Acceptance Packet

Scope: issue [#15](https://github.com/greatstrength/tiferet-stocks/issues/15), built on `v1.x-proto-build` from `v1.0.0b1`. No version bump, dependency change, alias-write event or CLI flag is included. These are local implementation checks for independent review, not QA approval or checked issue boxes.

## Decisions applied

`SymbolAlias` holds a provider id from `PROVIDERS` (initially `yahoo_chart`), a provider ticker and a canonical id. `SymbolAggregate.add_alias` enforces at most one alias per provider and only for that symbol; `apply_alias` is the only method that sets `id`. Rejections are uncatalogued model errors (`ALIAS_PROVIDER_EXISTS`, `ALIAS_NOT_FOR_SYMBOL`, `ALIAS_NOT_IN_COLLECTION`). The outbound and inbound helpers are pure domain functions with exact ticker match. `SymbolAliasRepository` and `YahooChartSymbolRepository` live in `tiferet_stocks/repos/symbol.py` and are wired independently; both Yahoo repositories share `YahooChartClient` in `repos/yahoo.py`. `GetSymbol` raises `SYMBOL_NOT_FOUND` only when the provider reports its one ticker `not_found`; timeouts, HTTP errors, bad payloads and mismatches stay data. Quote symbols are canonicalized with `add_alias` and `apply_alias`; quotes, bars, warnings and failures are re-keyed by `symbol_id`.

## Seed document

```yaml
aliases:
  - provider: yahoo_chart
    provider_ticker: BRK-B
    canonical_id: BRK.B
```

## Acceptance criteria

| AC | Requirement | Executable coverage |
|---|---|---|
| 1 | `SymbolAlias` with a restricted `PROVIDERS` list including `yahoo_chart`. | `tests/domain/test_symbol.py` (providers, alias construction, rejected providers) |
| 2 | Restricted aliases collection; `apply_alias` sets `id`, only it sets `id`. | `tests/domain/test_symbol.py`, `tests/mappers/test_symbol.py` (`add_alias`, `apply_alias`, `only_apply_alias_sets_id`) |
| 3 | Symbol subdomain only; no replacement inside `YahooChartPriceRepository`. | `tests/repos/test_symbol.py::test_symbol_repo_shares_chart_client`, `test_lookup_takes_the_id_it_is_given` |
| 4 | `SymbolAliasService.get_aliases(provider)` keyed by provider ticker, not on `SymbolLookupService`. | `tests/interfaces/test_symbol.py` |
| 5 | YAML alias repo (missing file empty, never created, parse and access errors kept) and HTTP lookup repo that does not raise; seed includes BRK.B. | `tests/repos/test_symbol.py` (alias repo cases, 404 as failure record, recorded lookups) |
| 6 | Lookup events: aliases first, outbound, HTTP, add and apply before the mismatch check. | `tests/events/test_symbol.py` (BRK.B get and resolve, re-keyed failures, unexpected ticker mismatch) |
| 7 | `GetQuotes` and `GetHistory` alias outbound and answer under the canonical id. | `tests/events/test_quote.py`, `tests/events/test_history.py` (BRK.B cases and AAPL control) |
| 8 | Repos and helpers do not raise; `GetSymbol` raises `SYMBOL_NOT_FOUND`; `ResolveSymbols` reports misses as data; existing raises unchanged. | `tests/events/test_symbol.py::test_get_symbol_not_found`, `test_get_symbol_other_failures_are_data`; `tests/test_symbol_alias_acceptance.py::test_existing_raises_unchanged`; `tests/test_config.py::test_symbol_not_found_config_matches_assets` |
| 9 | Distillation amended for the `SymbolAlias` exception. | `docs/core-domain-distillation.md` sections 2, 3, 4, 5 and 8 |
| 10 | BRK.B acceptance through the reference configuration with the network blocked; existing acceptance green. | `tests/test_symbol_alias_acceptance.py` (recorded `brk-b.json`, `brk-b_history.json`, AAPL control, unknown ticker, missing seed, independent wiring); opt-in `tests/repos/test_yahoo_live.py::test_live_brk_b_alias` |

## Boundaries

The seed file is not packaged in the wheel. The programmatic App with the reference configuration and no local `data/symbols.yml` requests `BRK.B` as given and still fails with HTTP 404 (`test_missing_seed_passes_through`). The installed CLI does not: since TSTK1-RFP-007 it seeds the Yahoo default aliases (`YAHOO_DEFAULT_SYMBOL_ALIASES`) into its bootstrap cache and quotes `BRK.B` with no symbols file (`tests/test_cli_seed.py`). A request for the provider ticker itself (`BRK-B`) is answered under the canonical `BRK.B`, because inbound re-keying follows the alias map. `symbols get` for an unknown ticker now exits 1 through the CLI with `SYMBOL_NOT_FOUND`, replacing its 1.0.0b1 failure row. Events now inject `symbol_alias_service`, so a consumer configuration must declare that service before the symbol, quote and history events.
