"""Code-owned, read-only definitions and measured values for the synthetic studio.

The registry makes source coverage explicit. A missing denominator, lifecycle
history, or entire source table is unknown, never a reassuring measured zero.
"""
from __future__ import annotations

import json
import hashlib
import sqlite3
from pathlib import Path
from statistics import median

from .contracts import DEMO_NOW
from .domain import date_value


REGISTRY_PATH = Path(__file__).resolve().parent.parent / "contracts" / "metric_registry.json"
MAX_EVIDENCE_ROWS = 12

# Each SELECT returns n (count/sum), d (eligible population), and optionally v.
# The statements and table identifiers are owned by this module, never by an agent.
SQL = {
    "M-B2C-LEADS": "SELECT COUNT(*) n, COUNT(*) d FROM leads l JOIN customers c ON c.id=l.customer_id WHERE c.segment='particular'",
    "M-B2C-WON": "SELECT COALESCE(SUM(l.status='won'),0) n, COUNT(*) d FROM leads l JOIN customers c ON c.id=l.customer_id WHERE c.segment='particular'",
    "M-B2C-QUOTE-MATCH": "SELECT COUNT(DISTINCT CASE WHEN j.lead_id IS NOT NULL THEN l.id END) n, COUNT(DISTINCT l.id) d FROM leads l JOIN customers c ON c.id=l.customer_id LEFT JOIN journey_links j ON j.lead_id=l.id WHERE c.segment='particular'",
    "M-WIP-OPEN": "SELECT COALESCE(SUM(status NOT IN ('delivered','cancelled')),0) n, COUNT(*) d FROM work_orders",
    "M-WIP-WAITING-PARTS": "SELECT COALESCE(SUM(status='waiting_parts'),0) n, COALESCE(SUM(status NOT IN ('delivered','cancelled')),0) d FROM work_orders",
    "M-BAY-OCCUPANCY": "SELECT (SELECT COUNT(DISTINCT bay_id) FROM work_orders WHERE status IN ('scheduled','in_service','quality_check','rework') AND bay_id IS NOT NULL) n, COUNT(*) d FROM bays",
    "M-PROCESS-WAIT": "SELECT COALESCE(SUM(total_hours),0) n, COUNT(*) d FROM mart_process_waits",
    "M-STOCK-ON-HAND": "SELECT COALESCE(SUM(on_hand),0) n, COUNT(*) d FROM mart_inventory",
    "M-STOCK-RESERVED": "SELECT COALESCE(SUM(reserved),0) n, COUNT(*) d FROM mart_inventory",
    "M-STOCK-AVAILABLE": "SELECT COALESCE(SUM(available),0) n, COUNT(*) d FROM mart_inventory",
    "M-STOCK-REORDER": "SELECT COALESCE(SUM(available<=reorder_point),0) n, COUNT(*) d FROM mart_inventory",
    "M-FLEET-OPEN-OPPS": "SELECT COALESCE(SUM(status NOT IN ('won','lost')),0) n, COUNT(*) d FROM opportunities",
    "M-FLEET-PIPELINE": "SELECT COALESCE(SUM(CASE WHEN status NOT IN ('won','lost') THEN value_cents ELSE 0 END),0) n, COUNT(*) d FROM opportunities",
    "M-FLEET-ACCOUNT-COVERAGE": "SELECT COALESCE(SUM(EXISTS(SELECT 1 FROM opportunities o WHERE o.fleet_account_id=a.id)),0) n, COUNT(*) d FROM fleet_accounts a",
    "M-FLEET-ACTIVE-CONTRACTS": "SELECT COALESCE(SUM(status='active' AND approval_ref IS NOT NULL AND trim(approval_ref)<>'' AND julianday(starts_at)<=julianday(?) AND julianday(ends_at)>julianday(?)),0) n, COUNT(*) d FROM contracts",
    "M-FLEET-MAINTENANCE": "SELECT COALESCE(SUM(m.status IN ('due','scheduled') AND (julianday(m.due_at)<=julianday(?) OR v.odometer_km>=m.due_km)),0) n, COUNT(*) d FROM maintenance m JOIN vehicles v ON v.id=m.vehicle_id",
    "M-FLEET-SLA-ELIGIBILITY": "SELECT COALESCE(SUM(s.sla_status IN ('met','breached','at_risk','on_track')),0) n, COUNT(*) d FROM mart_service_journey s WHERE s.segment='fleet' AND s.contract_id IS NOT NULL AND s.status<>'cancelled'",
    "M-FLEET-SLA-RISK": "SELECT COALESCE(SUM(s.sla_status IN ('at_risk','breached')),0) n, COUNT(*) d FROM mart_service_journey s WHERE s.segment='fleet' AND s.status NOT IN ('delivered','cancelled') AND s.sla_status IN ('met','breached','at_risk','on_track')",
    "M-TOW-OPEN": "SELECT COALESCE(SUM(status NOT IN ('closed','cancelled')),0) n, COUNT(*) d FROM tows",
    "M-TOW-HUMAN-REFS": "SELECT COALESCE(SUM(safety_ref IS NOT NULL AND trim(safety_ref)<>'' AND human_approval_ref IS NOT NULL AND trim(human_approval_ref)<>''),0) n, COUNT(*) d FROM tows",
    "M-FIN-QUOTES": "SELECT COALESCE(SUM(amount_cents),0) n, COUNT(*) d FROM quotes",
    "M-FIN-INVOICED": "SELECT COALESCE(SUM(CASE WHEN status='issued' THEN amount_cents ELSE 0 END),0) n, COUNT(*) d FROM invoices",
    "M-FIN-PAID": "SELECT COALESCE(SUM(amount_cents),0) n, COUNT(*) d FROM payments",
    "M-AR-RECEIVABLE": "SELECT COALESCE(SUM(i.amount_cents-COALESCE(p.paid,0)),0) n, COUNT(*) d FROM invoices i LEFT JOIN (SELECT invoice_id,SUM(amount_cents) paid FROM payments GROUP BY invoice_id) p ON p.invoice_id=i.id WHERE i.status='issued'",
    "M-AR-OVERDUE": "SELECT COALESCE(SUM(CASE WHEN julianday(i.due_at)<julianday(?) THEN i.amount_cents-COALESCE(p.paid,0) ELSE 0 END),0) n, COUNT(*) d FROM invoices i LEFT JOIN (SELECT invoice_id,SUM(amount_cents) paid FROM payments GROUP BY invoice_id) p ON p.invoice_id=i.id WHERE i.status='issued'",
    "M-FIN-CASH-NET": "SELECT (SELECT COALESCE(SUM(amount_cents),0) FROM payments WHERE method='cash')-(SELECT COALESCE(SUM(amount_cents),0) FROM expenses WHERE method='cash') n, (SELECT COUNT(*) FROM payments)+(SELECT COUNT(*) FROM expenses) d",
    "M-FIN-EXPENSES": "SELECT COALESCE(SUM(amount_cents),0) n, COUNT(*) d FROM expenses",
    "M-WEEKLY-PROPOSALS": "SELECT COALESCE(SUM(status='pending' AND approval_required=1 AND external_execution=0),0) n, COUNT(*) d FROM proposals",
}

RATIOS = {
    "M-B2C-WON", "M-B2C-QUOTE-MATCH", "M-WIP-WAITING-PARTS", "M-BAY-OCCUPANCY",
    "M-STOCK-REORDER", "M-FLEET-ACCOUNT-COVERAGE", "M-FLEET-SLA-ELIGIBILITY",
    "M-FLEET-SLA-RISK", "M-TOW-HUMAN-REFS",
}
MEDIANS = {
    "M-SERVICE-CYCLE": (
        "SELECT cycle_hours FROM mart_service_journey WHERE status='delivered' AND history_available=1 AND cycle_hours IS NOT NULL ORDER BY cycle_hours",
        "SELECT COUNT(*) FROM work_orders WHERE status='delivered'",
    ),
    "M-TOW-CLOSE-HOURS": (
        "SELECT (julianday(closed_at)-julianday(requested_at))*24 FROM tows WHERE status='closed' AND closed_at IS NOT NULL AND julianday(closed_at)>=julianday(requested_at) ORDER BY requested_at,id",
        "SELECT COUNT(*) FROM tows WHERE status='closed'",
    ),
}
PARAMETERIZED = {"M-FLEET-ACTIVE-CONTRACTS", "M-FLEET-MAINTENANCE", "M-AR-OVERDUE"}


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _source_evidence(con: sqlite3.Connection, definition: dict) -> tuple[list[dict], int, dict[str, int]]:
    """Return a bounded sample of exact source field values and full table counts."""
    rows: list[dict] = []
    total = 0
    counts: dict[str, int] = {}
    for table in definition["source_tables"]:
        # All identifiers are code-owned and constrained by the checked registry.
        count = con.execute(f'SELECT COUNT(*) FROM "{table}"').fetchone()[0]
        counts[table] = count
        total += count
        if len(rows) == MAX_EVIDENCE_ROWS:
            continue
        pk = "event_id" if table == "lifecycle_events" else "id"
        fields = [field.split(".", 1)[1] for field in definition["source_fields"] if field.startswith(table + ".")]
        wanted = list(dict.fromkeys([pk, "version", *fields]))
        available = {column[1] for column in con.execute(f'PRAGMA table_info("{table}")')}
        wanted = [field for field in wanted if field in available]
        query = 'SELECT ' + ','.join('"' + field + '"' for field in wanted) + f' FROM "{table}" ORDER BY "{pk}" LIMIT ?'
        for record in con.execute(query, (MAX_EVIDENCE_ROWS - len(rows),)):
            item = dict(zip(wanted, record))
            rows.append({"table": table, "record_id": str(item[pk]), "version": item.get("version"),
                         "fields": {key: item[key] for key in wanted if key not in (pk, "version")}})
    return rows, total, counts


def build_metric_registry(database: str | Path | sqlite3.Connection, as_of: str | None = None) -> dict:
    """Calculate the 31 governed M-* metrics using a read-only SQLite source.

    A caller-supplied connection remains open and unchanged and has no inferred
    source identity. A path is opened in SQLite read-only mode and its SHA-256 is
    checked before and after the read. Unsupported cutoffs are rejected rather
    than projected.
    """
    cutoff = as_of or DEMO_NOW
    if date_value(cutoff) != date_value(DEMO_NOW):
        raise ValueError("The synthetic warehouse supports only DEMO_NOW")
    definitions = json.loads(REGISTRY_PATH.read_text(encoding="utf-8"))["metrics"]
    ids = [definition["metric_id"] for definition in definitions]
    if len(ids) != len(set(ids)) or set(ids) != set(SQL) | set(MEDIANS) | {"M-WEEKLY-EXCEPTIONS"}:
        raise ValueError("Metric metadata and code-owned SQL are inconsistent")
    owned = not isinstance(database, sqlite3.Connection)
    database_path = Path(database).resolve() if owned else None
    source_sha256 = _sha256(database_path) if database_path is not None else None
    con = sqlite3.connect(database_path.as_uri() + "?mode=ro", uri=True) if owned else database
    try:
        existing = {row[0] for row in con.execute("SELECT name FROM sqlite_master WHERE type='table'")}
        output = []
        for definition in definitions:
            metric_id = definition["metric_id"]
            query = SQL.get(metric_id) or (MEDIANS[metric_id][0] if metric_id in MEDIANS else None)
            missing = [table for table in definition["source_tables"] if table not in existing]
            # Marts are derived from source tables, but must exist to measure.
            if metric_id in MEDIANS and metric_id == "M-SERVICE-CYCLE" and "mart_service_journey" not in existing:
                missing.append("mart_service_journey")
            if metric_id in {"M-STOCK-ON-HAND", "M-STOCK-RESERVED", "M-STOCK-AVAILABLE", "M-STOCK-REORDER"} and "mart_inventory" not in existing:
                missing.append("mart_inventory")
            if metric_id in {"M-FLEET-SLA-ELIGIBILITY", "M-FLEET-SLA-RISK"} and "mart_service_journey" not in existing:
                missing.append("mart_service_journey")
            if metric_id == "M-PROCESS-WAIT" and "mart_process_waits" not in existing:
                missing.append("mart_process_waits")
            evidence_rows, evidence_total, source_counts = ([], 0, {}) if missing else _source_evidence(con, definition)
            numerator = denominator = value = None
            status, reason = "unknown", None
            if missing:
                reason = "Required source table absent: " + ", ".join(sorted(set(missing)))
            elif metric_id == "M-WEEKLY-EXCEPTIONS":
                reason = "No versioned exception source is materialized in this warehouse"
            elif metric_id == "M-B2C-QUOTE-MATCH" and source_counts.get("journey_links", 0) == 0:
                reason = "Explicit journey links were not supplied; attribution coverage is unknown"
            elif metric_id in MEDIANS:
                values = [row[0] for row in con.execute(MEDIANS[metric_id][0])]
                numerator, denominator = len(values), con.execute(MEDIANS[metric_id][1]).fetchone()[0]
                if values:
                    value, status = round(median(values), 3), "measured"
                else:
                    reason = "No eligible time observations with the required evidence"
            elif query:
                params = (cutoff, cutoff) if metric_id == "M-FLEET-ACTIVE-CONTRACTS" else (cutoff,) if metric_id in PARAMETERIZED else ()
                raw = con.execute(query, params).fetchone()
                numerator, denominator = raw[0], raw[1]
                if denominator:
                    value = round(numerator / denominator, 6) if metric_id in RATIOS else numerator
                    status = "measured"
                else:
                    reason = "No eligible population at the declared cutoff"
            output.append({
                **definition, "as_of": cutoff, "numerator": numerator,
                "denominator": denominator, "value": value, "status": status,
                "reason": reason, "query": query, "source_counts": source_counts,
                "evidence_rows": evidence_rows, "evidence_total": evidence_total,
            })
        if database_path is not None:
            after_hash = _sha256(database_path)
            if after_hash != source_sha256:
                raise RuntimeError("metric source changed during registry calculation")
        return {"as_of": cutoff, "synthetic": True, "metrics": output,
                "source_sha256": source_sha256,
                "source_binding": "sha256_path" if source_sha256 is not None else "unverified_connection",
                "evidence_limit": MAX_EVIDENCE_ROWS,
                "limitations": "Evidence rows are bounded source samples; source_counts show full source populations. Values describe synthetic records only."}
    finally:
        if owned:
            con.close()


__all__ = ["build_metric_registry"]
