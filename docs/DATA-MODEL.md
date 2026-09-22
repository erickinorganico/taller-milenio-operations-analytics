# Normalized warehouse v2

`milenio.warehouse.build_warehouse(path, dataset, events=None, journeys=None)`
materializes the contract into one typed SQLite table per entity, plus
`lifecycle_events` and explicit `journey_links`. Every entity table has a
primary key, synthetic metadata, typed fields, required-field constraints,
enum/range checks, foreign keys, and indexes for references. `PRAGMA
foreign_key_check` runs before commit. A failed build removes the destination
and leaves no partial warehouse.

`lifecycle_events` records synthetic state history at event grain with event ID,
entity type and ID, from/to state, timestamp, actor, process ID, and synthetic
flag. `journey_links` preserves the lead → quote → appointment → work-order
linkage for generated historical scenarios rather than inferring conversion by
matching customer or vehicle IDs.

`make_operating_scenario()` starts with the v1 demo population and adds a
reproducible 90-day synthetic history: 160 completed work orders, varied
durations and amounts, recurring B2C/fleet clients, mixed collections,
consumption reservations, wait/rework lifecycle events, and explicit journeys.
All timestamps are before the frozen demo cutoff. The scenario remains synthetic
and is not evidence of actual Taller Milenio operations or commercial impact.

The returned catalog lists table columns, grain, references, counts, schema path,
and Mermaid entity relationships. The adjacent `schema.sql` is a portable,
inspectable DDL artifact for local analysis.
