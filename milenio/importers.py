"""Strict, local CSV preview/export helpers (stdlib only)."""
from __future__ import annotations

import csv
import io
import json
import re
from datetime import datetime

from .contracts import DEMO_NOW, FIELDS
from .contracts import FLOWS, INITIAL

IMPORTABLE = {"customers", "vehicles", "leads", "suppliers", "parts"}
MAX_BYTES, MAX_ROWS = 1_000_000, 500
_NUMERIC = {"int", "money", "positive", "signed"}


def _err(row, field, error):
    return {"row": row, "field": field, "error": error}


def _formula(value: str, spec: str) -> bool:
    return spec not in _NUMERIC and value.lstrip().startswith(("=", "+", "-", "@"))


def _parse(value: str, spec: str):
    if value is None:
        value = ""
    if not isinstance(value, str):
        raise ValueError("expected text")
    value = value.strip()
    if value == "":
        if spec.endswith("?"):
            return None
        raise ValueError("required value")
    base = spec.rstrip("?")
    if _formula(value, base):
        raise ValueError("formula-like values are not allowed")
    if base == "str" or base.startswith("ref:") or base == "date":
        if base == "date":
            parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
            if parsed.tzinfo is None:
                raise ValueError("date must include timezone")
        return value
    if base == "bool":
        if value.lower() not in ("true", "false"):
            raise ValueError("expected true or false")
        return value.lower() == "true"
    if base in _NUMERIC:
        try:
            number = int(value)
        except ValueError as exc:
            raise ValueError("expected integer") from exc
        if base == "positive" and number <= 0:
            raise ValueError("must be positive")
        return number
    if base == "list":
        try:
            result = json.loads(value)
        except json.JSONDecodeError as exc:
            raise ValueError("expected JSON list") from exc
        if not isinstance(result, list):
            raise ValueError("expected JSON list")
        return result
    if base.startswith("enum:"):
        choices = base[5:].split(",")
        if value not in choices:
            raise ValueError("must be one of " + ", ".join(choices))
        return value
    if base == "state":
        return value
    raise ValueError("unsupported field type")


def preview_csv(entity_type: str, csv_text: str) -> dict:
    result = {"ok": False, "rows": [], "errors": [], "columns": [], "synthetic": True}
    if entity_type not in IMPORTABLE:
        result["errors"].append(_err(1, "entity_type", "entity is not importable"))
        return result
    if not isinstance(csv_text, str):
        result["errors"].append(_err(1, "csv", "CSV must be text"))
        return result
    if len(csv_text.encode("utf-8")) > MAX_BYTES:
        result["errors"].append(_err(1, "csv", "CSV exceeds 1 MB"))
        return result
    if not csv_text.lstrip("\ufeff").strip():
        result["errors"].append(_err(1, "csv", "CSV is empty"))
        return result
    try:
        reader = csv.DictReader(io.StringIO(csv_text.lstrip("\ufeff")))
        columns = reader.fieldnames or []
        result["columns"] = columns
        if not columns:
            result["errors"].append(_err(1, "columns", "header row required"))
        if len(columns) != len(set(columns)):
            result["errors"].append(_err(1, "columns", "duplicate column"))
        allowed = {"id", "synthetic", *FIELDS[entity_type]}
        for col in columns:
            if not col or col not in allowed:
                result["errors"].append(_err(1, col or "columns", "unknown column"))
        required = {"id", "synthetic"} | {f for f, t in FIELDS[entity_type].items() if not t.endswith("?")}
        missing = required - set(columns)
        for col in sorted(missing):
            result["errors"].append(_err(1, col, "required column missing"))
        seen = set()
        row_count = 0
        for row_number, raw in enumerate(reader, 2):
            row_count += 1
            if row_number - 1 > MAX_ROWS:
                result["errors"].append(_err(row_number, "csv", "maximum 500 rows exceeded"))
                break
            parsed = {}
            if None in raw:
                result["errors"].append(_err(row_number, "columns", "too many values"))
            ident = (raw.get("id") or "").strip()
            if not ident:
                result["errors"].append(_err(row_number, "id", "required value"))
            elif not re.fullmatch(r"[A-Za-z0-9_-]{1,64}", ident):
                result["errors"].append(_err(row_number, "id", "invalid id"))
            elif ident in seen:
                result["errors"].append(_err(row_number, "id", "duplicate id"))
            seen.add(ident)
            if (raw.get("synthetic") or "").strip().lower() != "true":
                result["errors"].append(_err(row_number, "synthetic", "must be true"))
            parsed["id"] = ident
            for field, spec in FIELDS[entity_type].items():
                try:
                    parsed[field] = _parse(raw.get(field, ""), spec)
                    if isinstance(parsed[field], str) and len(parsed[field]) > 4000:
                        raise ValueError("text exceeds 4000 characters")
                except ValueError as exc:
                    result["errors"].append(_err(row_number, field, str(exc)))
            status = parsed.get("status")
            if entity_type in INITIAL and status != INITIAL[entity_type]:
                result["errors"].append(_err(row_number, "status", "new imports must use initial state"))
            if not result["errors"] or row_number not in {e["row"] for e in result["errors"]}:
                # Reuse the domain's authoritative type/range/state checks at
                # preview time, while keeping references for the Store pass.
                from .domain import DomainError, validate_record
                candidate = {"id": ident, "version": 1, "synthetic": True,
                             "created_at": DEMO_NOW, "updated_at": DEMO_NOW, **parsed}
                try:
                    validate_record(entity_type, candidate)
                except DomainError as exc:
                    result["errors"].append(_err(row_number, "record", str(exc)))
            result["rows"].append(parsed)
        if row_count == 0:
            result["errors"].append(_err(2, "csv", "at least one data row is required"))
    except csv.Error as exc:
        result["errors"].append(_err(1, "csv", f"invalid CSV: {exc}"))
    result["ok"] = not result["errors"]
    if not result["ok"]:
        result["rows"] = []
    return result


def apply_csv(store, entity_type: str, csv_text: str, actor: str = "Operador demo") -> dict:
    """Validate then atomically create rows in Store, retaining dict compatibility."""
    preview = preview_csv(entity_type, csv_text)
    if not preview["ok"]:
        return {"ok": False, "rows": 0, "errors": preview["errors"], "synthetic": True}
    if hasattr(store, "db") and hasattr(store, "data"):
        from .domain import DomainError, validate_dataset, validate_record
        with store.lock:
            try:
                if not store.verify_audit():
                    return {"ok": False, "rows": 0, "errors": [_err(1, "audit", "audit integrity check failed")], "synthetic": True}
                store.db.execute("BEGIN IMMEDIATE")
                existing = {r["id"] for r in store.data().get(entity_type, [])}
                conflicts = [_err(i + 2, "id", "id already exists") for i, row in enumerate(preview["rows"]) if row["id"] in existing]
                if conflicts:
                    store.db.execute("ROLLBACK")
                    return {"ok": False, "rows": 0, "errors": conflicts, "synthetic": True}
                for row in preview["rows"]:
                    item = {"id": row["id"], "version": 1, "synthetic": True,
                            "created_at": DEMO_NOW, "updated_at": DEMO_NOW, **row}
                    if store.get(entity_type, item["id"]) is not None:
                        raise ValueError("ID ya existe")
                    validate_record(entity_type, item)
                    store.save(entity_type, item, actor, "import")
                validate_dataset(store.data())
                store.db.execute("COMMIT")
                return {"ok": True, "rows": len(preview["rows"]), "errors": [], "synthetic": True, "actor": actor}
            except Exception as exc:
                store.db.execute("ROLLBACK")
                message = str(exc) or "import rejected"
                return {"ok": False, "rows": 0, "errors": [_err(1, "dataset", message)], "synthetic": True}
    return {"ok": False, "rows": 0, "errors": [_err(1, "store", "apply_csv requires a Store")], "synthetic": True}


def export_csv(entity_type: str, records) -> str:
    if entity_type not in FIELDS:
        raise ValueError("unknown entity")
    columns = ["id", *FIELDS[entity_type], "synthetic"]
    out = io.StringIO(newline="")
    writer = csv.DictWriter(out, fieldnames=columns, lineterminator="\n")
    writer.writeheader()
    for record in records:
        row = {}
        for col in columns:
            value = record.get(col, "")
            if value is None:
                value = ""
            if isinstance(value, list):
                value = json.dumps(value, ensure_ascii=False, separators=(",", ":"))
            elif isinstance(value, bool):
                value = "true" if value else "false"
            text = str(value)
            spec = FIELDS[entity_type].get(col, "str")
            if col != "synthetic" and spec.rstrip("?") not in _NUMERIC and text.lstrip().startswith(("=", "+", "-", "@")):
                text = "'" + text
            row[col] = text
        writer.writerow(row)
    return out.getvalue()


__all__ = ["preview_csv", "apply_csv", "export_csv", "IMPORTABLE"]
