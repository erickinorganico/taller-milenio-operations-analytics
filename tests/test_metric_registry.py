import json
import hashlib
import sqlite3
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from milenio.contracts import DEMO_NOW
from milenio.fixtures import make_fixture
from milenio.metric_registry import build_metric_registry
from milenio.scenarios import make_operating_scenario
from milenio.studio_analytics import build_marts
from milenio.warehouse import build_warehouse


class MetricRegistryTests(unittest.TestCase):
    def test_all_contract_ids_measured_or_explicitly_unknown_with_bounded_evidence(self):
        with tempfile.TemporaryDirectory() as tmp:
            scenario = make_operating_scenario()
            database = Path(tmp) / "warehouse.sqlite"
            build_warehouse(database, scenario["dataset"], scenario["events"], scenario["journeys"])
            build_marts(database)
            result = build_metric_registry(database)
            metrics = {m["metric_id"]: m for m in result["metrics"]}
            definitions = json.loads((Path(__file__).resolve().parent.parent / "contracts" / "metric_registry.json").read_text(encoding="utf-8"))
            self.assertEqual(set(metrics), {m["metric_id"] for m in definitions["metrics"]})
            self.assertEqual(len(metrics), 31)
            self.assertEqual(result["as_of"], DEMO_NOW)
            self.assertEqual(hashlib.sha256(database.read_bytes()).hexdigest(), result["source_sha256"])
            self.assertEqual("sha256_path", result["source_binding"])
            self.assertEqual(metrics["M-AR-RECEIVABLE"]["value"], 3_901_250)
            self.assertEqual(metrics["M-SERVICE-CYCLE"]["numerator"], 160)
            self.assertEqual(metrics["M-SERVICE-CYCLE"]["denominator"], 162)
            self.assertEqual(metrics["M-WEEKLY-EXCEPTIONS"]["status"], "unknown")
            for metric in metrics.values():
                self.assertIn(metric["status"], {"measured", "unknown"})
                self.assertLessEqual(len(metric["evidence_rows"]), 12)
                self.assertEqual(metric["evidence_total"], sum(metric["source_counts"].values()))
                if metric["status"] == "unknown":
                    self.assertIsNone(metric["value"])
                    self.assertTrue(metric["reason"])
                else:
                    self.assertIsNotNone(metric["query"])
            sample = metrics["M-FIN-INVOICED"]["evidence_rows"][0]
            self.assertEqual(sample["table"], "invoices")
            self.assertIn("amount_cents", sample["fields"])

    def test_imported_snapshot_does_not_measure_missing_history_or_attribution(self):
        with tempfile.TemporaryDirectory() as tmp:
            database = Path(tmp) / "warehouse.sqlite"
            build_warehouse(database, make_fixture())
            analysis = build_marts(database)
            metrics = {m["metric_id"]: m for m in build_metric_registry(database)["metrics"]}
            self.assertEqual(metrics["M-SERVICE-CYCLE"]["status"], "unknown")
            self.assertEqual(metrics["M-B2C-QUOTE-MATCH"]["status"], "unknown")
            self.assertEqual(metrics["M-PROCESS-WAIT"]["status"], "unknown")
            delivered = [r for r in analysis["marts"]["mart_service_journey"] if r["status"] == "delivered"]
            self.assertTrue(delivered)
            self.assertTrue(all(r["cycle_hours"] is None for r in delivered))
            self.assertIsNone(analysis["summary"]["cycle_p50_hours"])
            self.assertIsNone(analysis["summary"]["cycle_p90_hours"])

    def test_caller_connection_is_preserved_and_cutoff_is_fixed(self):
        with tempfile.TemporaryDirectory() as tmp:
            scenario = make_operating_scenario()
            database = Path(tmp) / "warehouse.sqlite"
            build_warehouse(database, scenario["dataset"], scenario["events"], scenario["journeys"])
            build_marts(database)
            connection = sqlite3.connect(database)
            try:
                connection.execute("PRAGMA query_only=ON")
                result = build_metric_registry(connection)
                self.assertEqual(len(result["metrics"]), 31)
                self.assertIsNone(result["source_sha256"])
                self.assertEqual("unverified_connection", result["source_binding"])
                self.assertEqual(connection.execute("PRAGMA query_only").fetchone()[0], 1)
                self.assertEqual(connection.execute("SELECT COUNT(*) FROM work_orders").fetchone()[0], 170)
            finally:
                connection.close()
            with self.assertRaises(ValueError):
                build_metric_registry(database, "2026-01-01T00:00:00Z")

    def test_path_source_change_during_calculation_fails_closed(self):
        with tempfile.TemporaryDirectory() as tmp:
            scenario = make_operating_scenario()
            database = Path(tmp) / "warehouse.sqlite"
            build_warehouse(database, scenario["dataset"], scenario["events"], scenario["journeys"])
            build_marts(database)
            import milenio.metric_registry as metric_registry_module
            original_hash = hashlib.sha256(database.read_bytes()).hexdigest()
            with patch.object(metric_registry_module, "_sha256", side_effect=[original_hash, "0" * 64]):
                with self.assertRaisesRegex(RuntimeError, "source changed"):
                    build_metric_registry(database)


if __name__ == "__main__":
    unittest.main()
