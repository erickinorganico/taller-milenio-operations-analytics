"""Build a local candidate containing the V6 web application and versioned docs."""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import shutil
import subprocess
import sys
import tempfile
import zipfile
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
FOLDERS = ("workshop", "milenio_web")
ROOT_FILES = ("manage.py", "requirements-web.txt", "Setup-Web.ps1", "Iniciar-Milenio.cmd",
              "Iniciar-Demo.cmd", "Setup-Agents.ps1", "README-WEB.md", "CLIENTE.html", "LICENSE")
OTHER_FILES = ("scripts/run_web.py", "scripts/package_web.py", "scripts/export_web_contracts.py",
               "scripts/verify_web.py", "scripts/verify_v6_delivery.py",
               "docs/V5-INSTALACION.md", "docs/V6-ANALYTICS.md", "docs/V6-AUTOMATIZACIONES.md",
               "docs/V6-VERIFICACION.md",
               "docs/V5-MANUAL.md", "specs/v5-domain-api.md", "specs/v5-intelligence.md", "specs/v6-analytics-automation.md",
               ".planning/PROJECT.md", ".planning/milestones/v5.0-REQUIREMENTS.md")
SKIP_PARTS = {".git", ".venv", "venv", "env", "__pycache__", ".pytest_cache", ".mypy_cache",
              ".ruff_cache", ".cache", "private", "dist", "output", "artifacts"}
SENSITIVE_SUFFIXES = {".sqlite", ".sqlite3", ".db", ".zip", ".pem", ".key", ".p12", ".pfx"}
MANIFEST = "WEB-PACKAGE-MANIFEST.json"


def _sha(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for block in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _name(value: str) -> str:
    if not value or value.startswith("/") or "\\" in value or ":" in value or any(
            part in ("", ".", "..") for part in value.split("/")):
        raise ValueError(f"unsafe archive path: {value}")
    return value


def _collect() -> dict[str, Path]:
    entries = {}
    for relative in (*ROOT_FILES, *OTHER_FILES):
        file = ROOT / relative
        if file.is_symlink() or not file.is_file():
            raise ValueError(f"required web source missing or linked: {file}")
        entries[_name(relative)] = file
    for folder in FOLDERS:
        directory = ROOT / folder
        if directory.is_symlink() or not directory.is_dir():
            raise ValueError(f"required web folder missing or linked: {directory}")
        for candidate in sorted(directory.rglob("*")):
            if candidate.is_symlink():
                raise ValueError(f"symlink cannot be packaged: {candidate}")
            if not candidate.is_file():
                continue
            relative = candidate.relative_to(ROOT)
            if any(part.casefold() in SKIP_PARTS for part in relative.parts):
                continue
            if (candidate.name == ".env" or candidate.name.startswith(".env.")
                    or candidate.suffix.casefold() in SENSITIVE_SUFFIXES):
                raise ValueError(f"sensitive file inside web source: {candidate}")
            if not candidate.resolve().is_relative_to(ROOT.resolve()):
                raise ValueError(f"web source escapes project: {candidate}")
            entries[_name(relative.as_posix())] = candidate
    for directory, pattern in ((ROOT / "docs", "V5*.md"), (ROOT / ".planning", "**/*.md")):
        if not directory.exists():
            continue
        if directory.is_symlink() or not directory.is_dir():
            raise ValueError(f"documentation directory is linked or invalid: {directory}")
        for candidate in sorted(directory.glob(pattern)):
            if candidate.is_symlink() or not candidate.is_file() or not candidate.resolve().is_relative_to(ROOT.resolve()):
                raise ValueError(f"unsafe documentation file: {candidate}")
            relative = candidate.relative_to(ROOT)
            if any(part.casefold() in SKIP_PARTS for part in relative.parts):
                raise ValueError(f"unsafe documentation path: {candidate}")
            entries[_name(relative.as_posix())] = candidate
    return entries


def _wheels(wheelhouse: Path) -> dict[str, Path]:
    if wheelhouse.is_symlink() or not wheelhouse.is_dir():
        raise ValueError("wheelhouse must be a real directory")
    found = {}
    for file in sorted(wheelhouse.rglob("*")):
        if file.is_symlink():
            raise ValueError("wheelhouse symlinks are not allowed")
        if file.is_file():
            if file.parent != wheelhouse or file.suffix.casefold() != ".whl":
                raise ValueError("wheelhouse accepts only flat .whl files")
            found[_name(".runtime/wheels/" + file.name)] = file
    required = {}
    for line in (ROOT / "requirements-web.txt").read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        match = re.fullmatch(r"([A-Za-z0-9_.-]+)==([A-Za-z0-9_.!+]+)", line)
        if not match:
            raise ValueError(f"web dependency is not exactly pinned: {line}")
        required[re.sub(r"[-_.]+", "-", match[1]).casefold()] = match[2]
    available = {}
    for archive_name in found:
        filename = Path(archive_name).name[:-4]
        pieces = filename.split("-")
        if len(pieces) not in (5, 6):
            raise ValueError(f"invalid wheel filename: {filename}")
        package, version = re.sub(r"[-_.]+", "-", pieces[0]).casefold(), pieces[1]
        python_tag, abi_tag, platform_tag = pieces[-3:]
        interpreters = set(python_tag.split("."))
        platforms = set(platform_tag.split("."))
        abis = set(abi_tag.split("."))
        universal = "any" in platforms and "none" in abis and bool(interpreters & {"py3", "cp312"})
        windows312 = "win_amd64" in platforms and (
            ("cp312" in interpreters and bool(abis & {"cp312", "abi3", "none"}))
            or ("py3" in interpreters and "none" in abis)
        )
        if not (universal or windows312):
            raise ValueError(f"wheel is not compatible with Windows x64 / Python 3.12: {filename}")
        if package in available:
            raise ValueError(f"duplicate dependency wheel: {package}")
        available[package] = version
    if available != required:
        raise ValueError(f"wheelhouse does not match requirements-web.txt: missing={sorted(set(required)-set(available))}, extra={sorted(set(available)-set(required))}, wrong_versions={sorted(name for name in set(available)&set(required) if available[name] != required[name])}")
    return found


def collect_wheels(destination: str | Path) -> dict:
    """Explicitly fetch the pinned CPython 3.12 win_amd64 wheel set."""
    destination = Path(destination).resolve()
    if destination.exists():
        raise ValueError("wheel destination already exists")
    with tempfile.TemporaryDirectory(prefix="milenio-web-wheels-") as temporary:
        staging = Path(temporary) / "wheels"
        staging.mkdir()
        subprocess.run([sys.executable, "-m", "pip", "download", "--only-binary=:all:",
                        "--platform", "win_amd64", "--python-version", "3.12",
                        "--implementation", "cp", "--abi", "cp312", "--dest", str(staging),
                        "-r", str(ROOT / "requirements-web.txt")], check=True)
        wheels = _wheels(staging)
        destination.parent.mkdir(parents=True, exist_ok=True)
        staging.rename(destination)
        return {"destination": str(destination), "wheels": len(wheels),
                "sha256": {path.name: _sha(path) for path in destination.iterdir()}}


def _write(archive: zipfile.ZipFile, name: str, source: Path | bytes):
    info = zipfile.ZipInfo(_name(name), date_time=(1980, 1, 1, 0, 0, 0))
    info.compress_type = zipfile.ZIP_DEFLATED
    info.external_attr = 0o644 << 16
    if isinstance(source, bytes):
        archive.writestr(info, source)
    else:
        with source.open("rb") as reader, archive.open(info, "w") as writer:
            shutil.copyfileobj(reader, writer, length=1024 * 1024)


def build(output: str | Path, wheelhouse: str | Path | None = None) -> dict:
    output = Path(output).resolve()
    if output.exists():
        raise ValueError("output already exists")
    entries: dict[str, Path] = _collect()
    if wheelhouse is not None:
        wheelhouse = Path(wheelhouse)
        if output.is_relative_to(wheelhouse.resolve()):
            raise ValueError("output cannot be inside wheelhouse")
        entries.update(_wheels(wheelhouse))
    names = [name.casefold() for name in entries]
    if len(names) != len(set(names)):
        raise ValueError("archive has case-insensitive path collisions")
    expected = {name: _sha(file) for name, file in sorted(entries.items())}
    manifest = {"format": "milenio-web-v6", "publication_status": "local_candidate",
                "entrypoint": "Iniciar-Milenio.cmd", "demo_entrypoint": "Iniciar-Demo.cmd",
                "includes_private_data": False, "wheels_included": wheelhouse is not None,
                "entries_sha256": expected}
    document = (json.dumps(manifest, ensure_ascii=False, sort_keys=True, indent=2) + "\n").encode("utf-8")
    output.parent.mkdir(parents=True, exist_ok=True)
    temporary = None
    try:
        with tempfile.NamedTemporaryFile(prefix=".web-package-", suffix=".zip", dir=output.parent, delete=False) as handle:
            temporary = Path(handle.name)
        with zipfile.ZipFile(temporary, "w", allowZip64=True) as archive:
            for name, source in sorted(entries.items()):
                _write(archive, name, source)
            _write(archive, MANIFEST, document)
        with zipfile.ZipFile(temporary) as archive:
            if len(archive.namelist()) != len(expected) + 1:
                raise ValueError("ZIP contains unexpected paths")
            for name, digest in expected.items():
                with archive.open(name) as reader:
                    actual = hashlib.file_digest(reader, "sha256").hexdigest()
                if actual != digest:
                    raise ValueError(f"ZIP content changed while writing: {name}")
        if output.exists():
            raise ValueError("output appeared during packaging")
        temporary.replace(output)
        temporary = None
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)
    return {"output": str(output), "sha256": _sha(output), "files": len(expected) + 1,
            "publication_status": "local_candidate", "wheels_included": wheelhouse is not None}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output")
    parser.add_argument("--wheelhouse")
    parser.add_argument("--collect-wheels")
    args = parser.parse_args()
    if args.collect_wheels:
        if args.output or args.wheelhouse:
            parser.error("--collect-wheels is separate from --output/--wheelhouse")
        result = collect_wheels(args.collect_wheels)
    elif args.output:
        result = build(args.output, args.wheelhouse)
    else:
        parser.error("pass --output or --collect-wheels")
    print(json.dumps(result, ensure_ascii=False))
