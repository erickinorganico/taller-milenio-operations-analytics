"""Build a deterministic source-plus-demo release archive.

The command packages tracked Git files, an optional verified synthetic bundle,
and an optional offline wheelhouse. It never includes the repository metadata,
virtual environments, private workbench data, or an existing output archive.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
FORBIDDEN = {".git", ".venv", ".workbench", "private", "dist"}
SENSITIVE_SUFFIXES = {".pem", ".key", ".p12", ".pfx"}


def _reject_sensitive(path: Path):
    if path.is_symlink():
        raise ValueError(f"symlinks are not allowed: {path}")
    if path.name == ".env" or (path.name.startswith(".env.") and path.name != ".env.example") or path.suffix.lower() in SENSITIVE_SUFFIXES:
        raise ValueError(f"sensitive file cannot be packaged: {path}")


def _safe_relative(path: Path) -> str:
    relative = path.resolve().relative_to(ROOT.resolve()).as_posix()
    parts = Path(relative).parts
    if not parts or any(part in {"..", "."} for part in parts) or any(part in FORBIDDEN for part in parts):
        raise ValueError(f"unsafe package path: {relative}")
    return relative


def _files(path: Path):
    if not path.exists() or not path.is_dir():
        raise ValueError(f"directory does not exist: {path}")
    for candidate in path.rglob("*"):
        if candidate.is_symlink():
            raise ValueError(f"symlinks are not allowed: {candidate}")
    return sorted(p for p in path.rglob("*") if p.is_file())


def _tracked():
    try:
        root_check = subprocess.run(["git", "rev-parse", "--show-toplevel"], cwd=ROOT, check=True, capture_output=True, text=True)
        if Path(root_check.stdout.strip()).resolve() != ROOT.resolve():
            raise ValueError("Git root does not match project root")
        completed = subprocess.run(["git", "ls-files", "-z"], cwd=ROOT, check=True, capture_output=True)
        result = []
        for raw in completed.stdout.split(b"\0"):
            if raw:
                candidate = ROOT / raw.decode("utf-8")
                _reject_sensitive(candidate)
                if candidate.is_file():
                    result.append(candidate)
        return sorted(result)
    except (OSError, ValueError, subprocess.CalledProcessError):
        # An extracted release has no .git. The root manifest is the narrow
        # allowlist; never replace it with a recursive filesystem walk.
        manifest_path = ROOT.parent / "RELEASE-MANIFEST.json"
        if not manifest_path.is_file():
            raise ValueError("git metadata unavailable and RELEASE-MANIFEST.json is missing")
        document = json.loads(manifest_path.read_text(encoding="utf-8"))
        hashes = document.get("entries_sha256", {})
        result = []
        for archive_name, expected in sorted(hashes.items()):
            if not archive_name.startswith("source/"):
                continue
            relative = archive_name[len("source/"):]
            if relative.startswith((".runtime/wheels/", "artifacts/demo/")):
                continue
            candidate = (ROOT / relative).resolve()
            if candidate.parent != ROOT and ROOT not in candidate.parents:
                raise ValueError(f"manifest path escapes source: {archive_name}")
            _safe_relative(candidate)
            _reject_sensitive(candidate)
            if not candidate.is_file() or _sha(candidate) != expected:
                raise ValueError(f"manifest source missing or changed: {archive_name}")
            result.append(candidate)
        if not result:
            raise ValueError("release manifest contains no source entries")
        return result


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _canonical(value) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False)


def _verify_bundle(path: Path):
    receipt = path / "receipt.json"
    if not receipt.is_file():
        raise ValueError("bundle requires root receipt.json")
    try:
        receipt_data = json.loads(receipt.read_text(encoding="utf-8"))
        if receipt_data.get("status") != "pass" or receipt_data.get("synthetic") is not True:
            raise ValueError("receipt is not a passing synthetic receipt")
        expected = receipt_data.get("artifacts_sha256", {})
        actual = {p.relative_to(path).as_posix(): _sha(p) for p in sorted(path.rglob("*")) if p.is_file() and p != receipt}
        if actual != expected or hashlib.sha256(_canonical(actual).encode("utf-8")).hexdigest() != receipt_data.get("content_sha256"):
            raise ValueError("receipt hashes do not match bundle contents")
    except Exception as exc:
        raise ValueError(f"bundle receipt verification failed: {exc}") from exc


def build(output: Path, bundle: Path | None = None, wheelhouse: Path | None = None) -> dict:
    output = output.resolve()
    if output.exists():
        raise ValueError("output already exists")
    if output.parent == output or output.parent == ROOT.parent:
        raise ValueError("unsafe output directory")
    entries: dict[str, Path] = {}
    reserved_prefix = "source/artifacts/demo/"
    for path in _tracked():
        relative = _safe_relative(path)
        if relative == output.relative_to(ROOT).as_posix() if output.is_relative_to(ROOT) else False:
            continue
        if wheelhouse is not None and relative.startswith('.runtime/wheels/'):
            continue
        if bundle is None or not ("source/" + relative).startswith(reserved_prefix):
            entries.setdefault("source/" + relative, path)
    if bundle is not None:
        bundle = bundle.resolve()
        _verify_bundle(bundle)
        for path in _files(bundle):
            relative = path.relative_to(bundle).as_posix()
            _safe_relative(ROOT / "artifacts/demo" / relative)
            entries.setdefault("source/artifacts/demo/" + relative, path)
    if wheelhouse is not None:
        wheelhouse = wheelhouse.resolve()
        for path in _files(wheelhouse):
            if path.suffix.lower() != ".whl":
                raise ValueError(f"wheelhouse may contain only .whl files: {path}")
            entries.setdefault("source/.runtime/wheels/" + path.relative_to(wheelhouse).as_posix(), path)
    output.parent.mkdir(parents=True, exist_ok=True)
    from milenio.verification import publication_scan
    scan = publication_scan(ROOT)
    if scan["status"] != "pass":
        raise ValueError("publication scan failed: " + json.dumps(scan["findings"], sort_keys=True))
    manifest = {name: _sha(path) for name, path in sorted(entries.items())}
    manifest_text = json.dumps({"format": 1, "synthetic_bundle_verified": bundle is not None,
                                "entries_sha256": manifest}, indent=2, sort_keys=True) + "\n"
    with zipfile.ZipFile(output, "x", compression=zipfile.ZIP_DEFLATED) as archive:
        for name, path in sorted(entries.items()):
            info = zipfile.ZipInfo(name, date_time=(2020, 1, 1, 0, 0, 0))
            info.compress_type = zipfile.ZIP_DEFLATED
            archive.writestr(info, path.read_bytes())
        info = zipfile.ZipInfo("RELEASE-MANIFEST.json", date_time=(2020, 1, 1, 0, 0, 0))
        info.compress_type = zipfile.ZIP_DEFLATED
        archive.writestr(info, manifest_text.encode("utf-8"))
    return {"output": str(output), "entries": len(entries), "bundle_verified": bundle is not None,
            "wheelhouse": wheelhouse is not None, "manifest_sha256": hashlib.sha256(manifest_text.encode()).hexdigest()}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--bundle", type=Path)
    parser.add_argument("--wheelhouse", type=Path)
    args = parser.parse_args(argv)
    if str(ROOT) not in sys.path:
        sys.path.insert(0, str(ROOT))
    try:
        print(json.dumps(build(args.output, args.bundle, args.wheelhouse), sort_keys=True))
        return 0
    except (OSError, ValueError, subprocess.CalledProcessError) as exc:
        print(f"package failed: {exc}")
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
