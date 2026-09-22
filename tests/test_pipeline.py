"""End-to-end contract for the offline analytics deliverable."""
import copy
import json
import sqlite3
import tempfile
import unittest
from pathlib import Path

from milenio.contracts import FIELDS
from milenio.fixtures import make_fixture
from milenio.pipeline import run_pipeline, verify_receipt


class PipelineE2ETests(unittest.TestCase):
    REQUIRED_JSON = (
        "dataset.json",
        "analysis.json",
        "proposals.json",
        "exceptions.json",
        "timeline.json",
        "quality.json",
        "receipt.json",
    )
    REQUIRED_REPORTS = (
        "particulares.md",
        "flotillas.md",
        "gruas.md",
        "administracion.md",
        "informe_ejecutivo.html",
    )

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)

    def tearDown(self):
        self.temp.cleanup()

    def test_demo_build_is_complete_and_reconciled(self):
        output = self.root / "demo"
        receipt = run_pipeline(output)

        self.assertEqual(receipt["status"], "pass")
        self.assertTrue(receipt["synthetic"])
        for name in self.REQUIRED_JSON:
            self.assertTrue((output / name).is_file(), name)
        self.assertTrue((output / "milenio.sqlite").is_file())
        for name in self.REQUIRED_REPORTS:
            self.assertTrue((output / "reports" / name).is_file(), name)

        chart_dir = output / "reports" / "charts"
        charts = list(chart_dir.glob("*.png")) + list(chart_dir.glob("*.svg"))
        self.assertTrue(charts, "the consulting package must include charts under reports/charts")

        dataset = json.loads((output / "dataset.json").read_text(encoding="utf-8"))
        self.assertEqual(set(dataset), set(FIELDS))
        for kind in FIELDS:
            self.assertTrue((output / "csv" / f"{kind}.csv").is_file(), kind)

        quality = json.loads((output / "quality.json").read_text(encoding="utf-8"))
        self.assertEqual(quality["status"], "pass")
        self.assertTrue(quality["synthetic"])
        self.assertTrue(quality["reconciliation"]["ok"])

        proposals = json.loads((output / "proposals.json").read_text(encoding="utf-8"))
        self.assertTrue(proposals)
        ids = {kind: {row["id"] for row in rows} for kind, rows in dataset.items()}
        for proposal in proposals:
            self.assertIs(proposal["approval_required"], True)
            self.assertIs(proposal["external_execution"], False)
            self.assertTrue(proposal["evidence"])
            for evidence in proposal["evidence"]:
                self.assertIn(evidence["entity_id"], ids[evidence["entity_type"]])

        db = sqlite3.connect(output / "milenio.sqlite")
        try:
            stored = db.execute("SELECT COUNT(*) FROM entities").fetchone()[0]
        finally:
            db.close()
        expected = sum(len(rows) for rows in dataset.values())
        self.assertEqual(stored, expected)

        verified = verify_receipt(output)
        self.assertEqual(verified["status"], "pass")
        self.assertEqual(verified["content_sha256"], receipt["content_sha256"])

    def test_invalid_dataset_fails_closed_without_mutating_source(self):
        dataset = make_fixture()
        dataset["customers"][0]["segment"] = "not-a-valid-segment"
        before = copy.deepcopy(dataset)
        output = self.root / "invalid"

        with self.assertRaises(ValueError):
            run_pipeline(output, dataset=dataset)

        self.assertEqual(dataset, before)
        self.assertFalse(output.exists())
        self.assertFalse((output / "receipt.json").exists())

    def test_same_source_has_reproducible_content_digest_and_is_immutable(self):
        dataset = make_fixture()
        before = copy.deepcopy(dataset)

        first = run_pipeline(self.root / "first", dataset=dataset)
        second = run_pipeline(self.root / "second", dataset=dataset)

        self.assertEqual(dataset, before)
        self.assertEqual(first["data_sha256"], second["data_sha256"])
        self.assertEqual(first["content_sha256"], second["content_sha256"])
        self.assertEqual(first["artifacts_sha256"], second["artifacts_sha256"])

    def test_existing_output_is_not_overwritten(self):
        output = self.root / "existing"
        output.mkdir()
        marker = output / "owner-data.txt"
        marker.write_bytes(b"preserve me exactly")
        before = {p.relative_to(output): p.read_bytes() for p in output.rglob("*") if p.is_file()}

        with self.assertRaises(ValueError):
            run_pipeline(output)

        after = {p.relative_to(output): p.read_bytes() for p in output.rglob("*") if p.is_file()}
        self.assertEqual(after, before)


if __name__ == "__main__":
    unittest.main()
