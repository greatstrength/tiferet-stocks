# RFP-005 CLI acceptance

Scope: issue #6's thirteen configured commands, unchanged feature ids and domain behavior, released Tiferet 2.2.2b1. The Chief resolved installed discovery to CWD config.yml or --config, selected per-symbol output retaining all warnings/failures, and approved composing the existing public lower-level CLI factories because the released one-call builder hardwires its parser/request context. These are local implementation checks for Saito/QA, not QA approval or checked issue boxes.

## Twelve criteria

The numbering follows https://github.com/greatstrength/tiferet-stocks/issues/6 in order. Parameterized tests exercise the actual released parser and features; installed acceptance crosses the real console script, container, events and renderer.

| AC | Requirement | Executable coverage |
|---|---|---|
| 1 | Each of the thirteen commands in proposal item 1 is declared under cli in the reference config and dispatches to the feature with the same id. | `tests/test_cli_catalog.py::test_catalog_has_exactly_thirteen_feature_ids`, `test_all_command_argument_contracts`, `test_all_commands_dispatch_existing_features`; `tests/test_cli_acceptance.py::test_all_thirteen_installed_commands` |
| 2 | quotes history with a valid range that has no trading days prints an empty result, and a provider failure exits non-zero with the catalogued HISTORY_UNAVAILABLE message. | `tests/test_cli_acceptance.py::test_history_oldest_first_and_empty_trading_range`, `test_configured_errors_exit_one_and_never_write` |
| 3 | quotes get SPY QQQ, run against a static provider config, prints one row per symbol and shows any failure by symbol and reason. | `tests/test_cli_acceptance.py::test_quotes_have_one_row_per_symbol_and_all_failure_fields`; presentation unit tests retain every repeated warning/failure field |
| 4 | quotes history SPY --start <date> --end <date> prints bars oldest first. | `tests/test_cli_acceptance.py::test_history_oldest_first_and_empty_trading_range` |
| 5 | symbols get and symbols resolve show warnings (including unmapped_exchange) and failures, not only successes. | `tests/test_cli_acceptance.py::test_symbol_reports_preserve_messages`; `tests/test_cli_presentation.py` |
| 6 | exchanges list prints exactly the ids in EXCHANGES. | `tests/test_cli_acceptance.py::test_exchanges_print_exact_domain_ids` |
| 7 | watchlists add with no --index appends; --index -1 appends; --index -2 exits with the catalogued WATCHLIST_INDEX_OUT_OF_RANGE message, not a traceback. | `tests/test_cli_acceptance.py::test_cli_indexes_and_rejected_write_invariance` (add: default/-1/0/99/-2) |
| 8 | watchlists move handles --to-index -1 and --to-index -2 the same way through the CLI. | `tests/test_cli_acceptance.py::test_cli_indexes_and_rejected_write_invariance` (move: default/-1/0/99/-2) |
| 9 | A catalogued error exits non-zero with its configured message. | `tests/test_cli_acceptance.py::test_configured_errors_exit_one_and_never_write`, `test_cli_indexes_and_rejected_write_invariance`; all catalog messages replaced with distinctive configured prefixes and core exit 1 required; parser errors separately require exit 2 |
| 10 | Reporting commands leave the watchlists file byte-identical. | `tests/test_cli_acceptance.py::test_all_reporting_commands_leave_files_byte_identical`, `test_cli_missing_file_reads_then_first_save`; every reporting command snapshots storage, config and history |
| 11 | The console script entry point in pyproject.toml runs the CLI after pip install . | `tests/test_cli_bootstrap.py::test_installed_wheel_uses_site_packages_and_released_beta`, `test_installed_console_outside_checkout`; wheel built from the project with offline pip wheel and installed noneditable with offline pip install, console invoked outside checkout |
| 12 | No CLI test touches the network. | Acceptance subprocesses load `tests/cli_support/sitecustomize.py`, which serves recorded lookup bytes and denies DNS/socket access before I/O; `tests/test_cli_acceptance.py::test_subprocess_network_guard_blocks_before_dns` proves the guard is live. Catalog dispatch patches urlopen; bootstrap commands do not use providers. Wheel build/install use --no-index --no-deps and existing local released dependencies. |

## Reproduction

```sh
PYTHONDONTWRITEBYTECODE=1 /workspace/tif-ai/major-venvs/stocks-222b1/bin/python -m pytest -q -p no:cacheprovider tests/test_cli_catalog.py tests/test_cli_presentation.py tests/test_cli_bootstrap.py tests/test_cli_acceptance.py
PYTHONDONTWRITEBYTECODE=1 /workspace/tif-ai/major-venvs/stocks-222b1/bin/python -m pytest -q -p no:cacheprovider
```

The packaging fixture creates a fresh temporary venv, installs the built wheel without dependencies/index access, and appends only the authoritative environment's existing released dependency directory through a .pth file. It removes inherited PYTHONPATH and checks the stocks import resolves to its own installed site-packages. Acceptance adds only the test-helper directory to PYTHONPATH, never repository production sources. The helper is not included in the wheel and adds no production provider or domain contract.

## Boundaries

The CLI writes only by dispatching the existing watchlist events; reads leave storage untouched and a missing file stays absent until first save. The same whole-file serialization, no-locking/comment-loss and supported-extension limitations as the watchlist repository apply. No export flags, version bump, dependency change, interactive loop, new provider or business rule is introduced. Wide per-symbol tables grow columns for repeated diagnostics rather than dropping them. Native history rendering prints ordered bar rows and an empty response for no trading days. Core default logging can precede the rendered response; table assertions isolate that response, and logging remains configuration-owned. Missing/malformed configuration remains a core infrastructure fault, not a new catalogued stocks error. Live-provider smoke tests remain separately skipped/offline; these checks do not certify a live network provider.
