import sqlite3
import tempfile
import unittest
from pathlib import Path

from milenio.scenarios import make_operating_scenario
from milenio.fixtures import make_fixture
from milenio.studio_analytics import MART_SCHEMAS, build_marts
from milenio.warehouse import build_warehouse


class WarehouseTests(unittest.TestCase):
    def test_all_six_marts_exist_with_stable_types_when_population_is_empty(self):
        with tempfile.TemporaryDirectory() as temp:
            data = make_fixture()
            data["payments"] = []
            data["invoices"] = []
            path = Path(temp) / "warehouse.sqlite"
            build_warehouse(path, data)
            analysis = build_marts(path)
            self.assertEqual(analysis["marts"]["mart_receivables"], [])
            connection = sqlite3.connect(path)
            try:
                names = {row[0] for row in connection.execute("SELECT name FROM sqlite_master WHERE type='table'")}
                self.assertTrue(set(MART_SCHEMAS).issubset(names))
                for name, expected in MART_SCHEMAS.items():
                    observed = [(row[1], row[2]) for row in connection.execute(f'PRAGMA table_info("{name}")')]
                    self.assertEqual(observed, expected)
                self.assertEqual(connection.execute('SELECT COUNT(*) FROM mart_receivables').fetchone()[0], 0)
                self.assertEqual(connection.execute('SELECT COUNT(*) FROM mart_process_waits').fetchone()[0], 0)
            finally:
                connection.close()

    def test_physical_tables_catalog_and_fk_enforcement(self):
        with tempfile.TemporaryDirectory() as temp:
            scenario = make_operating_scenario()
            path = Path(temp) / "warehouse.sqlite"
            catalog = build_warehouse(path, scenario["dataset"], scenario["events"], scenario["journeys"])
            connection = sqlite3.connect(path)
            connection.execute("PRAGMA foreign_keys=ON")
            names = {row[0] for row in connection.execute("SELECT name FROM sqlite_master WHERE type='table'")}
            self.assertEqual(set(scenario["dataset"]) | {"lifecycle_events", "journey_links"}, names)
            self.assertEqual(connection.execute("PRAGMA foreign_key_check").fetchall(), [])
            with self.assertRaises(sqlite3.IntegrityError):
                connection.execute("INSERT INTO journey_links VALUES ('bad','missing','missing','missing','missing',1)")
            self.assertEqual(catalog["counts"]["work_orders"], 170)
            self.assertTrue(Path(catalog["schema_sql"]).exists())
            connection.close()

    def test_reproducible_scenario_and_meaningful_distribution(self):
        first = make_operating_scenario()
        second = make_operating_scenario()
        self.assertEqual(first["manifest"], second["manifest"])
        self.assertEqual(first["dataset"], second["dataset"])
        self.assertGreaterEqual(len(first["dataset"]["work_orders"]), 150)
        self.assertEqual(len(first["journeys"]), 160)
        self.assertGreater(len(first["dataset"]["payments"]), 100)
        self.assertGreater(len(first["events"]), 1000)
        self.assertGreater(len({r["amount_cents"] for r in first["dataset"]["invoices"]}), 5)
        self.assertTrue(any(e["to_state"] == "waiting_parts" for e in first["events"]))
        self.assertTrue(any(e["to_state"] == "rework" for e in first["events"]))

    def test_illegal_history_and_journey_ownership_fail_closed(self):
        scenario = make_operating_scenario()
        bad_event = dict(scenario["events"][1], to_state="delivered")
        with tempfile.TemporaryDirectory() as temp:
            with self.assertRaises(ValueError):
                build_warehouse(Path(temp) / "bad-event.sqlite", scenario["dataset"], [scenario["events"][0], bad_event], scenario["journeys"])
            bad_journey = dict(scenario["journeys"][0], quote_id="Q-002")
            with self.assertRaises(ValueError):
                build_warehouse(Path(temp) / "bad-journey.sqlite", scenario["dataset"], scenario["events"], [bad_journey])

    def test_sql_checks_reject_invalid_state_and_null_primary_key(self):
        with tempfile.TemporaryDirectory() as temp:
            scenario = make_operating_scenario()
            path = Path(temp) / "warehouse.sqlite"
            build_warehouse(path, scenario["dataset"], scenario["events"], scenario["journeys"])
            connection = sqlite3.connect(path)
            with self.assertRaises(sqlite3.IntegrityError):
                connection.execute("INSERT INTO customers(id,version,synthetic,created_at,updated_at,name,segment,consent) VALUES ('X',1,1,'x','x','x','invalid',1)")
            with self.assertRaises(sqlite3.IntegrityError):
                connection.execute("INSERT INTO customers(id,version,synthetic,created_at,updated_at,name,segment,consent) VALUES (NULL,1,1,'x','x','x','particular',1)")
            connection.close()


if __name__ == "__main__":
    unittest.main()
