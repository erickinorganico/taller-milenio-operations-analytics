# Local decision opportunity review

Reviewed the current source under `milenio/` and the deterministic reporting
path. There are no LLM, paid model, or model routing callers. The repeated
decisions currently in code are exact contract rules: field typing and ranges,
state transitions, references, inventory arithmetic, capacity uniqueness, SLA
dates, payment reconciliation, and proposal approval gates. These require
authoritative evidence and deterministic outcomes, so they remain ordinary
Python validation and reporting logic.

There is no observed classification or ranking input/output, call frequency,
baseline, labeled evaluation set, or measured inference latency. A future
candidate could be a bounded triage label for a free-text intake note, with
choices `particular`, `fleet`, `tow`, or `review`, but no such caller exists in
the current source and no inference was run. The consequences of a wrong label
would include routing an urgent tow or customer request incorrectly, so the
fallback would be `review` plus the existing human approval workflow.

Decision: **not applicable** for this snapshot. No Laya runtime was installed,
no checkpoint was loaded, and no savings or quality claims are made. Revisit
only when a real repeated free-text caller is added; predeclare a labeled
Spanish/English evaluation set, ambiguous and adversarial cases, the review
fallback, cold/warm latency, retries, and supervision cost before any shadow
experiment or promotion.
