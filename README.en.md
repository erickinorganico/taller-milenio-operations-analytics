# Milenio V5 · Workshop operations and evidence-based intelligence

Local Spanish-language Django application covering intake, inspection, estimates and approval, work orders, parts/purchasing, quality checks, delivery and administrative collections. Includes fleet contracts, maintenance plans and towing milestones. SQLite stores 24 domain tables; 18 live metrics trace back to records. Three governed review agents produce evidence-bound proposals and human-owned action tasks.

Run `Setup-Web.ps1`, then `Iniciar-Demo.cmd` for synthetic data or `Iniciar-Milenio.cmd` for an empty installation. Windows x64/Python 3.12 is the tested target; the delivery ZIP includes offline dependency wheels. Persistent data defaults to LocalAppData, outside the source folder. The server binds to loopback only.

Rules mode is fully local. The optional native Codex adapter is implemented and tested with mocks; this delivery's CLI preflight found no authenticated session, so live V5 model inference remains unverified. There is no paid API fallback. Financial documents are administrative records, not fiscal invoices. Real workshop adoption, deployment acceptance and business impact require a pilot.

See the [Spanish README](README.md), [installation guide](docs/V5-INSTALACION.md), [verification](docs/V5-VERIFICACION.md), [GSD state](.planning/STATE.md), and [earlier V4 analytical toolkit](README-V4.md).
