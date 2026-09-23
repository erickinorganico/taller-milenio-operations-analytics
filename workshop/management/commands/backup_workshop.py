"""Consistent SQLite and evidence-media backup for one local workshop instance."""
from __future__ import annotations

import hashlib
import json
import os
import shutil
import sqlite3
import tempfile
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError


FORMAT = "milenio-workshop-backup-v1"
MANIFEST = "manifest.json"
DATABASE = "workshop.sqlite3"
MEDIA = "media"
REQUIRED_TABLES = {"django_migrations", "django_session", "auth_user", "workshop_workorder"}


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for block in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def safe_path(value: str | Path, *, must_exist=False) -> Path:
    original = Path(value).expanduser()
    if ".." in original.parts:
        raise CommandError("Path traversal is not allowed")
    for part in (original, *original.parents):
        if part.is_symlink():
            raise CommandError(f"Symlink path is not allowed: {part}")
    path = original.resolve()
    if must_exist and not path.exists():
        raise CommandError(f"Path does not exist: {path}")
    return path


def instance_paths() -> tuple[Path, Path, Path]:
    data = safe_path(settings.DATA_DIR, must_exist=True)
    db = safe_path(settings.DATABASES["default"]["NAME"])
    media = safe_path(settings.MEDIA_ROOT)
    if not db.is_relative_to(data) or not media.is_relative_to(data) or db == media:
        raise CommandError("Database and media must remain inside MILENIO_DATA_DIR")
    return data, db, media


def inspect_database(path: Path) -> dict:
    if not path.is_file() or path.is_symlink():
        raise CommandError("Backup database is missing or linked")
    con = sqlite3.connect(path.as_uri() + "?mode=ro", uri=True)
    try:
        integrity = con.execute("PRAGMA integrity_check").fetchone()[0]
        if integrity != "ok":
            raise CommandError("SQLite integrity_check failed")
        tables = {row[0] for row in con.execute("SELECT name FROM sqlite_master WHERE type='table'")}
        if not REQUIRED_TABLES <= tables:
            raise CommandError("Backup lacks required Django workshop tables")
        migrations = sorted([list(row) for row in con.execute("SELECT app,name FROM django_migrations")])
        if not any(app == "workshop" for app, _ in migrations):
            raise CommandError("Backup has no applied workshop migration")
        return {"user_version": con.execute("PRAGMA user_version").fetchone()[0],
                "migrations": migrations, "tables": len(tables)}
    except sqlite3.DatabaseError as exc:
        raise CommandError("Could not inspect SQLite database") from exc
    finally:
        con.close()


def files_in(directory: Path) -> list[Path]:
    if directory.is_symlink():
        raise CommandError(f"Symlink directory is not allowed: {directory}")
    if not directory.exists():
        return []
    if not directory.is_dir():
        raise CommandError(f"Expected directory: {directory}")
    result = []
    for path in sorted(directory.rglob("*")):
        if path.is_symlink():
            raise CommandError(f"Symlink file is not allowed: {path}")
        if not path.resolve().is_relative_to(directory.resolve()):
            raise CommandError("File escapes media directory")
        if path.is_file():
            result.append(path)
    return result


@contextmanager
def instance_lock(data_dir: Path, *, blocking=False):
    """Advisory lock held by the supported launcher and checked by restore."""
    data_dir.mkdir(parents=True, exist_ok=True)
    lock_path = data_dir / ".server.lock"
    if lock_path.is_symlink():
        raise CommandError("Server lock path cannot be a symlink")
    with lock_path.open("a+b") as handle:
        handle.seek(0, os.SEEK_END)
        if handle.tell() == 0:
            handle.write(b"0")
            handle.flush()
        handle.seek(0)
        try:
            if os.name == "nt":
                import msvcrt
                msvcrt.locking(handle.fileno(), msvcrt.LK_LOCK if blocking else msvcrt.LK_NBLCK, 1)
            else:
                import fcntl
                fcntl.flock(handle, fcntl.LOCK_EX | (0 if blocking else fcntl.LOCK_NB))
        except OSError as exc:
            raise CommandError("Workshop server is running or instance lock is held") from exc
        try:
            yield
        finally:
            handle.seek(0)
            if os.name == "nt":
                msvcrt.locking(handle.fileno(), msvcrt.LK_UNLCK, 1)
            else:
                fcntl.flock(handle, fcntl.LOCK_UN)


def validate_backup(directory: Path) -> dict:
    directory = safe_path(directory, must_exist=True)
    if not directory.is_dir():
        raise CommandError("Backup input must be a directory")
    if (directory / MANIFEST).is_symlink():
        raise CommandError("Backup manifest cannot be a symlink")
    try:
        manifest = json.loads((directory / MANIFEST).read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        raise CommandError("Backup manifest is missing or invalid") from exc
    if manifest.get("format") != FORMAT or type(manifest.get("synthetic")) is not bool:
        raise CommandError("Unsupported backup manifest")
    expected = manifest.get("files_sha256")
    if not isinstance(expected, dict) or DATABASE not in expected:
        raise CommandError("Backup manifest lacks database hash")
    actual = {}
    for file in files_in(directory):
        relative = file.relative_to(directory).as_posix()
        if relative == MANIFEST:
            continue
        parts = relative.split("/")
        if relative != DATABASE and (len(parts) < 2 or parts[0] != MEDIA):
            raise CommandError("Unexpected backup file")
        actual[relative] = sha256(file)
    if actual != expected:
        raise CommandError("Backup files do not match manifest hashes")
    schema = inspect_database(directory / DATABASE)
    if schema != manifest.get("schema"):
        raise CommandError("Backup schema does not match manifest")
    return manifest


class Command(BaseCommand):
    help = "Create a consistent SQLite and media backup in a new directory."

    def add_arguments(self, parser):
        parser.add_argument("--output", required=True, help="New backup directory; must not exist")

    def handle(self, *args, **options):
        data, db, media = instance_paths()
        output = safe_path(options["output"])
        if (output.exists() or output == data or db.is_relative_to(output)
                or media.is_relative_to(output) or output.is_relative_to(media)):
            raise CommandError("Backup destination must be a new directory outside active data paths")
        if not db.is_file():
            raise CommandError("Workshop database does not exist; start the app first")
        output.parent.mkdir(parents=True, exist_ok=True)
        stage = Path(tempfile.mkdtemp(prefix=".milenio-backup-", dir=output.parent))
        try:
            source = sqlite3.connect(db.as_uri() + "?mode=ro", uri=True)
            target = sqlite3.connect(stage / DATABASE)
            try:
                source.backup(target)
            finally:
                target.close()
                source.close()
            schema = inspect_database(stage / DATABASE)
            (stage / MEDIA).mkdir()
            for file in files_in(media):
                destination = stage / MEDIA / file.relative_to(media)
                destination.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(file, destination)
            hashes = {file.relative_to(stage).as_posix(): sha256(file) for file in files_in(stage)}
            manifest = {"format": FORMAT, "created_at_utc": datetime.now(timezone.utc).isoformat(),
                        "synthetic": settings.MILENIO_MODE == "demo", "source_mode": settings.MILENIO_MODE,
                        "schema": schema, "files_sha256": hashes,
                        "excludes": [".secret_key", "sessions after restore"]}
            (stage / MANIFEST).write_text(json.dumps(manifest, ensure_ascii=False, sort_keys=True, indent=2) + "\n", encoding="utf-8")
            validate_backup(stage)
            if output.exists():
                raise CommandError("Backup destination appeared during creation")
            stage.replace(output)
            self.stdout.write(f"Respaldo verificado: {output}")
        finally:
            if stage.exists():
                shutil.rmtree(stage)
