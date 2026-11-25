"""Encrypted offsite backups for the single Milenio cloud instance (Linux host)."""
import argparse
import fcntl
import json
import os
import re
import signal
import stat
import subprocess
import sys
import tempfile
import time
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path

BASE = Path(__file__).resolve().parents[1]
LOCK = Path("/run/lock/milenio-cloud.lock")
WRITERS = ("app", "analytics", "capture")
TAG = "milenio-taller"
HOST = "milenio-cloud"
UID = 10001
HASH = re.compile(r"[0-9a-f]{64}")
REVISION = re.compile(r"[0-9a-f]{40}")
B2 = re.compile(r"s3:https://s3\.[a-z0-9-]+\.backblazeb2\.com/[a-zA-Z0-9-]+(?:/[a-zA-Z0-9_./-]+)?")
KEYS = {"AWS_ACCESS_KEY_ID", "AWS_SECRET_ACCESS_KEY", "AWS_DEFAULT_REGION", "RESTIC_REPOSITORY", "RESTIC_PASSWORD_FILE"}


def private_file(path):
    info = path.lstat()
    if not stat.S_ISREG(info.st_mode) or info.st_uid != 0 or info.st_mode & 0o077:
        raise ValueError(f"{path} debe ser un archivo normal de root con permisos 0600 o 0400")
    return path


def restic_environment(config, sandbox=False):
    # Parse a small data format, never shell-evaluate credentials.
    entries = {}
    for line in private_file(config).read_text().splitlines():
        if not line.strip() or line.lstrip().startswith("#"):
            continue
        key, sep, value = line.partition("=")
        if key not in KEYS or not sep or not value or key in entries or value != value.strip():
            raise ValueError("Entrada no válida o repetida en la configuración privada de restic")
        entries[key] = value
    repo = entries.get("RESTIC_REPOSITORY", "")
    if not (sandbox and Path(repo).is_absolute()):
        if not B2.fullmatch(repo) or ".." in repo.split("/") or not all(entries.get(k) for k in ("AWS_ACCESS_KEY_ID", "AWS_SECRET_ACCESS_KEY", "AWS_DEFAULT_REGION")):
            raise ValueError("Configura un bucket B2 privado mediante S3 HTTPS y su llave de aplicación")
    password_path = Path(entries.get("RESTIC_PASSWORD_FILE", ""))
    if not password_path.is_absolute() or not private_file(password_path).read_text().strip():
        raise ValueError("Falta la contraseña de restic en un archivo privado")
    # Restic also accepts shell/password commands via its environment. Select only intended credentials.
    return {"PATH": os.defpath + ":/usr/local/bin", "HOME": "/root", **entries}


def output(args, env=None):
    return subprocess.check_output(args, text=True, env=env)


def run(args, **kwargs):
    subprocess.run(args, check=True, **kwargs)


@contextmanager
def exclusive_lock(path, inherited=False):
    if inherited:
        given = os.fstat(9)
        expected = path.stat()
        if (given.st_ino, given.st_dev) != (expected.st_ino, expected.st_dev):
            raise ValueError("La actualización debe heredar el descriptor 9 del bloqueo de despliegue")
    with path.open("a") as check:
        if inherited:
            # Separate open-file descriptions must conflict with the deploy parent's existing lock.
            try:
                fcntl.flock(check, fcntl.LOCK_EX | fcntl.LOCK_NB)
            except BlockingIOError:
                fcntl.flock(9, fcntl.LOCK_EX | fcntl.LOCK_NB)
            else:
                raise ValueError("El actualizador no tomó el bloqueo exclusivo")
        else:
            fcntl.flock(check, fcntl.LOCK_EX | fcntl.LOCK_NB)
        yield


class Cloud:
    def __init__(self, env_file):
        self.compose = ["docker", "compose", "--env-file", str(env_file), "-f", str(BASE / "compose.yaml")]
        config = json.loads(output([*self.compose, "config", "--format", "json"]))
        app = config["services"]["app"]
        mounts = [v for v in app["volumes"] if v["type"] == "bind" and v["target"] == "/var/lib/milenio"]
        if len(mounts) != 1:
            raise ValueError("Se requiere un único directorio persistente de la aplicación")
        self.data = Path(mounts[0]["source"])
        if not self.data.is_absolute() or self.data != self.data.resolve() or self.data.name != "app" or self.data.parent == Path("/"):
            raise ValueError("Directorio persistente inesperado")
        self.state = self.data.parent
        self.image = app["image"]
        owners = {s for s, svc in config["services"].items() if any(v.get("source") == str(self.data) and not v.get("read_only") for v in svc.get("volumes", []))}
        if owners != set(WRITERS):
            raise ValueError(f"Los servicios con escritura cambiaron; revisar el respaldo: {sorted(owners)}")

    def writers(self):
        running = []
        for svc in WRITERS:
            ident = output([*self.compose, "ps", "--all", "-q", svc]).strip()
            if not ident:
                continue
            if "\n" in ident:
                raise ValueError("Se requiere una sola instancia por servicio")
            result = json.loads(output(["docker", "inspect", ident]))[0]
            state = result["State"]["Status"]
            if svc == "app":
                self.image = result["Image"]
            if state == "running":
                running.append(svc)
            elif state not in ("created", "exited"):
                raise ValueError(f"{svc} está en transición ({state}); revisa el servicio antes del respaldo")
        return running

    def resume(self, services):
        if not services:
            return
        run([*self.compose, "start", *services])
        for _ in range(60):
            healthy = True
            for svc in services:
                ident = output([*self.compose, "ps", "--all", "-q", svc]).strip()
                state = json.loads(output(["docker", "inspect", ident]))[0]["State"]
                if not state["Running"] or state.get("Health", {}).get("Status", "healthy") != "healthy":
                    healthy = False
            if healthy:
                return
            time.sleep(2)
        raise ValueError("No se recuperó la salud de todos los servicios que estaban funcionando")

    def revision(self):
        revision = output(["docker", "image", "inspect", "--format", '{{index .Config.Labels "org.opencontainers.image.revision"}}', self.image]).strip()
        if not REVISION.fullmatch(revision):
            raise ValueError("Se requiere una imagen identificada con el commit completo de Git")
        return revision

    def job(self, mounts, data_dir, args):
        cli = ["docker", "run", "--rm", "--network", "none", "--read-only", "--cap-drop", "ALL",
               "--security-opt", "no-new-privileges", "--user", f"{UID}:{UID}", "--tmpfs", "/tmp:rw,nosuid,nodev",
               "-e", "DJANGO_SETTINGS_MODULE=milenio_web.cloud_settings", "-e", "MILENIO_MODE=live",
               "-e", "MILENIO_CLOUD_HOST=restore.example.invalid", "-e", f"MILENIO_DATA_DIR={data_dir}"]
        for source, target, mode in mounts:
            cli += ["--volume", f"{source}:{target}:{mode}"]
        run([*cli, self.image, "python", "manage.py", *args])


class Repository:
    def __init__(self, env):
        self.env = env

    def snapshots(self):
        return json.loads(output(["restic", "--no-lock", "snapshots", "--json", "--host", HOST, "--tag", TAG], self.env)) or []

    def select(self, snapshot):
        matches = self.snapshots()
        if snapshot == "latest" and matches:
            return max(matches, key=lambda s: datetime.fromisoformat(s["time"].replace("Z", "+00:00")))
        if not HASH.fullmatch(snapshot):
            raise ValueError("Indica el ID completo de la copia mostrado por list")
        for row in matches:
            if row["id"] == snapshot:
                return row
        raise ValueError("No se encontró esa copia de Milenio")

    def save(self, payload, revision):
        # Relative path and stable host are needed for grouping and predictable recovery paths.
        # Omit progress output: it can contain names of individual evidence files.
        with tempfile.TemporaryFile(mode="w+") as log:
            run(["restic", "backup", "--json", "--host", HOST, "--tag", TAG, "--tag", "git-" + revision, "taller"],
                cwd=payload.parent, env=self.env, stdout=log)
            log.seek(0)
            short_id = next((r["snapshot_id"] for line in log if (r := json.loads(line)).get("message_type") == "summary"), "")
        matches = [r["id"] for r in self.snapshots() if re.fullmatch("[0-9a-f]{8,64}", short_id) and r["id"].startswith(short_id)]
        if len(matches) != 1:
            raise ValueError("Restic terminó sin confirmar un ID único en el repositorio")
        return matches[0]


def receipt(state, name, data):
    path = state / f"{name}.json"
    with tempfile.NamedTemporaryFile("w", dir=state, delete=False) as temp:
        json.dump(data, temp)
        temp.write("\n")
        temp.flush()
        os.fsync(temp.fileno())
    Path(temp.name).replace(path)
    directory = os.open(state, os.O_RDONLY | os.O_DIRECTORY)
    try:
        os.fsync(directory)
    finally:
        os.close(directory)


def create(cloud, repo, temp, before_upgrade=False):
    repo.snapshots()  # Check credentials and connectivity before interrupting the workshop.
    running = cloud.writers()
    if before_upgrade and running:
        raise ValueError("Detener app, analytics y capture antes de la copia de actualización")
    if not (cloud.data / "workshop.sqlite3").is_file():
        raise ValueError("No se encontró la base operativa")
    revision = cloud.revision()
    work = temp / "job"
    work.mkdir(mode=0o700)
    os.chown(work, UID, UID)
    try:
        if running:
            run([*cloud.compose, "stop", "-t", "90", *running])
        if cloud.writers():
            raise ValueError("Aún hay servicios con escritura; se cancela la copia")
        cloud.job([(cloud.data, "/var/lib/milenio", "ro"), (work, "/capture", "rw")], "/var/lib/milenio",
                  ["backup_workshop", "--output", "/capture/taller"])
    finally:
        cloud.resume(running)
    result = repo.save(work / "taller", revision)
    receipt(cloud.state, "ultimo-respaldo", {"snapshot": result, "revision": revision, "completed_unix": time.time()})
    print(f"Copia cifrada confirmada: {result} (Git {revision})")


def recover(cloud, repo, temp, snapshot, fresh):
    pending = cloud.state / ".restic-promocion.json"
    if fresh and HASH.fullmatch(snapshot) and pending.exists() and cloud.data.is_dir():
        prepared = json.loads(private_file(pending).read_text())
        destination = cloud.data.stat()
        if (prepared["snapshot"] == snapshot and prepared["directory"] == [destination.st_dev, destination.st_ino]
                and not cloud.writers() and prepared["revision"] == cloud.revision()):
            # A crash after rename but before publishing the receipt is safe to replay by ID.
            receipt(cloud.state, "ultima-restauracion", prepared)
            pending.unlink()
            print(f"Recuperación ya instalada y recibo confirmado: {snapshot}")
            return
    if fresh and (snapshot == "latest" or cloud.data.exists() and (not cloud.data.is_dir() or any(cloud.data.iterdir()))):
        raise ValueError("restore-new exige ID completo y directorio de datos nuevo y vacío")
    current = cloud.writers()
    if fresh and current:
        raise ValueError("Detener servicios antes de instalar datos recuperados")
    row = repo.select(snapshot)
    revision = cloud.revision()
    if "git-" + revision not in row.get("tags", []):
        raise ValueError(f"Usar imagen del commit indicado en list: {row.get('tags')}")
    downloaded = temp / "download"
    downloaded.mkdir()
    run(["restic", "--no-lock", "restore", row["id"], "--target", str(downloaded)], env=repo.env)
    source = downloaded / "taller"
    if source.is_symlink() or not (source / "manifest.json").is_file():
        raise ValueError("Estructura inesperada en la copia")
    target = temp / "recovery"
    target.mkdir(mode=0o700)
    os.chown(target, UID, UID)
    (target / "app").mkdir(mode=0o700)
    os.chown(target / "app", UID, UID)
    # Isolated job has no active host data, mail credentials or network mounted.
    cloud.job([(source, "/capture", "ro"), (target, "/recovery", "rw")], "/recovery/app",
              ["restore_workshop", "--input", "/capture", "--confirm-restore"])
    result = {"snapshot": row["id"], "revision": revision, "completed_unix": time.time()}
    if fresh:
        if cloud.writers() or cloud.data.exists() and any(cloud.data.iterdir()):
            raise ValueError("El destino se ocupó durante la restauración")
        installed = (target / "app").stat()
        result["directory"] = [installed.st_dev, installed.st_ino]
        receipt(cloud.state, ".restic-promocion", result)
        (target / "app").replace(cloud.data)
    receipt(cloud.state, "ultima-restauracion" if fresh else "ultimo-simulacro", result)
    if fresh:
        pending.unlink()
    print(f"Restauración {'en directorio nuevo' if fresh else 'aislada verificada'}: {row['id']}")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("action", choices=("init", "run", "pre-upgrade", "list", "check", "restore-test", "restore-new", "retention", "prune"))
    parser.add_argument("snapshot", nargs="?")
    args = parser.parse_args()
    if args.snapshot and args.action not in ("restore-test", "restore-new"):
        parser.error("Sólo la restauración acepta un ID")
    if os.geteuid() != 0:
        raise ValueError("Ejecutar con sudo en la central de nube")
    os.umask(0o077)
    test_only = os.environ.get("MILENIO_BACKUP_LOCAL_TEST") == "1"
    env_file = Path(os.environ.get("MILENIO_NUBE_ENV", "/etc/milenio/nube.env"))
    config = Path(os.environ.get("MILENIO_BACKUP_ENV", "/etc/milenio/backup.env"))
    with exclusive_lock(LOCK, inherited=args.action == "pre-upgrade"):
        env = restic_environment(config, test_only)
        repo = Repository(env)
        if args.action == "init":
            run(["restic", "init"], env=env)
        elif args.action == "list":
            for row in repo.snapshots():
                print(row["time"], row["id"], " ".join(row["tags"]))
        elif args.action == "check":
            run(["restic", "check", "--read-data"], env=env)
        elif args.action in ("retention", "prune"):
            flags = ["--prune"] if args.action == "prune" else ["--dry-run"]
            run(["restic", "forget", "--host", HOST, "--tag", TAG, "--group-by", "host", "--keep-last", "3",
                 "--keep-daily", "7", "--keep-weekly", "4", "--keep-monthly", "6", *flags], env=env)
        else:
            cloud = Cloud(env_file)
            with tempfile.TemporaryDirectory(prefix=".milenio-backup-", dir=cloud.state) as tmp:
                if args.action in ("run", "pre-upgrade"):
                    create(cloud, repo, Path(tmp), args.action == "pre-upgrade")
                else:
                    recover(cloud, repo, Path(tmp), args.snapshot or "latest", args.action == "restore-new")


if __name__ == "__main__":
    def terminate(signum, frame):
        raise InterruptedError("El sistema pidió interrumpir el respaldo")

    signal.signal(signal.SIGTERM, terminate)
    try:
        main()
    except (OSError, ValueError, KeyError, subprocess.CalledProcessError) as error:
        sys.exit(f"Respaldo/recuperación interrumpido: {error}")
