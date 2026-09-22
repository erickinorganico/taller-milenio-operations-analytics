# Client input examples

These files are synthetic fixtures for `milenio.client_input`:

- `client_input_blank.xlsx` and `blank_csv/` are empty templates with the
  required headers and configuration fields.
- `client_input_sample.xlsx` and `sample_csv/` contain the same synthetic
  cutoff and cover waiting parts, ready, delivered, cancelled, a delivered
  order without an issued invoice, an overdue partial invoice, a settled
  invoice, and one inventory shortage.

The sample cutoff was supplied explicitly when the files were generated:
`2026-09-22T12:00:00-07:00`. It is a fixture value, not a live business clock.
All files are safe-to-publish examples and contain no client or employee data.

To generate a new pair with another cutoff:

```python
from milenio.client_input import generate_client_templates

generate_client_templates(
    "examples/client_data/generated",
    as_of="2026-09-22T12:00:00-07:00",
    snapshot_id="sample-2026-09-22",
)
```
