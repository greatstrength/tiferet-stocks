# TSTK1-RFP-005 CLI Command and Request Contract

Group 1 supplies the actual declarative catalog, command-id constants and request-binding parser factory. It does not yet install a console entrypoint or change response rendering; those are later conceptual commits. Existing programmatic feature signatures and results remain unchanged.

The parser delegates to released Tiferet 2.2.2b1's public parse_cli_args_handler with commands read by CliConfigRepository from cli.cmds. No custom argparse implementation, invented dest field or private context assignment is used. Public parsing returns the same feature id and core headers, with a copied data dictionary adapting the names below.

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
| watchlists add ID SYMBOL [--index INDEX] | watchlists.add | id, symbol_id, integer index default -1 |
| watchlists remove ID SYMBOL | watchlists.remove | id, symbol_id |
| watchlists move ID SYMBOL [--to-index INDEX] | watchlists.move | id, symbol_id, integer to_index default -1 |

Core list arguments use nargs '+' for one or more values. The optional exchange map uses core's dict interpretation of key=value tokens; omission preserves None for the existing event's optional exchanges argument. Negative -1/-2 values parse as integers; whether a value is a valid ordering request is decided by the existing watchlist feature, not duplicated in the parser. The command constants equal the already-existing feature ids.

## Validation

`tests/test_cli_catalog.py` checks the exact thirteen-command set, all argument signatures, name remapping, headers, unchanged parser inputs, scalar defaults, negative values and core parse failures. Integration cases dispatch all thirteen parsed commands through the existing App feature pipeline. Prices and daily bars use StaticPriceRepository; symbol lookups use recorded responses behind a patched urlopen and never call the network. Rejected -2 changes preserve stored bytes and retain the configured watchlist error code.

## Approved later groups

Group 2 adds per-symbol presentation preserving every warning/failure without changing the library's programmatic return values. Group 3 supplies public CLI factory adaptation, CWD config.yml or explicit --config, blueprint/package registration and the console entrypoint. Group 4 adds installed-command, output/error/exit-code and full acceptance evidence. No version/dependency change or expansion to other features is part of this lane.


## Symbol presentation

Quotes and lookup answers render as native core tables with one row per encountered symbol id, including ids represented only by warnings or failures. Quote scalars remain scalars; quote_symbol_id and resolved_symbol_id retain provider identity independently of the requested symbol_id. Symbol metadata uses symbol_ prefixes, and quote fetched_at is retained when present. Numbered failure_N_* and warning_N_* columns preserve every field of every record, including repeated reasons, details and attempts; counts make omissions visible. Other responses keep core's native formatting. Presentation never replaces or modifies the library result.
