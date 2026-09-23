import json
import sqlite3
import tempfile
import unittest
from pathlib import Path

from milenio.fixtures import make_fixture
from milenio.importers import export_csv
from milenio.scenarios import make_operating_scenario
from milenio.studio_analytics import build_marts
from milenio.studio_input import load_studio_input
from milenio.warehouse import build_warehouse


class StudioInputTests(unittest.TestCase):
    def _csv_snapshot(self, root):
        data = make_fixture()
        for kind, rows in data.items():
            (root / (kind + ".csv")).write_text(export_csv(kind, rows), encoding="utf-8-sig")
        return data

    def test_complete_csv_input_is_valid_and_hash_traced(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            original = self._csv_snapshot(root)
            loaded = load_studio_input(root)
            self.assertEqual(loaded["dataset"], original)
            self.assertEqual(loaded["events"], [])
            self.assertTrue(loaded["manifest"]["history_unknown_when_events_absent"])
            self.assertEqual(len(loaded["manifest"]["input_hashes"]), 25)

    def test_json_events_journeys_and_rejections(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            dataset = make_fixture()
            source = root / "dataset.json"
            source.write_text(json.dumps(dataset), encoding="utf-8")
            events, journeys = root / "events.json", root / "journeys.json"
            events.write_text("[]", encoding="utf-8"); journeys.write_text("[]", encoding="utf-8")
            loaded = load_studio_input(source, events, journeys)
            self.assertTrue(loaded["manifest"]["history_unknown_when_events_absent"])
            dataset["customers"][0]["synthetic"] = False
            source.write_text(json.dumps(dataset), encoding="utf-8")
            with self.assertRaises(ValueError): load_studio_input(source)
            (root / "customers.csv").write_text("id,name,unknown\nX,x,y\n", encoding="utf-8")

    def test_input_files_unchanged_and_empty_process_mart_has_schema(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            data = make_fixture()
            for kind, rows in data.items(): (root / (kind + ".csv")).write_text(export_csv(kind, rows), encoding="utf-8-sig")
            before = (root / "customers.csv").read_bytes()
            load_studio_input(root)
            self.assertEqual(before, (root / "customers.csv").read_bytes())
            db = root / "empty.sqlite"
            build_warehouse(db, data)
            build_marts(db)
            con = sqlite3.connect(db)
            try:
                columns = [row[1] for row in con.execute("PRAGMA table_info(mart_process_waits)")]
                self.assertEqual(columns, ["entity_type", "stage", "intervals", "cases", "total_hours", "mean_interval_hours"])
                self.assertEqual(con.execute("SELECT COUNT(*) FROM mart_process_waits").fetchone()[0], 0)
            finally:
                con.close()


if __name__ == "__main__": unittest.main()
