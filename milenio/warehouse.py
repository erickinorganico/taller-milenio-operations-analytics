"""Normalized SQLite warehouse for the synthetic operating snapshots."""
from __future__ import annotations

import json
import sqlite3
from pathlib import Path

from .contracts import DEMO_NOW, FIELDS, FLOWS, INITIAL
from .domain import date_value, validate_dataset


def _sql_type(spec):
    base = spec.rstrip("?")
    if base in {"int", "money", "positive", "signed"}:
        return "INTEGER"
    if base == "bool":
        return "INTEGER"
    if base == "list":
        return "TEXT"
    return "TEXT"


def _literal_check(field, spec, kind=None):
    base = spec.rstrip("?")
    if base == "bool":
        return f'CHECK ({field} IN (0,1))'
    if base == "positive":
        return f"CHECK ({field} > 0)"
    if base in {"int", "money"}:
        return f"CHECK ({field} >= 0)"
    if base == "signed":
        return ""
    if base.startswith("enum:"):
        values = ",".join("'" + x + "'" for x in base[5:].split(","))
        return f"CHECK ({field} IN ({values}))"
    if base == "state" and kind in FLOWS:
        values = ",".join("'" + x + "'" for x in FLOWS[kind])
        return f"CHECK ({field} IN ({values}))"
    if base == "list":
        return f"CHECK (json_valid({field}))"
    return ""


def _table_sql(kind):
    cols = ["id TEXT PRIMARY KEY NOT NULL", "version INTEGER NOT NULL CHECK(version > 0)", "synthetic INTEGER NOT NULL CHECK(synthetic=1)", "created_at TEXT NOT NULL", "updated_at TEXT NOT NULL"]
    fks = []
    for field, spec in FIELDS[kind].items():
        nullable = "" if spec.endswith("?") else " NOT NULL"
        check = _literal_check(field, spec, kind)
        cols.append(f'"{field}" {_sql_type(spec)}{nullable} {check}'.strip())
        if spec.startswith("ref:"):
            fks.append(f'FOREIGN KEY("{field}") REFERENCES "{spec[4:].rstrip("?")}"(id)')
    return f'CREATE TABLE "{kind}" (\n  ' + ",\n  ".join(cols + fks) + "\n) STRICT;"


def _encode(record, kind):
    values = [record["id"], record["version"], 1, record["created_at"], record["updated_at"]]
    for field, spec in FIELDS[kind].items():
        value = record.get(field)
        if isinstance(value, bool):
            value = int(value)
        elif isinstance(value, list):
            value = json.dumps(value, ensure_ascii=False, sort_keys=True)
        values.append(value)
    return values


def build_warehouse(path, dataset, events=None, journeys=None):
    """Build a typed SQLite snapshot atomically and return its catalog."""
    target = Path(path).resolve()
    if target.exists():
        raise ValueError("warehouse destination already exists")
    validate_dataset(dataset)
    events = list(events or [])
    journeys = list(journeys or [])
    indexes = {kind: {row["id"]: row for row in rows} for kind, rows in dataset.items()}
    event_seen, last_event, first_event = set(), {}, {}
    for event in events:
        required = ("event_id", "entity_type", "entity_id", "from_state", "to_state", "at", "actor", "process_id", "synthetic")
        if not isinstance(event, dict) or any(key not in event for key in required):
            raise ValueError("invalid lifecycle event shape")
        if any(not isinstance(event[key], str) or not event[key].strip() for key in required if key != 'synthetic') or event["event_id"] in event_seen or event["synthetic"] is not True:
            raise ValueError("invalid or duplicate lifecycle event")
        event_seen.add(event["event_id"])
        if event["entity_type"] not in indexes or event["entity_id"] not in indexes[event["entity_type"]]:
            raise ValueError("lifecycle event references unknown entity")
        timestamp = date_value(event["at"])
        if timestamp > date_value(DEMO_NOW):
            raise ValueError("lifecycle event is after demo cutoff")
        if event["entity_type"] not in FLOWS:
            raise ValueError("lifecycle entity has no known state flow")
        if event["from_state"] == "initial":
            if event["to_state"] != INITIAL[event["entity_type"]]:
                raise ValueError("lifecycle does not start at legal initial state")
        elif event["to_state"] not in FLOWS[event["entity_type"]].get(event["from_state"], []):
            raise ValueError("illegal lifecycle transition")
        key = (event["entity_type"], event["entity_id"])
        if key not in first_event:
            if event['from_state'] != 'initial':
                raise ValueError('lifecycle history must include its initial event')
            first_event[key] = event
        if key in last_event:
            prior = last_event[key]
            if timestamp < date_value(prior["at"]):
                raise ValueError("lifecycle events are not chronological")
            if event["from_state"] != prior["to_state"]:
                raise ValueError("lifecycle from_state does not continue prior to_state")
        last_event[key] = event
    for key, event in last_event.items():
        current = indexes[key[0]][key[1]].get("status")
        if current and event["to_state"] != current:
            raise ValueError("lifecycle final state does not match dataset")
        if key[0] == "work_orders":
            work = indexes[key[0]][key[1]]
            if work['completed_at'] and date_value(last_event[key]["at"]) != date_value(work["completed_at"]):
                raise ValueError("work-order lifecycle endpoint does not match completed_at")
            first = first_event[key]
            if date_value(first["at"]) != date_value(work["opened_at"]):
                raise ValueError("work-order lifecycle endpoint does not match opened_at")
    journey_seen = set()
    for journey in journeys:
        refs = (("lead_id", "leads"), ("quote_id", "quotes"), ("appointment_id", "appointments"), ("work_order_id", "work_orders"))
        if not isinstance(journey.get('id'),str) or not journey['id'].strip() or journey.get("id") in journey_seen or any(journey.get(field) not in indexes[kind] for field, kind in refs):
            raise ValueError("invalid journey link")
        journey_seen.add(journey["id"])
        lead = indexes["leads"][journey["lead_id"]]
        quote = indexes["quotes"][journey["quote_id"]]
        appointment = indexes["appointments"][journey["appointment_id"]]
        work = indexes["work_orders"][journey["work_order_id"]]
        if len({lead["customer_id"], quote["customer_id"], appointment["customer_id"], work["customer_id"]}) != 1 or len({lead.get("vehicle_id"), quote["vehicle_id"], appointment["vehicle_id"], work["vehicle_id"]}) != 1 or work.get("quote_id") != quote["id"]:
            raise ValueError("journey ownership mismatch")
    target.parent.mkdir(parents=True, exist_ok=True)
    schema_parts = ["PRAGMA foreign_keys = ON;"]
    schema_parts.extend(_table_sql(kind) for kind in FIELDS)
    schema_parts.append("""CREATE TABLE lifecycle_events (
      event_id TEXT PRIMARY KEY NOT NULL, entity_type TEXT NOT NULL, entity_id TEXT NOT NULL,
      from_state TEXT NOT NULL, to_state TEXT NOT NULL, at TEXT NOT NULL,
      actor TEXT NOT NULL, process_id TEXT NOT NULL, synthetic INTEGER NOT NULL CHECK(synthetic=1)
    ) STRICT;""")
    schema_parts.append("""CREATE TABLE journey_links (
      id TEXT PRIMARY KEY NOT NULL, lead_id TEXT NOT NULL REFERENCES leads(id),
      quote_id TEXT NOT NULL REFERENCES quotes(id), appointment_id TEXT NOT NULL REFERENCES appointments(id),
      work_order_id TEXT NOT NULL REFERENCES work_orders(id), synthetic INTEGER NOT NULL CHECK(synthetic=1)
    ) STRICT;""")
    for kind in FIELDS:
        for field, spec in FIELDS[kind].items():
            if spec.startswith("ref:"):
                schema_parts.append(f'CREATE INDEX "idx_{kind}_{field}" ON "{kind}"("{field}");')
    schema_parts.extend(["CREATE INDEX idx_lifecycle_entity ON lifecycle_events(entity_type, entity_id, at);", "CREATE INDEX idx_lifecycle_at ON lifecycle_events(at);"])
    schema = "\n\n".join(schema_parts) + "\n"
    connection = sqlite3.connect(target)
    connection.execute("PRAGMA foreign_keys=ON")
    try:
        connection.executescript(schema)
        connection.execute("BEGIN")
        pending = list(dataset)
        inserted = set()
        while pending:
            progressed = False
            for kind in list(pending):
                targets = {spec[4:].rstrip("?") for spec in FIELDS[kind].values() if spec.startswith("ref:")}
                if not targets.issubset(inserted):
                    continue
                rows = dataset[kind]
                columns = ["id", "version", "synthetic", "created_at", "updated_at", *FIELDS[kind]]
                marks = ",".join("?" for _ in columns)
                sql = f'INSERT INTO "{kind}" ({",".join(chr(34)+c+chr(34) for c in columns)}) VALUES ({marks})'
                try:
                    for row in rows:
                        try:
                            connection.execute(sql, _encode(row, kind))
                        except sqlite3.IntegrityError as exc:
                            raise ValueError(f"row {row.get('id')}: {exc}") from exc
                except sqlite3.IntegrityError as exc:
                    raise ValueError(f"insert failed for {kind}: {exc}") from exc
                pending.remove(kind)
                inserted.add(kind)
                progressed = True
            if not progressed:
                raise ValueError("cannot order tables for foreign-key insertion")
        connection.executemany("INSERT INTO lifecycle_events VALUES (?,?,?,?,?,?,?,?,?)", [tuple(event[k] for k in ("event_id", "entity_type", "entity_id", "from_state", "to_state", "at", "actor", "process_id", "synthetic")) for event in events])
        connection.executemany("INSERT INTO journey_links VALUES (?,?,?,?,?,?)", [(j["id"], j["lead_id"], j["quote_id"], j["appointment_id"], j["work_order_id"], 1) for j in journeys])
        foreign = connection.execute("PRAGMA foreign_key_check").fetchall()
        if foreign:
            raise ValueError(f"foreign key check failed: {foreign}")
        connection.commit()
    except Exception:
        connection.rollback()
        connection.close()
        if target.exists():
            target.unlink()
        raise
    finally:
        if connection:
            connection.close()
    schema_path = target.with_name("schema.sql")
    schema_path.write_text(schema, encoding="utf-8")
    counts = {}
    catalog_tables = {}
    check = sqlite3.connect(target)
    for kind in [*FIELDS, "lifecycle_events", "journey_links"]:
        counts[kind] = check.execute(f'SELECT COUNT(*) FROM "{kind}"').fetchone()[0]
        catalog_tables[kind] = {"grain": "one row per " + kind[:-1] if kind.endswith("s") else "one row per event", "count": counts[kind], "columns": [row[1] for row in check.execute(f'PRAGMA table_info("{kind}")')], "refs": {field: spec[4:].rstrip("?") for field, spec in FIELDS.get(kind, {}).items() if spec.startswith("ref:")}}
    check.close()
    mermaid = "erDiagram\n" + "\n".join(f"  {kind.upper()} {{ string id PK }}" for kind in FIELDS) + "\n"
    for kind, fields in FIELDS.items():
        for field, spec in fields.items():
            if spec.startswith("ref:"):
                mermaid += f"  {spec[4:].rstrip('?').upper()} ||--o{{ {kind.upper()} : {field}\n"
    mermaid += "  leads ||--o{ journey_links : lead_id\n  quotes ||--o{ journey_links : quote_id\n  appointments ||--o{ journey_links : appointment_id\n  work_orders ||--o{ journey_links : work_order_id\n"
    return {"database": str(target), "schema_sql": str(schema_path), "tables": catalog_tables, "counts": counts, "schema_version": 2, "synthetic": True, "demo_now": DEMO_NOW, "mermaid": mermaid}


__all__ = ["build_warehouse"]
