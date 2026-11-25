"""Migrate a portable Windows workshop backup into a blank, isolated Linux installation."""
import argparse
from decimal import Decimal
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import sqlite3
import stat
import subprocess
import sys
import tempfile
import time

UID = 10001
HASH = re.compile(r"[0-9a-f]{64}")
REVISION = re.compile(r"[0-9a-f]{40}")
TABLES = {
    "customer": "id,name",
    "vehicle": "id,customer_id,plate,vin",
    "workorder": "id,vehicle_id,number,status",
    "invoice": "id,work_order_id,number,total",
    "payment": "id,invoice_id,amount",
}


def file_hash(path):
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def business_facts(database):
    result = {}
    with sqlite3.connect(database.as_uri() + "?mode=ro", uri=True) as db:
        db.execute("PRAGMA trusted_schema=OFF")
        for name, columns in TABLES.items():
            rows = db.execute(f"SELECT {columns} FROM workshop_{name} ORDER BY id")
            digest = hashlib.sha256()
            count, total = 0, Decimal(0)
            for row in rows:
                digest.update(json.dumps(row, separators=(",", ":")).encode() + b"\n")
                count += 1
                if name in ("invoice", "payment"):
                    total += Decimal(str(row[-1]))
            result[name] = {"count": count, "sha256": digest.hexdigest()}
            if name in ("invoice", "payment"):
                result[name]["total"] = str(total)
    return result


def copy_portable(source, dest):
    # Copy ordinary files only. Confine inputs before passing them to the application UID.
    if set(p.name for p in source.iterdir()) - {"manifest.json", "workshop.sqlite3", "media"}:
        raise ValueError("Usa la carpeta que contiene el manifiesto portátil y sus dos componentes.")
    dest.mkdir(mode=0o700)
    os.chown(dest, UID, UID)
    for item in source.rglob("*"):
        relative = item.relative_to(source)
        target = dest / relative
        mode = item.lstat().st_mode
        if stat.S_ISDIR(mode):
            target.mkdir(mode=0o700, exist_ok=True)
        elif stat.S_ISREG(mode):
            shutil.copyfile(item, target)
            target.chmod(0o600)
        else:
            raise ValueError("La copia contiene un enlace o un tipo de archivo incompatible.")
        os.chown(target, UID, UID)


def stage(expected):
    import django
    source = Path("/source")
    raw = Path("/work/raw")
    final = Path("/work/final")
    if file_hash(source / "manifest.json") != expected:
        raise ValueError("El SHA-256 del manifiesto difiere del calculado en Windows.")
    raw.mkdir(mode=0o700)
    final.mkdir(mode=0o700)
    django.setup()
    from django.conf import settings
    from django.core.management import call_command
    from django.db import connection, connections
    from django.db.migrations.executor import MigrationExecutor
    from workshop.management.commands.backup_workshop import files_in, validate_backup

    if Path(settings.DATA_DIR) != raw:
        raise ValueError("La importación necesita staging aislado.")
    verified = validate_backup(source)
    if verified["source_mode"] != "live" or verified["synthetic"]:
        raise ValueError("Se requiere un respaldo portátil de la instalación live.")
    original = source / "workshop.sqlite3"
    before = business_facts(original)
    shutil.copyfile(original, raw / original.name)
    media_hashes = {p: h for p, h in verified["files_sha256"].items() if p.startswith("media/")}
    shutil.copytree(source / "media", raw / "media")
    # Work only on a copy. Reject unknown migrations and inconsistent dependencies before upgrading.
    executor = MigrationExecutor(connection)
    applied = set(executor.loader.applied_migrations)
    if applied - set(executor.loader.disk_migrations):
        raise ValueError("La base contiene migraciones de una versión posterior o desconocida.")
    executor.loader.check_consistent_history(connection)
    plan = executor.migration_plan(executor.loader.graph.leaf_nodes())
    if any(backwards for _, backwards in plan):
        raise ValueError("La copia requeriría una migración inversa.")
    call_command("migrate", interactive=False, verbosity=0)
    call_command("backup_workshop", output="/work/compatible", verbosity=0)
    connections.close_all()
    subprocess.run([sys.executable, "manage.py", "restore_workshop", "--input", "/work/compatible", "--confirm-restore"],
                   env={**os.environ, "MILENIO_DATA_DIR": str(final)}, check=True)
    restored = final / "workshop.sqlite3"
    if business_facts(restored) != before:
        raise ValueError("El cotejo de clientes, vehículos, folios o importes difiere del origen.")
    actual_media = {f.relative_to(final).as_posix(): file_hash(f) for f in files_in(final / "media")}
    if actual_media != media_hashes:
        raise ValueError("Los hashes o el número de fotografías cambiaron.")
    with sqlite3.connect(restored.as_uri() + "?mode=ro", uri=True) as db:
        for table in ("workshop_inspection", "workshop_documentcapture"):
            if not db.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name=?", [table]).fetchone():
                continue
            for (photo,) in db.execute(f"SELECT photo FROM {table} WHERE photo IS NOT NULL AND photo <> ''"):
                if "media/" + photo not in actual_media:
                    raise ValueError("Una referencia de fotografía carece de archivo en el respaldo.")
        if db.execute("SELECT COUNT(*) FROM django_session").fetchone()[0]:
            raise ValueError("La recuperación conservó sesiones antiguas.")
    if not (final / ".mail-recovery-hold").is_file():
        raise ValueError("La recuperación carece del bloqueo de correo esperado.")
    result = {"business": before, "media_files": len(actual_media),
              "source_applied": [list(m) for m in sorted(applied)],
              "migrated_forward": [f"{m.app_label}.{m.name}" for m, _ in plan]}
    Path("/work/checked.json").write_text(json.dumps(result), encoding="utf-8")


def install(source_arg, state, expected, release, revision):
    from backup.backup import LOCK, exclusive_lock, receipt
    if not HASH.fullmatch(expected) or not HASH.fullmatch(release) or not REVISION.fullmatch(revision):
        raise ValueError("Ambos identificadores de Windows deben tener 64 dígitos hexadecimales y Git debe indicar el commit completo.")
    source = Path(source_arg)
    if (not source.is_absolute() or source.resolve() != source or not source.is_dir()
            or source.is_relative_to(state) or state.is_relative_to(source)):
        raise ValueError("Selecciona una carpeta privada de respaldo fuera del almacenamiento de la nube.")
    data = state / "app"
    with exclusive_lock(LOCK, inherited=True):
        if data.is_symlink() or not data.is_dir() or any(data.iterdir()) or (state / "ultima-restauracion.json").exists():
            raise ValueError("Se requiere una central nueva con directorio app vacío.")
        if file_hash(source / "manifest.json") != expected:
            raise ValueError("El manifiesto transferido no coincide con el original.")
        # During migration the verified input, working DB, intermediate backup and final DB coexist.
        size = sum(item.lstat().st_size for item in source.rglob("*") if stat.S_ISREG(item.lstat().st_mode))
        if shutil.disk_usage(state).free < size * 6 + 64 * 1024**2:
            raise ValueError("Se requiere espacio temporal para seis copias del respaldo más 64 MiB.")
        with tempfile.TemporaryDirectory(prefix=".import-windows-", dir=state) as tmp:
            temp = Path(tmp)
            portable, work = temp / "source", temp / "work"
            copy_portable(source, portable)
            work.mkdir(mode=0o700)
            os.chown(work, UID, UID)
            subprocess.run(["docker", "run", "--rm", "--network", "none", "--read-only", "--cap-drop", "ALL",
                            "--security-opt", "no-new-privileges", "--user", f"{UID}:{UID}", "--tmpfs", "/tmp:rw,nosuid,nodev",
                            "--mount", f"type=bind,src={portable},dst=/source,readonly",
                            "--mount", f"type=bind,src={work},dst=/work",
                            "-e", "DJANGO_SETTINGS_MODULE=milenio_web.cloud_settings", "-e", "MILENIO_MODE=live",
                            "-e", "MILENIO_CLOUD_HOST=cutover.example.invalid", "-e", "MILENIO_DATA_DIR=/work/raw",
                            f"milenio-taller:{revision}", "python", "-m", "infra.nube.import_windows", "stage", expected], check=True)
            report = json.loads((work / "checked.json").read_text())
            if any(data.iterdir()):
                raise ValueError("El destino se ocupó durante la importación.")
            record = {**report, "kind": "windows-portable", "source_manifest_sha256": expected,
                      "source_release_reported": release, "revision": revision, "completed_unix": time.time()}
            receipt(state, "ultima-importacion-windows", record)
            (work / "final").replace(data)
    print("Copia de Windows cotejada e instalada en destino vacío. Revisa el recibo privado antes de activate-restored.")


def main():
    parser = argparse.ArgumentParser()
    commands = parser.add_subparsers(dest="action", required=True)
    cmd = commands.add_parser("install")
    for name in ("source", "state", "expected", "release", "revision"):
        cmd.add_argument(name)
    commands.add_parser("stage").add_argument("expected")
    args = parser.parse_args()
    if args.action == "stage":
        stage(args.expected)
    else:
        install(args.source, Path(args.state), args.expected, args.release, args.revision)


if __name__ == "__main__":
    main()
