# CSV imports and exports

The local demo supports create-only CSV imports for `customers`, `vehicles`,
`leads`, `suppliers`, and `parts`.  `preview_csv(entity_type, csv_text)` parses
UTF-8 (including a BOM), validates types and required columns, and returns
`{ok, rows, errors, columns, synthetic}`.  The rows omit metadata and are safe
to review before writing.  A file is rejected in full when any row is invalid;
the limits are 1 MB and 500 rows.

CSV columns are the contract fields plus `id` and `synthetic`.  `id` is
required, IDs must be unique within the file, and `synthetic` must literally be
`true`.  Unknown columns, non-boolean booleans, non-integer money/counts,
invalid dates, formula-like text (`=`, `+`, `-`, or `@` after whitespace), and
duplicate IDs are errors.  Numeric negative values remain available for the
numeric contract types; signed stock adjustments are represented separately by
the domain stock command.

`apply_csv` first runs the same preview and then creates records in a `Store`
inside one `BEGIN IMMEDIATE` transaction.  It uses the domain record validator,
writes audit events with the supplied actor, and validates the complete dataset
before commit.  Existing IDs or a broken cross-entity invariant reject the
entire batch and roll back both records and audit events.  A small dict adapter
is retained for isolated legacy tests.

`export_csv` emits spreadsheet-safe UTF-8 CSV.  Text cells beginning with a
spreadsheet formula prefix are prefixed with an apostrophe; metadata beyond
`synthetic` is intentionally omitted from the portable import format.
