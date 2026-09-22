import unittest

from milenio.contracts import DEMO_NOW, FIELDS
from milenio.domain import validate_dataset
from milenio.fixtures import make_fixture
from milenio.importers import apply_csv, export_csv, preview_csv
from milenio.reports import bootstrap
from milenio.reports import AGENTS
from milenio.storage import Store


class FixtureTests(unittest.TestCase):
    def test_is_deterministic_and_complete(self):
        first, second = make_fixture(42), make_fixture(42)
        self.assertEqual(first, second)
        self.assertEqual(set(first), set(FIELDS))
        self.assertGreaterEqual(len(first["customers"]), 8)
        self.assertGreaterEqual(len(first["vehicles"]), 12)
        self.assertGreaterEqual(len(first["work_orders"]), 10)
        self.assertGreaterEqual(len(first["tows"]), 5)
        for kind, rows in first.items():
            for row in rows:
                self.assertTrue(row["synthetic"])
                self.assertEqual(row["version"], 1)
                self.assertEqual(row["created_at"], DEMO_NOW)
                self.assertEqual(set(FIELDS[kind]) - set(row), set())
                self.assertEqual(row["id"], row["id"].strip())

    def test_references_resolve(self):
        data = make_fixture()
        ids = {kind: {row["id"] for row in rows} for kind, rows in data.items()}
        for kind, rows in data.items():
            for row in rows:
                for field, spec in FIELDS[kind].items():
                    if spec.startswith("ref:") and row[field] is not None:
                        target = spec[4:].rstrip("?")
                        self.assertIn(row[field], ids[target], (kind, row["id"], field))

    def test_source_proposals_have_full_matching_evidence(self):
        data = make_fixture()
        records = {kind: {row["id"]: row for row in rows} for kind, rows in data.items()}
        for proposal in data["proposals"]:
            self.assertIn(proposal["agent"], AGENTS)
            for evidence in proposal["evidence"]:
                source = records[evidence["entity_type"]][evidence["entity_id"]]
                self.assertIn(evidence["field"], FIELDS[evidence["entity_type"]])
                self.assertEqual(evidence["value"], source[evidence["field"]])
                self.assertEqual(evidence["version"], source["version"])

    def test_full_domain_and_store_bootstrap(self):
        data = make_fixture()
        validate_dataset(data)
        store = Store()
        store.initialize(data)
        packet = bootstrap(store)
        self.assertTrue(packet["reconciliation"]["ok"])
        self.assertEqual(len(packet["data"]), len(FIELDS))


class ImportTests(unittest.TestCase):
    HEADER = "id,name,segment,consent,contact,synthetic\n"

    def test_bom_and_strict_values(self):
        csv_text = "\ufeff" + self.HEADER + "C-NEW,Ana,particular,true,ana@example.test,true\n"
        result = preview_csv("customers", csv_text)
        self.assertTrue(result["ok"], result)
        self.assertEqual(result["rows"][0]["consent"], True)

    def test_domain_ranges_and_header_only_are_rejected(self):
        self.assertFalse(preview_csv("customers", self.HEADER)["ok"])
        # Customers have no numeric fields; a vehicle negative odometer proves
        # preview delegates range checks to the domain validator.
        vehicle = "id,customer_id,label,plate,odometer_km,synthetic\nV-NEG,C-001,Demo,DEMO-NEG,-1,true\n"
        self.assertFalse(preview_csv("vehicles", vehicle)["ok"])

    def test_attack_and_malformed_rows_are_atomic(self):
        text = self.HEADER + "C-NEW,=HYPERLINK(\"x\"),particular,true,x@y.test,true\n" + "C-NEW,Bob,particular,yes,x@y.test,true\n"
        result = preview_csv("customers", text)
        self.assertFalse(result["ok"])
        self.assertEqual(result["rows"], [])
        store = {"customers": make_fixture()["customers"]}
        applied = apply_csv(store, "customers", text)
        self.assertFalse(applied["ok"])
        self.assertEqual(len(store["customers"]), 10)

    def test_unknown_columns_and_duplicate_ids(self):
        text = self.HEADER.replace("contact", "contact,secret") + "C-NEW,Ana,particular,true,x@y.test,boom,true\nC-NEW,Bob,particular,true,x@y.test,boom,true\n"
        result = preview_csv("customers", text)
        self.assertFalse(result["ok"])
        self.assertTrue(any(e["field"] == "secret" for e in result["errors"]))
        self.assertTrue(any("duplicate" in e["error"] for e in result["errors"]))

    def test_export_neutralizes_formula_text(self):
        output = export_csv("customers", [{"id": "C-X", "name": "=2+2", "segment": "particular", "consent": True, "contact": "@x", "synthetic": True}])
        self.assertIn("'=2+2", output)
        self.assertIn("'@x", output)

    def test_store_import_is_audited_and_atomic(self):
        store = Store()
        store.initialize(make_fixture())
        valid = self.HEADER + "C-IMPORT,Ana,particular,true,ana@example.test,true\n"
        applied = apply_csv(store, "customers", valid)
        self.assertTrue(applied["ok"], applied)
        revision = store.revision()
        invalid = self.HEADER + "C-BAD,Bad,particular,yes,bad@example.test,true\n"
        rejected = apply_csv(store, "customers", invalid)
        self.assertFalse(rejected["ok"])
        self.assertEqual(store.revision(), revision)
        self.assertIsNone(store.get("customers", "C-BAD"))


if __name__ == "__main__":
    unittest.main()
