import hashlib
import sqlite3
import tempfile
import unittest
from contextlib import closing
from pathlib import Path
from unittest import mock

from milenio.client_actions import REQUIRED_DECISION_FIELDS
from milenio.contracts import DEMO_NOW
from milenio.metric_registry import build_metric_registry
from milenio.operating_cases import build_operating_cases
from milenio.scenarios import make_operating_scenario
from milenio.studio_analytics import build_marts
from milenio.warehouse import build_warehouse


class OperatingCasesTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.database = Path(self.tmp.name) / "warehouse.sqlite"
        scenario = make_operating_scenario()
        build_warehouse(self.database, scenario["dataset"], scenario["events"], scenario["journeys"])
        build_marts(self.database)

    def cases(self):
        return build_operating_cases(self.database, build_metric_registry(self.database))

    def test_source_metric_case_evidence_and_read_only_stability(self):
        before_hash = hashlib.sha256(self.database.read_bytes()).hexdigest()
        first = self.cases()
        second = self.cases()
        self.assertEqual(first, second)
        self.assertEqual(before_hash, hashlib.sha256(self.database.read_bytes()).hexdigest())
        self.assertEqual(first["source_hash"], before_hash)
        self.assertEqual(first["source_hash_kind"], "sqlite_file_sha256")
        self.assertEqual(len(first["input_rows_sha256"]), 64)
        self.assertEqual(first["as_of"], DEMO_NOW)
        self.assertTrue(first["decisions"])
        self.assertEqual(len(first["coverage"]), 33)
        self.assertEqual(len({d["action_id"] for d in first["decisions"]}), len(first["decisions"]))
        coverage = {item["table"]: item for item in first["coverage"]}
        self.assertEqual(coverage["work_orders"]["scanned_rows"], 170)
        self.assertEqual(coverage["invoices"]["scanned_rows"], 164)
        self.assertEqual(coverage["mart_inventory"]["scanned_rows"], 6)
        self.assertEqual(sum(item["triggered_cases"] for item in first["coverage"]), len(first["decisions"]))
        metrics = {m["metric_id"]: m for m in build_metric_registry(self.database)["metrics"]}
        with closing(sqlite3.connect(self.database)) as con:
            for case in first["decisions"]:
                self.assertTrue(set(REQUIRED_DECISION_FIELDS) <= case.keys())
                self.assertTrue(case["metric_ids"])
                self.assertTrue(case["process_ids"])
                self.assertEqual(case["source_hash"], first["source_hash"])
                self.assertEqual(case["source_hash_kind"], "sqlite_file_sha256")
                self.assertFalse(case["external_business_action"])
                self.assertTrue(all(mid in metrics for mid in case["metric_ids"]))
                self.assertEqual(case["source_ids"], list(dict.fromkeys(
                    f"{r['table']}:{r['record_id']}" for r in case["evidence"])))
                for ref in case["evidence"]:
                    key = "part_id" if ref["table"] == "mart_inventory" else "work_order_id" if ref["table"] == "mart_service_journey" else "id"
                    row = con.execute(f'SELECT "{ref["field"]}", version FROM "{ref["table"]}" WHERE "{key}"=?',
                                      (ref["record_id"],)).fetchone() if ref["table"] not in {"mart_inventory", "mart_service_journey"} else con.execute(
                                          f'SELECT "{ref["field"]}" FROM "{ref["table"]}" WHERE "{key}"=?', (ref["record_id"],)).fetchone()
                    self.assertIsNotNone(row)
                    self.assertEqual(ref["value"], row[0])
                    self.assertEqual(ref["version"], None if len(row) == 1 else row[1])
        self.assertIn("M-AR-OVERDUE", next(d for d in first["decisions"] if d["category"] == "overdue_ar")["metric_ids"])
        self.assertIn("M-STOCK-REORDER", next(d for d in first["decisions"] if d["category"] == "reorder_review")["metric_ids"])

    def test_paid_invoice_and_status_only_maintenance_never_trigger(self):
        result = self.cases()
        overdue = {d["source_ids"][0] for d in result["decisions"] if d["category"] == "overdue_ar"}
        maintenance = {d["source_ids"][0] for d in result["decisions"] if d["category"] == "maintenance_due"}
        self.assertNotIn("invoices:INV-003", overdue)  # Fully paid.
        self.assertNotIn("maintenance:M-002", maintenance)  # 'due' label alone is insufficient.
        self.assertNotIn("maintenance:M-003", maintenance)
        with closing(sqlite3.connect(self.database)) as con:
            con.execute("UPDATE maintenance SET due_at='2026-09-20T00:00:00Z',version=version+1 WHERE id='M-002'")
            con.commit()
        later = self.cases()
        changed = next(d for d in later["decisions"] if d["category"] == "maintenance_due" and "maintenance:M-002" in d["source_ids"])
        self.assertIn("vehicles:V-010", changed["source_ids"])
        self.assertNotEqual(result["source_hash"], later["source_hash"])

    def test_ids_stable_across_row_versions_and_tow_requires_human_review(self):
        before = self.cases()
        target = next(d for d in before["decisions"] if d["category"] == "tow_refs_review")
        tow_id = target["source_ids"][0].split(":", 1)[1]
        with closing(sqlite3.connect(self.database)) as con:
            con.execute("UPDATE tows SET version=version+1 WHERE id=?", (tow_id,))
            con.commit()
        after = self.cases()
        same = next(d for d in after["decisions"] if d["category"] == "tow_refs_review" and f"tows:{tow_id}" in d["source_ids"])
        self.assertEqual(target["action_id"], same["action_id"])
        self.assertNotEqual(target["source_hash"], same["source_hash"])
        self.assertIn("seguridad", same["recommended_next_step"].lower())
        self.assertFalse(same["external_business_action"])

    def test_due_date_mileage_sla_and_followup_triggers(self):
        with closing(sqlite3.connect(self.database)) as con:
            con.execute("UPDATE vehicles SET odometer_km=due_km FROM maintenance WHERE vehicles.id=maintenance.vehicle_id AND maintenance.id='M-003'")
            con.execute("UPDATE work_orders SET contract_id='CT-001' WHERE id='WO-010'")
            con.execute("UPDATE mart_service_journey SET contract_id='CT-001',sla_status='at_risk' WHERE work_order_id='WO-010'")
            con.execute("UPDATE opportunities SET follow_up_at='2026-09-20T00:00:00Z' WHERE id='OP-001'")
            con.execute("UPDATE work_orders SET status='ready',due_at='2026-09-20T00:00:00Z' WHERE id='WO-002'")
            con.commit()
        cases = self.cases()["decisions"]
        self.assertTrue(any(d["category"] == "maintenance_due" and "maintenance:M-003" in d["source_ids"] for d in cases))
        self.assertTrue(any(d["category"] == "fleet_sla_risk" and "contracts:CT-001" in d["source_ids"] for d in cases))
        self.assertTrue(any(d["category"] == "opportunity_followup" and "opportunities:OP-001" in d["source_ids"] for d in cases))
        self.assertTrue(any(d["category"] == "ready" and "work_orders:WO-002" in d["source_ids"] for d in cases))

    def test_missing_source_is_unknown_not_zero(self):
        with closing(sqlite3.connect(self.database)) as con:
            con.execute("DROP TABLE quotes")
            con.commit()
        result = self.cases()
        quotes = next(c for c in result["coverage"] if c["table"] == "quotes")
        self.assertEqual(quotes["status"], "unknown_missing_source")
        self.assertIsNone(quotes["scanned_rows"])
        self.assertIsNone(quotes["triggered_cases"])
        self.assertFalse(any(d["category"] == "quote_expired" for d in result["decisions"]))

    def test_stale_metric_registry_and_mid_read_change_are_rejected(self):
        registry = build_metric_registry(self.database)
        with closing(sqlite3.connect(self.database)) as con:
            con.execute("UPDATE leads SET version=version+1 WHERE id='L-001'")
            con.commit()
        with self.assertRaisesRegex(ValueError, "does not match"):
            build_operating_cases(self.database, registry)
        fresh = build_metric_registry(self.database)
        with mock.patch("milenio.operating_cases._file_sha256", side_effect=[fresh["source_sha256"], "0" * 64]):
            with self.assertRaisesRegex(RuntimeError, "changed during"):
                build_operating_cases(self.database, fresh)

    def test_connection_identity_unverified_and_non_synthetic_rows_rejected(self):
        with closing(sqlite3.connect(self.database)) as con:
            con.execute("PRAGMA query_only=ON")
            registry = build_metric_registry(con)
            cases = build_operating_cases(con, registry)
            self.assertIsNone(cases["source_hash"])
            self.assertEqual(cases["source_hash_kind"], "unverified_connection")
            self.assertTrue(cases["input_rows_sha256"])
            self.assertTrue(all(d["source_hash"] is None and d["source_hash_kind"] == "unverified_connection"
                                for d in cases["decisions"]))
            self.assertEqual(con.execute("PRAGMA query_only").fetchone()[0], 1)
        with closing(sqlite3.connect(self.database)) as con:
            con.execute("PRAGMA ignore_check_constraints=ON")
            con.execute("UPDATE leads SET synthetic=0 WHERE id='L-001'")
            con.commit()
        with self.assertRaisesRegex(ValueError, "Non-synthetic row"):
            self.cases()


if __name__ == "__main__":
    unittest.main()
