# TSTK1-RFP-004 Watchlist Acceptance Packet

Scope: issue [#5](https://github.com/greatstrength/tiferet-stocks/issues/5), prototype implementation only. No version/dependency change, pytest retirement, tester API, history/Quotations change or release action is included. The authoritative runtime baseline is released Tiferet 2.2.2b1, installed in an isolated environment.

## Decisions applied

The Chief's missing-file ruling is implemented: a missing file is an empty collection, reads create nothing, get returns None for an absent key, and the first save creates storage. The starter is empty. Existence derives from get rather than a new exists contract. Events check user-facing rules before aggregate mutation and work on private copies. Explicit offset-bearing ISO at values override the clock. None means an omitted update field; an empty string can clear a description. Delete returns the deleted id and does not stamp.

## Documented keyed document

This generic example round-trips with the same data through YAML and JSON. Serialization may reformat the file; comments are not preserved.

```yaml
watchlists:
  etfs:
    name: Broad ETFs
    description: Example watchlist
    created_at: '2026-10-26T18:00:00-07:00'
    updated_at: '2026-10-26T18:00:00-07:00'
    symbol_ids:
    - SPY
    - QQQ
    - XLK
```

## All 18 acceptance criteria

The numbering below follows the issue's acceptance list in order. These are local implementation checks for independent review, not QA approval or checked issue boxes.

| AC | Requirement | Actual executable coverage |
|---|---|---|
| 1 | Exactly six Watchlist fields | `tests/domain/test_watchlist.py::test_watchlist_fields_and_defaults` |
| 2 | Add default, zero, length, past-end, -1 and rejected -2 | `tests/mappers/test_watchlist.py::test_add_symbol_indices`, `test_invalid_mutation_preserves_state`; `tests/test_watchlist_acceptance.py::test_feature_format_parity_and_write_boundary` |
| 3 | Move default/-1, first/middle/last/past-end/exact index and rejected -2 | `tests/mappers/test_watchlist.py::test_move_symbol_indices`, `test_invalid_mutation_preserves_state`; feature-format acceptance probe |
| 4 | Duplicate add and absent remove/move rejected | `tests/mappers/test_watchlist.py::test_invalid_mutation_preserves_state`; `tests/events/test_watchlist.py::test_rejected_changes_precheck_before_aggregate`; feature-format acceptance probe |
| 5 | Only name/description settable | `tests/mappers/test_watchlist.py::test_settable_labels`, `test_dedicated_fields_not_settable` |
| 6 | Upsert sets both timestamps initially and preserves creation later | `tests/mappers/test_watchlist.py::test_upsert_preserves_creation`; `tests/events/test_watchlist.py::test_changes_stamp_private_copy` |
| 7 | All five catalogued errors precede aggregate calls and use configured messages | `tests/events/test_watchlist.py::test_rejected_changes_precheck_before_aggregate`; `tests/test_watchlist_features.py::test_catalogued_messages_and_no_write_on_error` |
| 8 | Direct aggregate duplicate/-2 remains ModelError | `tests/mappers/test_watchlist.py::test_invalid_mutation_preserves_state` |
| 9 | Unsupported extension is not catalogued | `tests/repos/test_watchlist.py::test_unsupported_extension_is_not_empty`; `tests/test_watchlist_features.py::test_default_error_catalog_matches_assets` |
| 10 | ConfigObject excludes body id, with no exclude_none role entry | `tests/mappers/test_watchlist.py::test_config_serialization_and_mapping` |
| 11 | Missing description omitted | `tests/mappers/test_watchlist.py::test_config_serialization_and_mapping`; `tests/repos/test_watchlist.py::test_save_replace_delete_preserves_other_data` |
| 12 | Empty symbol list remains [] | Same serialization and repository replacement tests as AC11 |
| 13 | Documented YAML round-trip and equivalent JSON | `tests/test_watchlist_acceptance.py::test_documented_watchlists_round_trip`; `tests/repos/test_watchlist.py::test_first_save_and_round_trip` |
| 14 | Delete one of two watchlists preserves the other | `tests/repos/test_watchlist.py::test_save_replace_delete_preserves_other_data`; `tests/test_watchlist_features.py::test_first_create_and_all_features` |
| 15 | Reference service points to data/watchlists.yml | `tests/repos/test_watchlist.py::test_starter_and_reference_configuration` |
| 16 | Every change except Delete stamps; at overrides clock | `tests/events/test_watchlist.py::test_changes_stamp_private_copy`, `test_create_uses_clock_or_override`, `test_read_and_delete_do_not_stamp` |
| 17 | Get/List reads preserve bytes | `tests/repos/test_watchlist.py::test_first_save_and_round_trip`; `tests/test_watchlist_features.py::test_first_create_and_all_features`; feature-format acceptance probe |
| 18 | Production stocks writes only from repos/watchlist.py | `tests/test_watchlist_acceptance.py::test_feature_format_parity_and_write_boundary`, `test_bounded_mutations_are_killed[extra_write-*]` |

## Runtime write-boundary proof

The subprocess probe installs a Python audit hook that inspects write-mode open events and filesystem-changing events. It walks live frames and attributes each operation to the innermost production tiferet_stocks module. Only repos/watchlist.py may originate a write, including writes delegated to core loaders. Test fixture/helper frames are not production and are not miscounted. All eight watchlist features and the four pre-existing read features run under the hook. Both YAML and JSON exercise 14 explicit ordering cases, eight configured rejection cases, read byte/mtime preservation, deterministic timestamps and preservation of another watchlist. This is a bounded runtime regression guard for exercised behavior, not a claim to sandbox every possible native syscall or unexecuted code path.

## Bounded mutation gates

`tests/test_watchlist_acceptance.py::test_bounded_mutations_are_killed` repeats the acceptance probe for both formats with each in-memory mutant. Production files remain unchanged and all patches die with their subprocess.

| Mutant | Positive check that kills it | Expected evidence |
|---|---|---|
| move ignores requested index and always appends | Exact literal final-order assertions | `ORDER:` |
| event verify prechecks disabled | Taken-key request must raise its catalogued error | `PRECHECK_MISSING:` |
| clock writes a rogue file from the event module | Audit-frame production write boundary; rogue file never created | `WRITE_BOUNDARY:` |
| upsert resets creation time on every change | Existing creation timestamp must survive | `CREATION_TIME_RESET` |

## Reproduction

From the branch worktree, run `PYTHONDONTWRITEBYTECODE=1 /workspace/tif-ai/major-venvs/stocks-222b1/bin/python -m pytest -q -p no:cacheprovider`. Focused final acceptance: append `tests/test_watchlist_acceptance.py`. The optional older 2.2.0 run is compatibility evidence only, not the release baseline. The subprocess tests use the invoking interpreter, so they cannot silently fall back to another Tiferet version.

## Remaining review boundaries

All 18 criteria have executable local coverage; independent Saito review and QA Operator approval remain separate. No issue is closed and no PR, remote branch, tag or release is changed by this packet. Whole-file ASCII, import grouping/placement, artifact spacing and diff whitespace are checked before the final conceptual commit. Known storage limits remain whole-file rewrites, no locking and YAML comment loss, as documented in the RFP.
