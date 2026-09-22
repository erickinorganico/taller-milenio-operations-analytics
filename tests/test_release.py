import json
import tempfile
import unittest
import zipfile
from pathlib import Path

import hashlib
import os
import subprocess
import sys
from unittest.mock import patch

import scripts.package_release as package_release
from scripts.package_release import build


class ReleaseTests(unittest.TestCase):
    def _bundle(self, root):
        bundle = root / "bundle"
        bundle.mkdir()
        payload = bundle / "dataset.json"
        payload.write_text('{"synthetic": true}\n', encoding="utf-8")
        hashes = {"dataset.json": hashlib.sha256(payload.read_bytes()).hexdigest()}
        receipt = {"status": "pass", "synthetic": True, "artifacts_sha256": hashes,
                   "content_sha256": hashlib.sha256(json.dumps(hashes, sort_keys=True, separators=(",", ":")).encode()).hexdigest()}
        (bundle / "receipt.json").write_text(json.dumps(receipt), encoding="utf-8")
        return bundle

    def _studio_bundle(self, root):
        bundle = root / "studio"
        bundle.mkdir()
        dossier = bundle / "DOSSIER.html"
        dossier.write_text("<h1>Sintético</h1>\n", encoding="utf-8")
        hashes = {"DOSSIER.html": hashlib.sha256(dossier.read_bytes()).hexdigest()}
        receipt = {"version": 2, "status": "pass", "synthetic": True,
                   "artifacts_sha256": hashes,
                   "content_sha256": hashlib.sha256(json.dumps(hashes, sort_keys=True, separators=(",", ":")).encode()).hexdigest()}
        (bundle / "receipt.json").write_text(json.dumps(receipt), encoding="utf-8")
        return bundle

    def test_archive_excludes_private_and_git_and_includes_verified_bundle(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            bundle = self._bundle(root)
            output = root / "release.zip"
            result = build(output, bundle=bundle)
            self.assertTrue(result["bundle_verified"])
            with zipfile.ZipFile(output) as archive:
                names = archive.namelist()
            self.assertIn("source/artifacts/demo/receipt.json", names)
            self.assertIn("RELEASE-MANIFEST.json", names)
            self.assertFalse(any(any(part in {".git", ".venv", ".workbench", "private", "dist"} for part in Path(name).parts) for name in names))

    def test_tampered_bundle_receipt_is_rejected(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            bundle = self._bundle(root)
            receipt_path = bundle / "receipt.json"
            receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
            receipt["artifacts_sha256"]["dataset.json"] = "0" * 64
            receipt_path.write_text(json.dumps(receipt), encoding="utf-8")
            with self.assertRaises(ValueError):
                build(root / "release.zip", bundle=bundle)

    def test_offline_wheels_use_setup_layout_and_non_wheels_reject(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            wheelhouse = root / "wheels"
            wheelhouse.mkdir()
            (wheelhouse / "demo-1.0-py3-none-any.whl").write_bytes(b"wheel")
            output = root / "release.zip"
            build(output, wheelhouse=wheelhouse)
            with zipfile.ZipFile(output) as archive:
                self.assertIn("source/.runtime/wheels/demo-1.0-py3-none-any.whl", archive.namelist())
            (wheelhouse / "README.txt").write_text("reject", encoding="utf-8")
            with self.assertRaises(ValueError):
                build(root / "reject.zip", wheelhouse=wheelhouse)

    def test_symlink_inputs_reject_when_platform_allows_symlinks(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            wheelhouse = root / "wheels"
            wheelhouse.mkdir()
            target = root / "outside.whl"
            target.write_bytes(b"wheel")
            try:
                os.symlink(target, wheelhouse / "linked.whl")
            except (OSError, NotImplementedError):
                self.skipTest("symlinks unavailable on this Windows runner")
            with self.assertRaises(ValueError):
                build(root / "reject.zip", wheelhouse=wheelhouse)

    def test_extracted_source_uses_manifest_without_git(self):
        with tempfile.TemporaryDirectory() as temp:
            archive_root = Path(temp)
            source = archive_root / "source"
            source.mkdir()
            tracked = source / "README.md"
            tracked.write_text("synthetic release\n", encoding="utf-8")
            name = "source/README.md"
            manifest = {"format": 1, "entries_sha256": {name: hashlib.sha256(tracked.read_bytes()).hexdigest()}}
            (archive_root / "RELEASE-MANIFEST.json").write_text(json.dumps(manifest), encoding="utf-8")
            original = package_release.ROOT
            try:
                package_release.ROOT = source / '..' / 'source'
                recovered = package_release._tracked()
                self.assertEqual(recovered, [tracked.resolve()])
            finally:
                package_release.ROOT = original

    def test_cli_smoke_runs_from_project_root(self):
        with tempfile.TemporaryDirectory() as temp:
            output = Path(temp) / "release.zip"
            completed = subprocess.run([sys.executable, "scripts/package_release.py", "--output", str(output)], cwd=package_release.ROOT, capture_output=True, text=True)
            self.assertEqual(completed.returncode, 0, completed.stdout + completed.stderr)
            self.assertTrue(output.is_file())

    def test_nested_checkout_root_mismatch_uses_manifest_fallback(self):
        with tempfile.TemporaryDirectory() as temp:
            archive_root = Path(temp)
            source = archive_root / "source"
            source.mkdir()
            tracked = source / "README.md"
            tracked.write_text("synthetic release\n", encoding="utf-8")
            name = "source/README.md"
            manifest = {"format": 1, "entries_sha256": {name: hashlib.sha256(tracked.read_bytes()).hexdigest()}}
            (archive_root / "RELEASE-MANIFEST.json").write_text(json.dumps(manifest), encoding="utf-8")
            original = package_release.ROOT
            try:
                package_release.ROOT = source
                root_result = subprocess.CompletedProcess([], 0, stdout=str(archive_root / "parent-repo") + "\n", stderr="")
                with patch.object(package_release.subprocess, "run", side_effect=[root_result, subprocess.CalledProcessError(128, "git")]):
                    recovered = package_release._tracked()
                self.assertEqual(recovered, [tracked.resolve()])
            finally:
                package_release.ROOT = original

    def test_explicit_bundle_and_wheelhouse_replace_entire_tracked_prefixes(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            source = root / 'source'
            source.mkdir()
            tracked = []
            for relative in ('artifacts/demo/dataset.json', 'artifacts/demo/obsolete.json',
                             '.runtime/wheels/demo-1.0-py3-none-any.whl', '.runtime/wheels/obsolete.whl'):
                path = source / relative
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_bytes(b'old tracked bytes')
                tracked.append(path)
            bundle = self._bundle(root)
            wheelhouse = root / 'wheels'
            wheelhouse.mkdir()
            wheel_name = 'demo-1.0-py3-none-any.whl'
            (wheelhouse / wheel_name).write_bytes(b'explicit wheelhouse bytes')
            output = root / 'output' / 'release.zip'
            with patch.object(package_release, 'ROOT', source), patch.object(package_release, '_tracked', return_value=tracked):
                build(output, bundle=bundle, wheelhouse=wheelhouse)
            with zipfile.ZipFile(output) as archive:
                self.assertEqual(archive.read('source/artifacts/demo/dataset.json'), (bundle / 'dataset.json').read_bytes())
                self.assertEqual(archive.read('source/.runtime/wheels/' + wheel_name), b'explicit wheelhouse bytes')
                self.assertNotIn('source/artifacts/demo/obsolete.json', archive.namelist())
                self.assertNotIn('source/.runtime/wheels/obsolete.whl', archive.namelist())
                receipt = json.loads(archive.read('source/artifacts/demo/receipt.json'))
                actual = hashlib.sha256(archive.read('source/artifacts/demo/dataset.json')).hexdigest()
                self.assertEqual(actual, receipt['artifacts_sha256']['dataset.json'])

    def test_explicit_studio_bundle_uses_v2_path_and_replaces_tracked_prefix(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            source = root / "source"
            source.mkdir()
            tracked_current = source / "artifacts" / "workbench-v2" / "receipt.json"
            tracked_old = source / "artifacts" / "workbench-v2" / "obsolete.txt"
            for path in (tracked_current, tracked_old):
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text("tracked old", encoding="utf-8")
            studio = self._studio_bundle(root)
            output = root / "output" / "release.zip"
            with patch.object(package_release, "ROOT", source), patch.object(package_release, "_tracked", return_value=[tracked_current, tracked_old]):
                result = build(output, studio_bundle=studio)
            self.assertTrue(result["studio_bundle_verified"])
            with zipfile.ZipFile(output) as archive:
                self.assertEqual(archive.read("source/artifacts/workbench-v2/DOSSIER.html"), (studio / "DOSSIER.html").read_bytes())
                self.assertIn("source/artifacts/workbench-v2/receipt.json", archive.namelist())
                self.assertNotIn("source/artifacts/workbench-v2/obsolete.txt", archive.namelist())

    def test_tampered_studio_bundle_receipt_is_rejected(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            studio = self._studio_bundle(root)
            dossier = studio / "DOSSIER.html"
            dossier.write_text("modified", encoding="utf-8")
            with self.assertRaises(ValueError):
                build(root / "release.zip", studio_bundle=studio)


if __name__ == "__main__":
    unittest.main()
