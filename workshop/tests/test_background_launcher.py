"""Windows integration checks for the detached PowerShell launcher.

These tests use a disposable demo data directory and isolated launcher config;
they never touch the project's private operational data or launcher settings.
"""
import json
import os
import shutil
import sqlite3
import socket
import subprocess
import time
import unittest
import urllib.error
import urllib.request
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from contextlib import closing
from pathlib import Path
from tempfile import TemporaryDirectory
from threading import Thread


ROOT = Path(__file__).resolve().parents[2]
LAUNCHER = ROOT / "Abrir-Milenio.ps1"
POWERSHELL = shutil.which("powershell.exe") or shutil.which("powershell")


@unittest.skipUnless(os.name == "nt" and POWERSHELL and LAUNCHER.is_file(),
                     "PowerShell detached launcher integration requires Windows")
class BackgroundLauncherTests(unittest.TestCase):
    @staticmethod
    def _free_port():
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as listener:
            listener.bind(("127.0.0.1", 0))
            return listener.getsockname()[1]

    @staticmethod
    def _invoke(*args, timeout=90):
        return subprocess.run(
            [POWERSHELL, "-NoProfile", "-ExecutionPolicy", "Bypass", "-File", str(LAUNCHER), *map(str, args)],
            cwd=ROOT, capture_output=True, text=True, timeout=timeout,
        )

    @staticmethod
    def _health(port):
        with urllib.request.urlopen(f"http://127.0.0.1:{port}/health/", timeout=2) as response:
            if response.status != 200:
                raise AssertionError(f"health returned HTTP {response.status}")
            return json.loads(response.read().decode("utf-8"))

    @staticmethod
    def _stopped(port):
        try:
            urllib.request.urlopen(f"http://127.0.0.1:{port}/health/", timeout=0.5)
        except (OSError, TimeoutError, urllib.error.URLError):
            return True
        return False

    @staticmethod
    def _wait_process_exit(process_id, timeout=15):
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            result = subprocess.run(
                [POWERSHELL, "-NoProfile", "-Command",
                 f"if (Get-Process -Id {int(process_id)} -ErrorAction SilentlyContinue) {{ exit 1 }} else {{ exit 0 }}"],
                capture_output=True, text=True, timeout=5,
            )
            if result.returncode == 0:
                return True
            time.sleep(0.25)
        return False

    def _launcher_args(self, data_dir, config_dir, port):
        return ("-Mode", "demo", "-DataDir", data_dir, "-ConfigDir", config_dir,
                "-Port", str(port), "-NoBrowser", "-SkipSetup")

    @staticmethod
    def _prepare_empty_database(data_dir):
        data_dir.mkdir(parents=True, exist_ok=True)
        connection = sqlite3.connect(data_dir / "workshop.sqlite3")
        connection.close()

    def test_shell_returns_server_stays_ready_rerun_is_idempotent_and_stop_is_graceful(self):
        with TemporaryDirectory(prefix="milenio-background-launcher-") as temporary:
            root = Path(temporary)
            data_dir = root / "data" / "demo"
            config_dir = root / "launcher-config"
            port = self._free_port()
            args = self._launcher_args(data_dir, config_dir, port)
            process_id = None
            try:
                self._prepare_empty_database(data_dir)
                launched = self._invoke(*args, timeout=90)
                self.assertEqual(launched.returncode, 0, launched.stdout + launched.stderr)
                record_path = data_dir / ".launcher.json"
                self.assertTrue(record_path.is_file())
                record = json.loads(record_path.read_text(encoding="utf-8-sig"))
                process_id = record["process_id"]
                launch_id = record["launch_id"]
                self.assertTrue(launch_id)
                self.assertTrue(config_dir.is_dir())
                self.assertEqual(self._health(port), {
                    "status": "ok", "application": "milenio-operations",
                    "mode": "demo", "launch_id": launch_id,
                })

                # The detached server survives the PowerShell command that launched it.
                process_check = subprocess.run(
                    [POWERSHELL, "-NoProfile", "-Command",
                     f"if (Get-Process -Id {int(process_id)} -ErrorAction SilentlyContinue) {{ exit 0 }} else {{ exit 1 }}"],
                    capture_output=True, text=True, timeout=5,
                )
                self.assertEqual(process_check.returncode, 0, "server process exited with launcher shell")

                database = data_dir / "workshop.sqlite3"
                self.assertTrue(database.is_file())
                with closing(sqlite3.connect(database)) as connection:
                    initial_orders = connection.execute("SELECT COUNT(*) FROM workshop_workorder").fetchone()[0]
                    self.assertEqual(initial_orders, 38)

                launched_again = self._invoke(*args, timeout=15)
                self.assertEqual(launched_again.returncode, 0, launched_again.stdout + launched_again.stderr)
                record_again = json.loads(record_path.read_text(encoding="utf-8-sig"))
                self.assertEqual(record_again["launch_id"], launch_id)
                self.assertEqual(record_again["process_id"], process_id)
                with closing(sqlite3.connect(database)) as connection:
                    self.assertEqual(connection.execute("SELECT COUNT(*) FROM workshop_workorder").fetchone()[0], 38)
                    self.assertEqual(connection.execute("SELECT COUNT(*) FROM workshop_customer").fetchone()[0], 4)

                stopped = self._invoke(*args, "-Stop", timeout=15)
                self.assertEqual(stopped.returncode, 0, stopped.stdout + stopped.stderr)
                self.assertTrue(self._stopped(port), "health stayed up after graceful stop")
                self.assertTrue(self._wait_process_exit(process_id), "launcher child process remained alive after stop")
                self.assertTrue(database.is_file(), "stop must retain the demo database")
            finally:
                # Keep the disposable directory intact until the launched process exits.
                if process_id is None:
                    record_path = data_dir / ".launcher.json"
                    if record_path.is_file():
                        process_id = json.loads(record_path.read_text(encoding="utf-8-sig")).get("process_id")
                if process_id is not None and not self._wait_process_exit(process_id, timeout=1):
                    try:
                        self._invoke(*args, "-Stop", timeout=15)
                    except subprocess.SubprocessError:
                        pass
                    if not self._wait_process_exit(process_id, timeout=15):
                        # This exact PID came from our disposable fixture's launch record.
                        subprocess.run(
                            [POWERSHELL, "-NoProfile", "-Command",
                             f"Stop-Process -Id {int(process_id)} -ErrorAction SilentlyContinue"],
                            capture_output=True, text=True, timeout=5,
                        )
                        if not self._wait_process_exit(process_id, timeout=10):
                            raise RuntimeError("could not clean up the test's own launcher child")

    def test_occupied_port_is_rejected_without_stopping_other_service(self):
        class Handler(BaseHTTPRequestHandler):
            def do_GET(self):
                body = b"unrelated service"
                self.send_response(200)
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)

            def log_message(self, format, *args):
                pass

        occupied = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        thread = Thread(target=occupied.serve_forever, daemon=True)
        thread.start()
        try:
            with TemporaryDirectory(prefix="milenio-occupied-port-") as temporary:
                root = Path(temporary)
                data_dir = root / "data" / "demo"
                config_dir = root / "launcher-config"
                self._prepare_empty_database(data_dir)
                db_before = (data_dir / "workshop.sqlite3").read_bytes()
                result = self._invoke(*self._launcher_args(data_dir, config_dir, occupied.server_port), timeout=15)
                self.assertNotEqual(result.returncode, 0, result.stdout + result.stderr)
                self.assertIn("puerto", (result.stdout + result.stderr).casefold())
                self.assertTrue(self._health_response_is_unrelated(occupied.server_port))
                self.assertEqual((data_dir / "workshop.sqlite3").read_bytes(), db_before)
        finally:
            occupied.shutdown()
            occupied.server_close()
            thread.join(timeout=5)

    @staticmethod
    def _health_response_is_unrelated(port):
        with urllib.request.urlopen(f"http://127.0.0.1:{port}/", timeout=2) as response:
            return response.read() == b"unrelated service"

@unittest.skipUnless(os.name == "nt" and POWERSHELL, "Los accesos de escritorio requieren Windows")
class ManagedLauncherTests(unittest.TestCase):
    def setUp(self):
        self.tmp = TemporaryDirectory(prefix="milenio-managed-launcher-")
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.instance = "85b65e9a-5f93-42a6-ba86-ecb73a974566"
        self.health = {"application": "milenio-operations", "mode": "live", "status": "ok",
                       "instance_id": self.instance}
        self.paths = []
        self.redirect = False
        fixture = self

        class Handler(BaseHTTPRequestHandler):
            def do_GET(self):
                fixture.paths.append(self.path)
                if fixture.redirect:
                    self.send_response(302)
                    self.send_header("Location", "/unexpected")
                    self.end_headers()
                    return
                body = json.dumps(fixture.health).encode()
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)

            def log_message(self, *args):
                pass

        self.server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        self.addCleanup(self.server.server_close)
        Thread(target=self.server.serve_forever, daemon=True).start()
        self.addCleanup(self.server.shutdown)
        self.config_path = self.root / "private" / "infra.local.json"
        self.config_path.parent.mkdir()
        self.origin = f"http://127.0.0.1:{self.server.server_port}"
        self.config = {"schema_version": 2, "role": "client", "transport": "ssh-loopback",
                       "expected_hostname": socket.gethostname(), "instance_id": self.instance,
                       "central_url": self.origin, "local_port": self.server.server_port}
        self.env = {**os.environ, "MILENIO_DEPLOYMENT_CONFIG": str(self.config_path),
                    "MILENIO_LEGACY_LOCAL": "", "LOCALAPPDATA": str(self.root / "appdata")}

    def launch(self, section="Taller", launcher=LAUNCHER):
        self.config_path.write_text(json.dumps(self.config), encoding="utf-8-sig")
        return subprocess.run([POWERSHELL, "-NoProfile", "-ExecutionPolicy", "Bypass",
                               "-File", str(launcher), "-Mode", "live", "-Seccion", section, "-NoBrowser"],
                              env=self.env, capture_output=True, text=True, timeout=15)

    def test_client_shortcuts_open_only_configured_tunnel_and_fixed_pages(self):
        self.config_path.write_text(json.dumps(self.config), encoding="utf-8")
        for section, route in (("Taller", "/"), ("Comercial", "/commercial/")):
            result = subprocess.run(["cmd.exe", "/d", "/c", f"Abrir-{section}.cmd", "-NoBrowser"],
                                    cwd=ROOT, env=self.env, stdin=subprocess.DEVNULL,
                                    capture_output=True, text=True, timeout=15)
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            self.assertIn(self.origin + route, result.stdout)
        self.assertEqual(self.paths, ["/health/", "/health/"])
        self.assertFalse((self.root / "appdata").exists())

    def test_release_finds_custom_installation_and_honors_maintenance(self):
        launcher = self.root / "releases" / "0123456789abcdef" / LAUNCHER.name
        launcher.parent.mkdir(parents=True)
        shutil.copyfile(LAUNCHER, launcher)
        self.env.pop("MILENIO_DEPLOYMENT_CONFIG")
        data = self.root / "data" / "live"
        data.mkdir(parents=True)
        self.config.update(role="server", port=self.server.server_port, data_dir=str(data))
        result = self.launch(launcher=launcher)
        self.assertEqual(result.returncode, 0, result.stderr)
        (data / ".stop-managed").touch()
        paused = self.launch(launcher=launcher)
        self.assertNotEqual(paused.returncode, 0)
        self.assertIn("mantenimiento", paused.stderr.lower())
        self.assertEqual(self.paths, ["/health/"])

    def test_rejects_foreign_service_redirect_or_external_origin(self):
        self.health["instance_id"] = "other"
        self.assertNotEqual(self.launch().returncode, 0)
        self.redirect = True
        self.assertNotEqual(self.launch().returncode, 0)
        self.config["central_url"] = "https://invalid.invalid/"
        self.assertNotEqual(self.launch().returncode, 0)
        self.assertEqual(self.paths, ["/health/", "/health/"])
