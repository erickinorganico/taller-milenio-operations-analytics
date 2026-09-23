import hashlib
import json
import sqlite3
import tempfile
import unittest
from contextlib import closing
from pathlib import Path

from milenio.metric_registry import build_metric_registry
from milenio.scenarios import make_operating_scenario
from milenio.source_catalog import build_source_catalog
from milenio.studio_analytics import build_marts
from milenio.warehouse import build_warehouse


class SourceCatalogTests(unittest.TestCase):
    def _build(self, root):
        scenario = make_operating_scenario()
        database = root / "warehouse.sqlite"
        build_warehouse(database, scenario["dataset"], scenario["events"], scenario["journeys"])
        build_marts(database)
        return database

    def test_complete_physical_and_derived_rows_are_read_only_and_linked(self):
        with tempfile.TemporaryDirectory() as temp:
            database = self._build(Path(temp))
            before = hashlib.sha256(database.read_bytes()).hexdigest()
            metrics = build_metric_registry(database)
            catalog = build_source_catalog(database, metrics)
            after = hashlib.sha256(database.read_bytes()).hexdigest()
            self.assertEqual(before, after)
            self.assertEqual((catalog["physical_source_tables"], catalog["derived_marts"], len(catalog["tables"])), (27, 6, 33))
            tables = {table["name"]: table for table in catalog["tables"]}
            self.assertEqual(len(tables), 33)
            self.assertEqual(tables["work_orders"]["row_count"], 170)
            self.assertEqual(len(tables["work_orders"]["rows"]), 170)
            self.assertEqual(tables["work_orders"]["primary_key"], ["id"])
            self.assertEqual(tables["lifecycle_events"]["primary_key"], ["event_id"])
            self.assertEqual(tables["mart_process_waits"]["primary_key"], [])
            self.assertEqual(tables["mart_process_waits"]["logical_key"], ["entity_type", "stage"])
            self.assertIn("M-SERVICE-CYCLE", tables["work_orders"]["metric_ids"])
            self.assertIn("M-SERVICE-CYCLE", tables["mart_service_journey"]["metric_ids"])
            self.assertIn("M-STOCK-AVAILABLE", tables["mart_inventory"]["metric_ids"])
            self.assertEqual(tables["work_orders"]["source_file"], "tables/work_orders.csv")
            self.assertEqual(tables["work_orders"]["source_status"], "synthetic_example")
            self.assertEqual(tables["mart_inventory"]["source_status"], "derived_from_synthetic")
            self.assertEqual(tables["work_orders"]["owner_status"], "proposed_unvalidated")
            self.assertEqual(tables["work_orders"]["rows"], sorted(tables["work_orders"]["rows"], key=lambda r: r["id"]))
            for table in catalog["tables"]:
                self.assertEqual(table["row_count"], len(table["rows"]))
                self.assertTrue(table["fields"])
                self.assertTrue(all("null_count" in field and "description" in field for field in table["fields"]))
                json.dumps(table, ensure_ascii=False, allow_nan=False)

    def test_relationships_are_actual_sqlite_foreign_keys(self):
        with tempfile.TemporaryDirectory() as temp:
            database = self._build(Path(temp))
            catalog = build_source_catalog(database, build_metric_registry(database))
            tables = {table["name"]: table for table in catalog["tables"]}
            links = tables["work_orders"]["relationships"]
            self.assertTrue(any(link["target_table"] == "customers" and link["from_fields"] == ["customer_id"] for link in links))
            self.assertTrue(any(link["target_table"] == "vehicles" and link["from_fields"] == ["vehicle_id"] for link in links))
            self.assertEqual(tables["mart_service_journey"]["relationships"], [])
            with closing(sqlite3.connect(database)) as connection:
                expected = len(connection.execute('PRAGMA foreign_key_list("work_orders")').fetchall())
            self.assertEqual(len(links), expected)


if __name__ == "__main__":
    unittest.main()
