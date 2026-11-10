# tiferet-stocks

## Watchlist storage

The reference configuration uses `data/watchlists.yml`; `.yaml`, `.yml` and `.json` files are supported through Tiferet's configuration repository. The starter YAML is empty. A missing file is an empty collection: reads return no watchlists and never create a file or directory, and the first save creates the file and any missing parent directories. Malformed files and access failures are not treated as empty.

Each watchlist is keyed by id under `watchlists`; its body contains its name, optional description and timestamps, and ordered `symbol_ids`. Only the watchlist repository writes storage. Reads leave bytes and timestamps unchanged. Saves preserve other watchlists and unrelated root nodes, but rewrite the whole file without locking; concurrent writers can lose changes, and YAML comments are not preserved. An unsupported extension is a core `ServiceError`, not a catalogued watchlist error.


## Watchlist features

The reference `stocks_client` session exposes `watchlists.get`, `watchlists.list`, `watchlists.create`, `watchlists.update`, `watchlists.delete`, `watchlists.add`, `watchlists.remove` and `watchlists.move`. Changes take `id`; create also takes `name`, optional `description` and initial `symbol_ids`. Update changes supplied name/description values. Symbol edits take `symbol_id`; add uses `index` and move uses `to_index`, defaulting to -1 (the end). Positions are zero-based; values past the end land last, and values below -1 are rejected.

Every successful change except delete stamps `updated_at`, setting `created_at` only on creation. An explicit offset-bearing ISO `at` overrides the event clock. Reads never stamp. Duplicate ids, absent watchlists/symbols and invalid negative positions are checked before aggregate mutation and resolve through the configured watchlist error catalog. Adding a ticker does not look it up. Changes work on private aggregates so rejected requests do not mutate service-held objects.

## Command line

After `pip install .`, run `tiferet-stocks exchanges list` with the reference config.yml in the current directory, or use `tiferet-stocks --config /path/to/config.yml exchanges list`. The package installs the console script and code, not a writable configuration or data directory. Provider and watchlist paths are CWD-relative unless absolute paths are configured. The reference provider is Yahoo; the acceptance suite substitutes static prices/history and recorded lookup responses without network access.

The thirteen commands cover quotes get/history, symbols get/resolve, exchanges list, and watchlists list/get/create/update/delete/add/remove/move. Quote and lookup tables retain every warning and failure by symbol; other results use core's native formatting. Catalogued domain errors exit 1 and parser errors exit 2. See [CLI contract](docs/cli-contract.md) for syntax/configuration and [acceptance evidence](docs/cli-acceptance.md) for the twelve RFP criteria and installed-wheel tests.
