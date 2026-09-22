import sqlite3
import tempfile
import unittest
import zipfile
from pathlib import Path

from milenio.scenarios import make_operating_scenario
from milenio.studio_analytics import build_marts
from milenio.warehouse import build_warehouse
from milenio.workbook import build_workbook


class WorkbookTests(unittest.TestCase):
    def test_workbook_tables_formulas_and_source_separation(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            scenario = make_operating_scenario()
            db = root / "warehouse.sqlite"
            build_warehouse(db, scenario["dataset"], scenario["events"], scenario["journeys"])
            analysis = build_marts(db)
            agents = [{"id": "demo-agent", "description": "Synthetic"}]
            processes = [{"process_id": "demo-process", "title": "Synthetic process"}]
            output = root / "analysis.xlsx"
            result = build_workbook(db, output, analysis["summary"], agents, processes)
            self.assertEqual(result["formula_cells"], 6)
            self.assertGreaterEqual(result["source_tables"], 33)
            self.assertTrue(output.exists())
            with zipfile.ZipFile(output) as archive:
                workbook_xml = archive.read("xl/workbook.xml").decode("utf-8")
                self.assertIn("INICIO", workbook_xml)
                self.assertGreaterEqual(workbook_xml.count("<sheet "), result["worksheets"])
                self.assertTrue(any(name.startswith("xl/tables/table") for name in archive.namelist()))
                self.assertFalse(any(b"#REF!" in archive.read(name) for name in archive.namelist() if name.endswith(".xml")))

            con = sqlite3.connect(db)
            self.assertEqual(con.execute("SELECT COUNT(*) FROM mart_daily_operations").fetchone()[0], len(analysis["marts"]["mart_daily_operations"]))
            con.close()


if __name__ == "__main__":
    unittest.main()
