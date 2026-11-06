# tiferet-stocks

## Watchlist storage

The reference configuration uses `data/watchlists.yml`; `.yaml`, `.yml` and `.json` files are supported through Tiferet's configuration repository. The starter YAML is empty. A missing file is an empty collection: reads return no watchlists and never create a file or directory, and the first save creates the file and any missing parent directories. Malformed files and access failures are not treated as empty.

Each watchlist is keyed by id under `watchlists`; its body contains its name, optional description and timestamps, and ordered `symbol_ids`. Only the watchlist repository writes storage. Reads leave bytes and timestamps unchanged. Saves preserve other watchlists and unrelated root nodes, but rewrite the whole file without locking; concurrent writers can lose changes, and YAML comments are not preserved. An unsupported extension is a core `ServiceError`, not a catalogued watchlist error.
