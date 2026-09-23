"""Restore a verified local backup while preserving the previous data snapshot."""
from __future__ import annotations

import shutil
import socket
import sqlite3
import tempfile
import uuid
from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.db import connections
from django.db.migrations.loader import MigrationLoader

from .backup_workshop import DATABASE, MEDIA, files_in, inspect_database, instance_lock, instance_paths, safe_path, sha256, validate_backup


def _assert_server_stopped():
    port = {"live": 8765, "demo": 8766}.get(settings.MILENIO_MODE)
    if port is None:
        return
    try:
        with socket.create_connection(("127.0.0.1", port), timeout=0.2):
            raise CommandError(f"Port {port} is open; stop the workshop server before restoring")
    except (ConnectionRefusedError, TimeoutError, OSError):
        pass


def _check_current_schema(schema: dict):
    applied = {(app, name) for app, name in schema["migrations"]}
    disk = {(app, name) for app, name in MigrationLoader(None).disk_migrations if app == "workshop"}
    observed = {item for item in applied if item[0] == "workshop"}
    if observed != disk:
        raise CommandError("Backup workshop migrations differ from installed application code")


class Command(BaseCommand):
    help = "Restore a verified backup; requires confirmation and a stopped server."

    def add_arguments(self, parser):
        parser.add_argument("--input", required=True, help="Verified backup directory")
        parser.add_argument("--confirm-restore", action="store_true", help="Explicitly replace active data after validation")

    def handle(self, *args, **options):
        if not options["confirm_restore"]:
            raise CommandError("Restore requires --confirm-restore")
        data, db, media = instance_paths()
        source = safe_path(options["input"], must_exist=True)
        if source == data or source.is_relative_to(media):
            raise CommandError("Restore input cannot be the active data directory")
        with instance_lock(data):
            _assert_server_stopped()
            manifest = validate_backup(source)
            if manifest.get("source_mode") != settings.MILENIO_MODE:
                raise CommandError("Backup mode differs from active instance; live and demo cannot be mixed")
            _check_current_schema(manifest["schema"])
            for suffix in ("-wal", "-shm"):
                if Path(str(db) + suffix).exists():
                    raise CommandError("SQLite journal files remain; close the server and checkpoint before restore")
            stage = Path(tempfile.mkdtemp(prefix=".milenio-restore-", dir=data.parent))
            try:
                shutil.copy2(source / DATABASE, stage / DATABASE)
                (stage / MEDIA).mkdir()
                for file in files_in(source / MEDIA):
                    destination = stage / MEDIA / file.relative_to(source / MEDIA)
                    destination.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copy2(file, destination)
                staged_hashes = {file.relative_to(stage).as_posix(): sha256(file) for file in files_in(stage)}
                if staged_hashes != manifest["files_sha256"] or inspect_database(stage / DATABASE) != manifest["schema"]:
                    raise CommandError("Staged restore does not match the verified backup")
                con = sqlite3.connect(stage / DATABASE)
                try:
                    con.execute("DELETE FROM django_session")
                    con.commit()
                finally:
                    con.close()
                inspect_database(stage / DATABASE)
                connections.close_all()
                previous = data / ("recovery-before-" + uuid.uuid4().hex)
                previous.mkdir()
                previous_db = previous / DATABASE
                previous_media = previous / MEDIA
                moved_previous = []
                installed = []
                try:
                    if db.exists():
                        db.replace(previous_db)
                        moved_previous.append((previous_db, db))
                    if media.exists():
                        media.replace(previous_media)
                        moved_previous.append((previous_media, media))
                    (stage / DATABASE).replace(db)
                    installed.append(db)
                    (stage / MEDIA).replace(media)
                    installed.append(media)
                except Exception:
                    for path in reversed(installed):
                        if path.is_dir():
                            shutil.rmtree(path)
                        else:
                            path.unlink(missing_ok=True)
                    for old, target in reversed(moved_previous):
                        old.replace(target)
                    raise
                self.stdout.write(f"Restauración verificada: {db}. Copia previa: {previous}")
            finally:
                if stage.exists():
                    shutil.rmtree(stage)
