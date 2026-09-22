"""Local test harness, publication hygiene and machine-readable verification receipt."""
import importlib.metadata
import io
import json
import re
import sys
import unittest
from datetime import datetime, timezone
from pathlib import Path
from xml.etree import ElementTree as ET


ROOT = Path(__file__).resolve().parent.parent


def publication_scan(root=ROOT):
    """Bounded sentinel, not a guarantee that arbitrary imported data is anonymous."""
    patterns = {
        "github_credential": r"(?:gh[pousr]_[A-Za-z0-9]{32,}|github_pat_[A-Za-z0-9_]{40,})",
        "aws_access_id": r"AKIA[A-Z0-9]{16}",
        "private_key": r"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----",
        "private_workstation_path": r"[A-Z]:[\\/]Users[\\/][A-Za-z0-9_.-]+[\\/]",
    }
    files = [p for p in root.iterdir() if p.is_file() and p.suffix in {".md", ".toml", ".txt", ".ps1", ".cmd"}]
    for folder in ("milenio", "tests", "docs", "examples", "contracts", "queries", ".github"):
        files.extend(p for p in (root / folder).rglob("*") if p.is_file() and p.suffix in {".py", ".md", ".json", ".csv", ".sql", ".yml", ".yaml"})
    findings = []
    for path in sorted(files):
        text = path.read_text(encoding="utf-8-sig")
        for category, pattern in patterns.items():
            if re.search(pattern, text):
                findings.append({"file": path.relative_to(root).as_posix(), "category": category})
    return {"status": "pass" if not findings else "fail", "files_scanned": len(files), "findings": findings,
            "scope": "Publication source/templates/docs. Synthetic bundle is validated separately. Heuristic, not anonymization certification."}


class RecordingResult(unittest.TextTestResult):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.executed = []

    def startTest(self, test):
        self.executed.append(test.id())
        super().startTest(test)


def verify_project(output):
    from .pipeline import write_json, source_manifest
    output = Path(output)
    output.parent.mkdir(parents=True, exist_ok=True)
    stream = io.StringIO()
    suite = unittest.defaultTestLoader.discover(str(ROOT / "tests"), pattern="test_*.py")
    result = unittest.TextTestRunner(stream=stream, verbosity=2, resultclass=RecordingResult).run(suite)
    log = stream.getvalue().replace(str(ROOT), "<project>")
    output.with_suffix(".log").write_text(log, encoding="utf-8")
    scan = publication_scan()
    dependencies = {}
    for line in (ROOT / "requirements.txt").read_text(encoding="utf-8-sig").splitlines():
        if not line.strip() or line.startswith("#"):
            continue
        name, version = line.split("==", 1)
        try:
            actual = importlib.metadata.version(name)
        except importlib.metadata.PackageNotFoundError:
            actual = None
        dependencies[name] = {"required": version, "installed": actual, "ok": actual == version}
    successful = result.wasSuccessful() and result.testsRun > 0 and scan["status"] == "pass" and all(r["ok"] for r in dependencies.values())
    receipt = {"status": "pass" if successful else "fail", "tested_at_utc": datetime.now(timezone.utc).isoformat(),
               "tests": {"run": result.testsRun, "failures": len(result.failures), "errors": len(result.errors), "skipped": len(result.skipped)},
               "source_sha256": source_manifest(), "publication_scan": scan, "dependencies": dependencies,
               "limitations": ["Synthetic snapshot only", "No operator discovery or real-system pilot", "No production dispatch, tax or accounting certification"]}
    write_json(output, receipt)
    junit = ET.Element("testsuite", name="milenio", tests=str(result.testsRun), failures=str(len(result.failures)), errors=str(len(result.errors)))
    failures = {test.id(): info for test, info in result.failures}
    errors = {test.id(): info for test, info in result.errors}
    for name in result.executed:
        case = ET.SubElement(junit, "testcase", name=name)
        if name in failures or name in errors:
            ET.SubElement(case, "failure" if name in failures else "error").text = (failures.get(name) or errors[name]).replace(str(ROOT), "<project>")
    ET.ElementTree(junit).write(output.with_suffix(".xml"), encoding="utf-8", xml_declaration=True)
    print(json.dumps({"status": receipt["status"], "tests": receipt["tests"], "publication_scan": scan["status"], "receipt": str(output)}))
    if not successful:
        print(log, file=sys.stderr)
        if scan["findings"]:
            print(json.dumps(scan["findings"]), file=sys.stderr)
    return 0 if successful else 1
