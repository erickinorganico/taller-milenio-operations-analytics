"""Package a verified synthetic V4 studio as a local, reviewable ZIP candidate.

The reader opens INICIO.html at archive root; the sealed delivery is preserved
under studio/. Optional source is selected from an explicit allowlist and does
not depend on Git staging or commit state.
"""
from __future__ import annotations

import argparse
import fnmatch
import hashlib
import json
import shutil
import sys
import tempfile
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
from milenio.client_delivery import verify_client
from milenio.client_actions import load_action_reviews
from milenio.studio import verify_studio

MANIFEST_NAME = "OPERATING-KIT-MANIFEST.json"
INTRO_NAME = "ABRIR-PRIMERO.txt"
SOURCE_FOLDERS = ("milenio", "contracts", "agents", "processes", "specs", "docs", "queries", "scripts", "tests", ".github")
SKIP_PARTS = {".git", ".venv", "venv", "env", "__pycache__", ".pytest_cache", ".mypy_cache",
              ".ruff_cache", ".cache", ".workbench", "private", "dist", "output", "artifacts", ".runtime"}
SENSITIVE_SUFFIXES = {".pem", ".key", ".p12", ".pfx"}
ROOT_EXACT = {"PROJECT.md", "LICENSE", "pyproject.toml", "requirements.txt"}
ROOT_PATTERNS = ("README*.md", "Setup*.ps1", "Run*.cmd", "Run*.ps1", "CLIENTE*.html")
INTRO = (
    "Taller Milenio / modelo operativo V4 (datos sintéticos)\n\n"
    "Extraiga todo el ZIP y abra INICIO.html en esta carpeta. Ese acceso abre "
    "studio/INICIO.html; el studio sellado permanece completo dentro de studio/. "
    "Para comprobarlo, ejecute verify_studio sobre la carpeta studio. "
    "Las decisiones son propuestas para "
    "revisión humana; no ejecutan acciones de negocio.\n\n"
    "Si existe source/, contiene un candidato local de código y ejemplos. "
    "Su manifiesto registra bytes empaquetados; no afirma publicación ni estado de Git.\n"
).encode("utf-8")
ROOT_ENTRY = (
    '<!doctype html><html lang="es"><meta charset="utf-8">'
    '<meta http-equiv="refresh" content="0; url=studio/INICIO.html">'
    '<title>Taller Milenio · Abrir studio</title>'
    '<p>Abra el <a href="studio/INICIO.html">studio operativo sellado</a>.</p></html>\n'
).encode("utf-8")


def _sha(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for block in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _zip_sha(archive: zipfile.ZipFile, name: str) -> str:
    digest = hashlib.sha256()
    with archive.open(name) as source:
        for block in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _safe_name(name: str) -> str:
    if not name or "\\" in name or name.startswith("/") or ":" in name:
        raise ValueError(f"unsafe archive path: {name}")
    parts = name.split("/")
    if any(part in ("", ".", "..") for part in parts):
        raise ValueError(f"unsafe archive path: {name}")
    return name


def _files(directory: Path):
    if directory.is_symlink() or not directory.is_dir():
        raise ValueError(f"directory missing or linked: {directory}")
    base = directory.resolve()
    for candidate in sorted(directory.rglob("*")):
        if candidate.is_symlink():
            raise ValueError(f"symlink cannot be packaged: {candidate}")
        if not candidate.resolve().is_relative_to(base):
            raise ValueError(f"path escapes package input: {candidate}")
        if candidate.is_file():
            yield candidate


def _root_file(name: str) -> bool:
    return name in ROOT_EXACT or any(fnmatch.fnmatchcase(name, pattern) for pattern in ROOT_PATTERNS)


def _source_files(verified_hashes: dict[str, str] | None = None) -> dict[str, Path]:
    entries: dict[str, Path] = {}
    for file in ROOT.iterdir():
        if file.is_symlink() and _root_file(file.name):
            raise ValueError(f"symlink cannot be packaged: {file}")
        if file.is_file() and _root_file(file.name):
            entries[_safe_name("source/" + file.name)] = file
    for folder in SOURCE_FOLDERS:
        directory = ROOT / folder
        if not directory.exists():
            continue
        for file in _files(directory):
            relative = file.relative_to(ROOT)
            if any(part.casefold() in SKIP_PARTS for part in relative.parts):
                continue
            if file.name == ".env" or file.name.startswith(".env.") or file.suffix.casefold() in SENSITIVE_SUFFIXES:
                raise ValueError(f"sensitive source file: {file}")
            entries[_safe_name("source/" + relative.as_posix())] = file
    client_data = ROOT / "examples" / "client_data"
    if client_data.exists():
        for file in _files(client_data):
            relative = file.relative_to(ROOT)
            if any(part.casefold() in SKIP_PARTS for part in relative.parts):
                continue
            example_relative = file.relative_to(client_data).as_posix()
            approved = example_relative in {"README.md", "client_input_sample.xlsx", "client_input_blank.xlsx"}
            approved = approved or (len(file.relative_to(client_data).parts) == 2
                                    and file.relative_to(client_data).parts[0] in {"sample_csv", "blank_csv"}
                                    and file.suffix.casefold() == ".csv")
            if not approved:
                continue
            if file.suffix.casefold() in SENSITIVE_SUFFIXES:
                raise ValueError(f"sensitive example file: {file}")
            entries[_safe_name("source/" + relative.as_posix())] = file
    deliveries = ROOT / "examples" / "client_delivery"
    if deliveries.exists():
        if deliveries.is_symlink():
            raise ValueError("client delivery examples cannot be linked")
        # Only receipt-backed examples are packaged. Standalone spreadsheets
        # and comparisons lack a sealed synthetic identity.
        for child in sorted(deliveries.iterdir()):
            if child.is_symlink():
                raise ValueError(f"symlink cannot be packaged: {child}")
            if not child.is_dir() or not (child / "receipt.json").is_file():
                continue
            receipt_hash = _sha(child / "receipt.json")
            receipt = verify_client(child)
            if _sha(child / "receipt.json") != receipt_hash:
                raise ValueError(f"client receipt changed during verification: {child}")
            if receipt.get("synthetic") is not True:
                raise ValueError(f"non-synthetic client example: {child}")
            sealed_names = set(receipt.get("artifacts_sha256", {})) | {"receipt.json"}
            review_workbook = child / "Seguimiento.xlsx"
            if review_workbook.is_file():
                review_hash = _sha(review_workbook)
                analysis = json.loads((child / "analysis.json").read_text(encoding="utf-8"))
                if analysis.get("metadata", {}).get("synthetic") is not True:
                    raise ValueError(f"non-synthetic client analysis: {child}")
                reviews = load_action_reviews(review_workbook, analysis["decisions"], analysis["metadata"])
                if _sha(review_workbook) != review_hash:
                    raise ValueError(f"client review workbook changed during verification: {child}")
                if any(review["status"] != "pending" or any(review[field] is not None for field in
                       ("owner", "target_date", "note", "outcome_evidence")) for review in reviews):
                    raise ValueError(f"client review workbook contains human annotations: {child}")
                sealed_names.add("Seguimiento.xlsx")
            for file in _files(child):
                relative = file.relative_to(ROOT)
                if any(part.casefold() in SKIP_PARTS for part in relative.parts):
                    continue
                if file.relative_to(child).as_posix() not in sealed_names:
                    continue
                name = _safe_name("source/" + relative.as_posix())
                entries[name] = file
                if verified_hashes is not None:
                    relative_name = file.relative_to(child).as_posix()
                    verified_hashes[name] = (review_hash if relative_name == "Seguimiento.xlsx" else
                                             receipt_hash if relative_name == "receipt.json" else
                                             receipt["artifacts_sha256"][relative_name])
    return entries


def _wheel_files(wheelhouse: Path) -> dict[str, Path]:
    if wheelhouse.is_symlink() or not wheelhouse.is_dir():
        raise ValueError("wheelhouse must be a real directory")
    entries = {}
    for file in _files(wheelhouse):
        if file.parent != wheelhouse or file.suffix.casefold() != ".whl":
            raise ValueError(f"wheelhouse accepts only flat .whl files: {file}")
        entries[_safe_name("source/.runtime/wheels/" + file.name)] = file
    if not entries:
        raise ValueError("wheelhouse is empty")
    return entries


def _zip_entry(archive: zipfile.ZipFile, name: str, source: Path | bytes) -> None:
    info = zipfile.ZipInfo(_safe_name(name), date_time=(1980, 1, 1, 0, 0, 0))
    info.compress_type = zipfile.ZIP_DEFLATED
    info.external_attr = 0o644 << 16
    if isinstance(source, bytes):
        archive.writestr(info, source)
    else:
        with source.open("rb") as reader, archive.open(info, "w") as writer:
            shutil.copyfileobj(reader, writer, length=1024 * 1024)


def build(output, studio, include_source=False, wheelhouse=None) -> dict:
    """Write one local ZIP after checking the V4 studio and every selected path."""
    output = Path(output).resolve()
    studio = Path(studio)
    if output.exists():
        raise ValueError("output already exists")
    if studio.is_symlink() or not studio.is_dir():
        raise ValueError("studio must be a real directory")
    studio = studio.resolve()
    if output.is_relative_to(studio):
        raise ValueError("output cannot be inside the sealed studio")
    verified = verify_studio(studio)
    if verified.get("status") != "pass":
        raise ValueError("studio verification did not pass")
    receipt = json.loads((studio / "receipt.json").read_text(encoding="utf-8"))
    if receipt.get("synthetic") is not True or not (studio / "INICIO.html").is_file():
        raise ValueError("studio must be synthetic and contain INICIO.html")
    entries: dict[str, Path | bytes] = {}
    verified_source_hashes: dict[str, str] = {}
    for file in _files(studio):
        name = _safe_name("studio/" + file.relative_to(studio).as_posix())
        entries[name] = file
    if include_source:
        for name, file in _source_files(verified_source_hashes).items():
            if name in entries:
                raise ValueError(f"duplicate package path: {name}")
            entries[name] = file
        # Preserve the studio's relative path expected by source-side scripts.
        for file in _files(studio):
            name = _safe_name("source/artifacts/operating-model-v4/" + file.relative_to(studio).as_posix())
            if name in entries:
                raise ValueError(f"duplicate package path: {name}")
            entries[name] = file
    if wheelhouse is not None:
        if not include_source:
            raise ValueError("wheelhouse requires include_source=True")
        wheelhouse = Path(wheelhouse)
        if output.is_relative_to(wheelhouse.resolve()):
            raise ValueError("output cannot be inside wheelhouse")
        for name, file in _wheel_files(wheelhouse).items():
            if name in entries:
                raise ValueError(f"duplicate package path: {name}")
            entries[name] = file
    entries["INICIO.html"] = ROOT_ENTRY
    entries[INTRO_NAME] = INTRO
    folded = [name.casefold() for name in entries]
    if len(folded) != len(set(folded)):
        raise ValueError("archive contains paths that collide on case-insensitive filesystems")
    hashes = {name: hashlib.sha256(value).hexdigest() if isinstance(value, bytes) else _sha(value)
              for name, value in sorted(entries.items())}
    manifest = {
        "format": "milenio-operating-kit-v4", "publication_status": "local_candidate",
        "synthetic": True, "reader_entrypoint": "INICIO.html", "sealed_studio_path": "studio",
        "studio_content_sha256": verified["content_sha256"],
        "source_included": bool(include_source), "wheels_included": wheelhouse is not None,
        "entries_sha256": hashes,
    }
    manifest_bytes = (json.dumps(manifest, ensure_ascii=False, sort_keys=True, indent=2) + "\n").encode("utf-8")
    output.parent.mkdir(parents=True, exist_ok=True)
    temporary = None
    try:
        with tempfile.NamedTemporaryFile(prefix=".operating-kit-", suffix=".zip", dir=output.parent, delete=False) as handle:
            temporary = Path(handle.name)
        with zipfile.ZipFile(temporary, "w", compression=zipfile.ZIP_DEFLATED, allowZip64=True) as archive:
            for name, source in sorted(entries.items()):
                _zip_entry(archive, name, source)
            _zip_entry(archive, MANIFEST_NAME, manifest_bytes)
        # The seal is checked again after reading; a concurrent studio edit is
        # an error even if it occurs while the ZIP is being written.
        verify_studio(studio)
        with zipfile.ZipFile(temporary) as archive:
            actual = {name: _zip_sha(archive, name) for name in hashes}
            if actual != hashes or any(actual[name] != expected for name, expected in verified_source_hashes.items()) or len(archive.namelist()) != len(hashes) + 1:
                raise ValueError("package content changed while writing")
        if output.exists():
            raise ValueError("output already exists")
        temporary.replace(output)
        temporary = None
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)
    return {"output": str(output), "files": len(hashes) + 1,
            "sha256": _sha(output), "manifest_sha256": hashlib.sha256(manifest_bytes).hexdigest(),
            "publication_status": "local_candidate", "synthetic": True,
            "source_included": bool(include_source), "wheels_included": wheelhouse is not None}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", required=True)
    parser.add_argument("--studio", required=True)
    parser.add_argument("--include-source", action="store_true")
    parser.add_argument("--wheelhouse")
    args = parser.parse_args()
    print(json.dumps(build(args.output, args.studio, args.include_source, args.wheelhouse), ensure_ascii=False))
