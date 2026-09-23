import hashlib
import json
import os
import tempfile
import unittest
import zipfile
from pathlib import Path
from unittest import mock

import openpyxl

import scripts.package_operating_kit as package
from milenio.client_actions import write_action_workbook


def _seal_studio(directory):
    directory.mkdir()
    (directory / "INICIO.html").write_text('<a href="data.json">Abrir datos</a>', encoding="utf-8")
    (directory / "data.json").write_text('{"synthetic":true}', encoding="utf-8")
    hashes = {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in directory.iterdir()}
    canonical = json.dumps(hashes, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    receipt = {"version": 2, "status": "pass", "synthetic": True,
               "artifacts_sha256": hashes,
               "content_sha256": hashlib.sha256(canonical.encode()).hexdigest()}
    (directory / "receipt.json").write_text(json.dumps(receipt), encoding="utf-8")
    return directory


class OperatingPackageTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.studio = _seal_studio(self.root / "studio")

    def _manifest(self, archive):
        manifest = json.loads(archive.read(package.MANIFEST_NAME))
        self.assertEqual(manifest["publication_status"], "local_candidate")
        self.assertEqual(manifest["reader_entrypoint"], "INICIO.html")
        self.assertEqual(manifest["sealed_studio_path"], "studio")
        self.assertEqual(set(manifest["entries_sha256"]), set(archive.namelist()) - {package.MANIFEST_NAME})
        for name, expected in manifest["entries_sha256"].items():
            self.assertEqual(hashlib.sha256(archive.read(name)).hexdigest(), expected)
        return manifest

    def test_reader_archive_has_root_entrypoint_and_exact_manifest_bytes(self):
        output = self.root / "reader.zip"
        result = package.build(output, self.studio)
        self.assertEqual(result["sha256"], hashlib.sha256(output.read_bytes()).hexdigest())
        with zipfile.ZipFile(output) as archive:
            manifest = self._manifest(archive)
            self.assertIn("INICIO.html", archive.namelist())
            self.assertIn(b'href="studio/INICIO.html"', archive.read("INICIO.html"))
            self.assertEqual(archive.read("studio/INICIO.html"), (self.studio / "INICIO.html").read_bytes())
            self.assertEqual(archive.read("studio/receipt.json"), (self.studio / "receipt.json").read_bytes())
            self.assertIn(package.INTRO_NAME, archive.namelist())
            self.assertNotIn("source/INICIO.html", archive.namelist())
            self.assertFalse(manifest["source_included"])
            self.assertTrue(manifest["synthetic"])
            extracted = self.root / "extracted-reader"
            archive.extractall(extracted)
        self.assertEqual(package.verify_studio(extracted / "studio")["status"], "pass")

    def test_source_layout_is_narrow_and_offline_wheels_match_setup(self):
        for name, data in (("README.md", "readme"), ("PROJECT.md", "project"),
                           ("milenio/module.py", "module"), ("docs/guide.md", "guide"),
                           ("examples/client_data/README.md", "synthetic example"),
                           ("examples/client_data/Acuerdo_de_entrega.xlsx", "unsealed example"),
                           (".github/workflows/verify.yml", "name: verify"),
                           ("docs/private/secret.txt", "do not package"),
                           ("milenio/__pycache__/module.pyc", "cache"),
                           ("artifacts/other/private.json", "private artifact"),
                           (".env", "ENV=private")):
            path = self.root / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(data, encoding="utf-8")
        wheels = self.root / "wheels"
        wheels.mkdir()
        (wheels / "demo-1.0-py3-none-any.whl").write_bytes(b"wheel bytes")
        output = self.root / "full.zip"
        with mock.patch.object(package, "ROOT", self.root):
            package.build(output, self.studio, include_source=True, wheelhouse=wheels)
        with zipfile.ZipFile(output) as archive:
            names = set(archive.namelist())
            manifest = self._manifest(archive)
            self.assertIn("source/milenio/module.py", names)
            self.assertIn("source/README.md", names)
            self.assertIn("source/examples/client_data/README.md", names)
            self.assertNotIn("source/examples/client_data/Acuerdo_de_entrega.xlsx", names)
            self.assertIn("source/artifacts/operating-model-v4/INICIO.html", names)
            self.assertIn("source/artifacts/operating-model-v4/receipt.json", names)
            self.assertIn("source/.runtime/wheels/demo-1.0-py3-none-any.whl", names)
            self.assertNotIn("source/docs/private/secret.txt", names)
            self.assertNotIn("source/milenio/__pycache__/module.pyc", names)
            self.assertNotIn("source/artifacts/other/private.json", names)
            self.assertNotIn("source/.env", names)
            self.assertTrue(manifest["source_included"])
            self.assertTrue(manifest["wheels_included"])
            extracted = self.root / "extracted-full"
            archive.extractall(extracted)
        self.assertEqual(package.verify_studio(extracted / "studio")["status"], "pass")
        self.assertEqual(package.verify_studio(extracted / "source/artifacts/operating-model-v4")["status"], "pass")

    def test_tampered_or_non_synthetic_studio_rejected_without_output(self):
        (self.studio / "data.json").write_text('{"synthetic":false}', encoding="utf-8")
        output = self.root / "tampered.zip"
        with self.assertRaises(ValueError):
            package.build(output, self.studio)
        self.assertFalse(output.exists())
        _seal_studio(self.root / "fresh")
        receipt_path = self.root / "fresh" / "receipt.json"
        receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
        receipt["synthetic"] = False
        receipt_path.write_text(json.dumps(receipt), encoding="utf-8")
        with self.assertRaises(ValueError):
            package.build(output, self.root / "fresh")
        self.assertFalse(output.exists())

    def test_symlink_and_unsafe_archive_paths_rejected(self):
        with self.assertRaisesRegex(ValueError, "unsafe archive path"):
            package._safe_name("source/../private.txt")
        source = self.root / "milenio"
        source.mkdir()
        target = self.root / "outside.py"
        target.write_text("private", encoding="utf-8")
        try:
            os.symlink(target, source / "linked.py")
        except (OSError, NotImplementedError):
            self.skipTest("symlinks unavailable on this Windows runner")
        with mock.patch.object(package, "ROOT", self.root):
            with self.assertRaisesRegex(ValueError, "symlink"):
                package.build(self.root / "symlink.zip", self.studio, include_source=True)
        self.assertFalse((self.root / "symlink.zip").exists())

    def test_client_examples_require_verified_synthetic_receipt_and_wheels_are_flat(self):
        delivery = self.root / "examples" / "client_delivery" / "week"
        delivery.mkdir(parents=True)
        (delivery / "receipt.json").write_text("{}", encoding="utf-8")
        (delivery / "INICIO.html").write_text("sealed", encoding="utf-8")
        metadata = {"snapshot_id": "SYN-001", "as_of": "2026-09-22T00:00:00Z", "synthetic": True}
        decisions = [{"action_id": "A-1", "category": "test", "title": "Revisar ejemplo", "priority": "P2",
                      "owner_role": "Recepción", "why_now": "Dato sintético", "recommended_next_step": "Revisar",
                      "amount_at_risk_cents": None, "evidence": [], "source_ids": ["synthetic:1"]}]
        (delivery / "analysis.json").write_text(json.dumps({"metadata": metadata, "decisions": decisions}), encoding="utf-8")
        write_action_workbook(delivery / "Seguimiento.xlsx", decisions, metadata)
        with mock.patch.object(package, "ROOT", self.root), mock.patch.object(package, "verify_client", return_value={"synthetic": False}):
            with self.assertRaisesRegex(ValueError, "non-synthetic"):
                package.build(self.root / "private.zip", self.studio, include_source=True)
        self.assertFalse((self.root / "private.zip").exists())
        verified_receipt = {"synthetic": True, "artifacts_sha256": {
            name: hashlib.sha256((delivery / name).read_bytes()).hexdigest() for name in ("INICIO.html", "analysis.json")}}
        with mock.patch.object(package, "ROOT", self.root), mock.patch.object(package, "verify_client",
                                                                                  return_value=verified_receipt):
            package.build(self.root / "sealed-only.zip", self.studio, include_source=True)
        with zipfile.ZipFile(self.root / "sealed-only.zip") as archive:
            self.assertIn("source/examples/client_delivery/week/INICIO.html", archive.namelist())
            self.assertIn("source/examples/client_delivery/week/Seguimiento.xlsx", archive.namelist())
        review = openpyxl.load_workbook(delivery / "Seguimiento.xlsx")
        review["Seguimiento"]["L2"] = "Nombre de revisor privado"
        review.save(delivery / "Seguimiento.xlsx")
        review.close()
        with mock.patch.object(package, "ROOT", self.root), mock.patch.object(package, "verify_client",
                                                                                  return_value=verified_receipt):
            with self.assertRaisesRegex(ValueError, "human annotations"):
                package.build(self.root / "annotated.zip", self.studio, include_source=True)
        self.assertFalse((self.root / "annotated.zip").exists())
        write_action_workbook(delivery / "Seguimiento.xlsx", decisions, metadata)
        wheels = self.root / "wheels"
        wheels.mkdir()
        (wheels / "README.txt").write_text("not a wheel", encoding="utf-8")
        with mock.patch.object(package, "ROOT", self.root), mock.patch.object(package, "verify_client", return_value=verified_receipt):
            with self.assertRaisesRegex(ValueError, "flat .whl"):
                package.build(self.root / "bad-wheels.zip", self.studio, include_source=True, wheelhouse=wheels)


if __name__ == "__main__":
    unittest.main()
