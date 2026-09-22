# Synthetic process replay

`milenio.process_replay.analyze_process_events(events, dataset)` replays
structured lifecycle events without changing the input lists. It groups cases
by entity type and ID, orders a copied trace by UTC timestamp, checks each edge
against `contracts.FLOWS`, and reports case variants, transition counts, stage
durations, endpoint agreement, and cycle hours.

Records with a state machine but no event history are reported as `unknown`
coverage. They are not treated as nonconformant. Invalid edges, out-of-order
input timestamps, and endpoint mismatches are separate summary measures.

The operating scenario exercises ordinary delivered paths plus legal
`waiting_parts` and `rework` loops. Durations are synthetic evidence for testing
the replay mechanics only; they do not establish real workshop timing, SLA
performance, or commercial outcomes.
