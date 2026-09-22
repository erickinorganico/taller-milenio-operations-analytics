"""Typed SQLite projections and independent read-only analytical queries."""
import sqlite3
from pathlib import Path
from .contracts import FIELDS


def create_views(store):
    # Identifiers come exclusively from the versioned contract, never from input.
    for kind, fields in FIELDS.items():
        columns = ["id", "version"] + [f"json_extract(document, '$.{name}') AS {name}" for name in fields]
        store.db.execute(f"CREATE VIEW IF NOT EXISTS v_{kind} AS SELECT {', '.join(columns)} FROM entities WHERE type='{kind}'")


def query_snapshots(db_path):
    root = Path(__file__).resolve().parent.parent / "queries"
    connection = sqlite3.connect(Path(db_path).resolve().as_uri() + "?mode=ro", uri=True)
    connection.row_factory = sqlite3.Row
    try:
        connection.execute("PRAGMA query_only=ON")
        return {path.stem: [dict(row) for row in connection.execute(path.read_text(encoding="utf-8"))]
                for path in sorted(root.glob("*.sql"))}
    finally:
        connection.close()
