"""Run the offline Windows installer twice on a disposable central installation."""
import argparse
import hashlib
import http.client
import json
import os
from pathlib import Path
import socket
import subprocess
import sys
import tempfile
import zipfile


def read_json(path):
    return json.loads(path.read_text(encoding="utf-8-sig"))


def require(condition, message):
    if not condition:
        raise RuntimeError(message)


def check_health(port, config):
    connection = http.client.HTTPConnection("127.0.0.1", port, timeout=5)
    try:
        connection.request("GET", "/health/")
        response = connection.getresponse()
        require(response.status == 200, "Health check did not return HTTP 200")
        result = json.loads(response.read(65536))
    finally:
        connection.close()
    require(result.get("application") == "milenio-operations" and result.get("mode") == "live"
            and result.get("status") == "ok" and result.get("supervisor_recent"), "Incorrect application health")
    require(result.get("instance_id") == config["instance_id"] and result.get("release_id") == config["release_id"],
            "Running server differs from the installed identity or release")


def verify(archive):
    if os.name != "nt":
        raise RuntimeError("Windows-only rehearsal")
    with Path(archive).open("rb") as handle:
        package_digest = hashlib.file_digest(handle, "sha256").hexdigest()
    with tempfile.TemporaryDirectory(prefix="mi-") as temporary:
        root = Path(temporary)
        source, target = root / "source", root / "server"
        with zipfile.ZipFile(archive) as bundle:
            for name in bundle.namelist():
                if Path(name).is_absolute() or ".." in Path(name).parts or ":" in name or "\\" in name:
                    raise ValueError("Unsafe package path")
            bundle.extractall(source)
        env = {key: value for key, value in os.environ.items() if not key.startswith("MILENIO_")}
        env.update(PYTHONUTF8="1", PIP_NO_INDEX="1", PIP_DISABLE_PIP_VERSION_CHECK="1")
        setup = ["powershell.exe", "-NoProfile", "-ExecutionPolicy", "Bypass", "-File", str(source / "Setup-Server.ps1"),
                 "-InstallRoot", str(target), "-PythonPath", sys._base_executable, "-Offline"]
        with socket.socket() as available:
            available.bind(("127.0.0.1", 0))
            port = available.getsockname()[1]
        require(port != 8770, "Expected a non-default test port")
        config_path = target / "private/infra.local.json"
        pointer_path = target / "private/current.json"
        data = target / "data/live"

        def install(trial, arguments, expected_error=None):
            # A spawned supervisor can inherit console handles. A file permits the installer to exit independently.
            print(f"Running offline installer rehearsal: {trial}", file=sys.stderr, flush=True)
            log = root / f"install-{trial}.log"
            with log.open("wb") as output:
                proc = subprocess.run(setup + arguments, cwd=source, env=env, stdout=output,
                                      stderr=subprocess.STDOUT, timeout=360)
            diagnostic = log.read_text(encoding="utf-8", errors="replace")[-5000:].replace(str(root), "<synthetic>")
            if expected_error:
                require(proc.returncode != 0 and expected_error in diagnostic, f"Unexpected result: {diagnostic}")
            else:
                require(proc.returncode == 0, f"Installer failed: {diagnostic}")

        install("stopped", ["-Port", str(port), "-NoStart"])
        first = read_json(config_path)
        pointer = read_json(pointer_path)
        release = Path(pointer["release_dir"]).resolve()
        require(release.is_relative_to((target / "releases").resolve()) and Path(first["data_dir"]).resolve() == data.resolve(),
                "Installer did not select the disposable paths")
        require(first["port"] == port and first["release_id"] == pointer["release_id"], "Initial configuration mismatch")
        require((data / ".stop-managed").is_file() and (data / "workshop.sqlite3").is_file()
                and first["mail_worker_allowed"] is False, "First installation did not remain stopped with mail disabled")
        try:
            install("start", [])
            second = read_json(config_path)
            require(second["instance_id"] == first["instance_id"] and second["release_id"] == first["release_id"]
                    and second["port"] == port and second["mail_worker_allowed"] is False,
                    "Repeat installation changed identity, release, port or mail setting")
            check_health(port, first)
            install("wrong-port", ["-Port", "8770"], "puerto indicado difiere")
            check_health(port, first)
        finally:
            # Stop using only this run's private config and the paths it created.
            config = read_json(config_path)
            require(config["instance_id"] == first["instance_id"] and Path(config["data_dir"]).resolve() == data.resolve(),
                    "Refusing to stop an unrelated instance")
            stop_env = {**env, "MILENIO_DEPLOYMENT_CONFIG": str(config_path)}
            subprocess.run([str(release / ".venv/Scripts/python.exe"), str(release / "scripts/deploy.py"), "stop"],
                           cwd=release, env=stop_env, check=True, timeout=90)
        require((data / ".stop-managed").is_file(), "Stop did not preserve the maintenance latch")
        return {"status": "pass", "package_sha256": package_digest, "powershell_installer": True,
                "offline_dependencies": len(list((source / ".runtime/wheels").glob("*.whl"))),
                "repeat_preserves_identity": True, "repeat_preserves_custom_port": True,
                "live_health_matches_instance_and_release": True, "wrong_port_rejected_while_serving": True,
                "temporary_supervisor_started_and_stopped": True, "changes_firewall_or_startup": False,
                "scope": "disposable Windows installation; no external network or production services"}


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--package", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    result = verify(Path(args.package).resolve())
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result))
