"""Disposable backup/restore checks; no test touches a real workshop database."""
import io
import http.client
import hashlib
import json
import os
import shutil
import socket
import sqlite3
import subprocess
import sys
import tempfile
import time
import unittest
import urllib.request
import zipfile
from contextlib import closing, redirect_stderr
from decimal import Decimal
from pathlib import Path
from unittest import mock

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "milenio_web.settings")
import django
django.setup()

from django.core.management import call_command
from django.core.management.base import CommandError
from django.test import override_settings

from workshop.management.commands.backup_workshop import instance_lock
from scripts import package_web, run_web


class RecoveryTests(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.root = Path(temp.name)
        self.data = self.root / "private" / "operational" / "test"
        self.data.mkdir(parents=True)
        self.db = self.data / "workshop.sqlite3"
        self.media = self.data / "media"
        self.media.mkdir()
        (self.media / "evidence").mkdir()
        (self.media / "evidence" / "photo.txt").write_text("synthetic-media", encoding="utf-8")
        self.secret = self.data / ".secret_key"
        self.secret.write_text("instance-secret", encoding="utf-8")
        with closing(sqlite3.connect(self.db)) as con:
            con.executescript("""
                CREATE TABLE django_migrations (id INTEGER PRIMARY KEY, app TEXT, name TEXT);
                CREATE TABLE django_session (session_key TEXT PRIMARY KEY, session_data TEXT, expire_date TEXT);
                CREATE TABLE auth_user (id INTEGER PRIMARY KEY, username TEXT);
                CREATE TABLE workshop_workorder (id INTEGER PRIMARY KEY, number TEXT);
                CREATE TABLE workshop_invoice (id INTEGER PRIMARY KEY, work_order_id INTEGER, total TEXT);
                CREATE TABLE workshop_payment (id INTEGER PRIMARY KEY, invoice_id INTEGER, amount TEXT);
                INSERT INTO workshop_workorder(id,number) VALUES(1,'WO-SYN-1');
                INSERT INTO workshop_invoice(id,work_order_id,total) VALUES(1,1,'1000.00');
                INSERT INTO workshop_payment(id,invoice_id,amount) VALUES(1,1,'300.00');
                INSERT INTO django_session(session_key,session_data,expire_date) VALUES('old-session','secret','2026-09-30');
            """)
            for migration in sorted((Path(__file__).resolve().parents[1] / "migrations").glob("[0-9][0-9][0-9][0-9]_*.py")):
                con.execute("INSERT INTO django_migrations(app,name) VALUES(?,?)", ("workshop", migration.stem))
            con.commit()
        replacement = {"default": {"ENGINE": "django.db.backends.sqlite3", "NAME": self.db}}
        settings_context = override_settings(DATA_DIR=self.data, DATABASES=replacement,
                                             MEDIA_ROOT=self.media, MILENIO_MODE="test")
        settings_context.enable()
        self.addCleanup(settings_context.disable)

    def _backup(self):
        backup = self.root / "backup"
        call_command("backup_workshop", output=str(backup), stdout=io.StringIO())
        return backup

    def _number(self):
        with closing(sqlite3.connect(self.db)) as con:
            return con.execute("SELECT number FROM workshop_workorder WHERE id=1").fetchone()[0]

    @staticmethod
    def _financial_snapshot(database):
        with closing(sqlite3.connect(database)) as con:
            counts = {table: con.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
                      for table in ("workshop_workorder", "workshop_invoice", "workshop_payment")}
            billed = sum((Decimal(value) for (value,) in con.execute("SELECT total FROM workshop_invoice")), Decimal("0"))
            paid = sum((Decimal(value) for (value,) in con.execute("SELECT amount FROM workshop_payment")), Decimal("0"))
        return counts, billed, paid, billed - paid

    def test_restore_into_separate_instance_preserves_counts_and_partial_balance(self):
        expected = self._financial_snapshot(self.db)
        self.assertEqual(expected, ({"workshop_workorder": 1, "workshop_invoice": 1,
                                     "workshop_payment": 1}, Decimal("1000.00"),
                                    Decimal("300.00"), Decimal("700.00")))
        backup = self._backup()
        destination = self.root / "other_instance" / "test"
        destination.mkdir(parents=True)
        destination_db = destination / "workshop.sqlite3"
        shutil.copy2(self.db, destination_db)
        destination_media = destination / "media"
        destination_media.mkdir()
        (destination_media / "obsolete.txt").write_text("old", encoding="utf-8")
        (destination / ".secret_key").write_text("destination-secret", encoding="utf-8")
        with closing(sqlite3.connect(destination_db)) as con:
            con.execute("UPDATE workshop_invoice SET total='80.00'")
            con.execute("DELETE FROM workshop_payment")
            con.commit()
        target_settings = {"default": {"ENGINE": "django.db.backends.sqlite3", "NAME": destination_db}}
        with override_settings(DATA_DIR=destination, DATABASES=target_settings,
                               MEDIA_ROOT=destination_media, MILENIO_MODE="test"):
            call_command("restore_workshop", input=str(backup), confirm_restore=True, stdout=io.StringIO())
        self.assertEqual(self._financial_snapshot(destination_db), expected)
        self.assertEqual((destination_media / "evidence" / "photo.txt").read_text(encoding="utf-8"), "synthetic-media")
        self.assertFalse((destination_media / "obsolete.txt").exists())
        self.assertEqual((destination / ".secret_key").read_text(encoding="utf-8"), "destination-secret")
        with closing(sqlite3.connect(destination_db)) as con:
            self.assertEqual(con.execute("SELECT COUNT(*) FROM django_session").fetchone()[0], 0)
        self.assertEqual(len(list(destination.glob("recovery-before-*/workshop.sqlite3"))), 1)

    def test_consistent_backup_and_restore_preserve_previous_and_clear_sessions(self):
        backup = self._backup()
        manifest = json.loads((backup / "manifest.json").read_text(encoding="utf-8"))
        self.assertIn("workshop.sqlite3", manifest["files_sha256"])
        self.assertIn("media/evidence/photo.txt", manifest["files_sha256"])
        self.assertNotIn(".secret_key", manifest["files_sha256"])
        with closing(sqlite3.connect(self.db)) as con:
            con.execute("UPDATE workshop_workorder SET number='WO-CHANGED' WHERE id=1")
            con.commit()
        (self.media / "evidence" / "photo.txt").write_text("changed-media", encoding="utf-8")
        call_command("restore_workshop", input=str(backup), confirm_restore=True, stdout=io.StringIO())
        self.assertEqual(self._number(), "WO-SYN-1")


        self.assertEqual((self.media / "evidence" / "photo.txt").read_text(encoding="utf-8"), "synthetic-media")
        self.assertEqual(self.secret.read_text(encoding="utf-8"), "instance-secret")
        with closing(sqlite3.connect(self.db)) as con:
            self.assertEqual(con.execute("SELECT COUNT(*) FROM django_session").fetchone()[0], 0)
        previous = list(self.data.glob("recovery-before-*/workshop.sqlite3"))
        self.assertEqual(len(previous), 1)
        with closing(sqlite3.connect(previous[0])) as con:
            self.assertEqual(con.execute("SELECT number FROM workshop_workorder WHERE id=1").fetchone()[0], "WO-CHANGED")

    def test_explicit_confirmation_and_tamper_required_before_active_change(self):
        backup = self._backup()
        with self.assertRaisesRegex(CommandError, "confirm-restore"):
            call_command("restore_workshop", input=str(backup), stdout=io.StringIO())
        (backup / "workshop.sqlite3").write_bytes(b"tampered")
        with self.assertRaisesRegex(CommandError, "manifest hashes"):
            call_command("restore_workshop", input=str(backup), confirm_restore=True, stdout=io.StringIO())
        self.assertEqual(self._number(), "WO-SYN-1")
        self.assertEqual(list(self.data.glob("recovery-before-*")), [])

    def test_traversal_and_server_lock_rejected(self):
        backup = self._backup()
        with self.assertRaisesRegex(CommandError, "traversal"):
            call_command("restore_workshop", input=str(self.root / "child" / ".." / "backup"),
                         confirm_restore=True, stdout=io.StringIO())
        with instance_lock(self.data):
            with self.assertRaisesRegex(CommandError, "lock is held"):
                call_command("restore_workshop", input=str(backup), confirm_restore=True, stdout=io.StringIO())
        self.assertEqual(self._number(), "WO-SYN-1")

    def test_mode_mismatch_and_extra_backup_file_rejected(self):
        backup = self._backup()
        manifest_path = backup / "manifest.json"
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        manifest["source_mode"] = "demo"
        manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
        with self.assertRaisesRegex(CommandError, "mode differs"):
            call_command("restore_workshop", input=str(backup), confirm_restore=True, stdout=io.StringIO())
        manifest["source_mode"] = "test"
        manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
        (backup / "unexpected.txt").write_text("outside manifest", encoding="utf-8")
        with self.assertRaisesRegex(CommandError, "Unexpected backup file"):
            call_command("restore_workshop", input=str(backup), confirm_restore=True, stdout=io.StringIO())
        self.assertEqual(self._number(), "WO-SYN-1")

    def test_changed_schema_with_updated_hash_is_rejected_before_replace(self):
        backup = self._backup()
        with closing(sqlite3.connect(backup / "workshop.sqlite3")) as con:
            con.execute("CREATE TABLE unexpected_schema(id INTEGER PRIMARY KEY)")
            con.commit()
        manifest_path = backup / "manifest.json"
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        manifest["files_sha256"]["workshop.sqlite3"] = hashlib.sha256((backup / "workshop.sqlite3").read_bytes()).hexdigest()
        manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
        with self.assertRaisesRegex(CommandError, "schema does not match"):
            call_command("restore_workshop", input=str(backup), confirm_restore=True, stdout=io.StringIO())
        self.assertEqual(self._number(), "WO-SYN-1")

    def test_corrupt_database_with_updated_hash_is_rejected_before_replace(self):
        backup = self._backup()
        (backup / "workshop.sqlite3").write_bytes(b"not a sqlite database")
        manifest_path = backup / "manifest.json"
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        manifest["files_sha256"]["workshop.sqlite3"] = hashlib.sha256((backup / "workshop.sqlite3").read_bytes()).hexdigest()
        manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
        with self.assertRaisesRegex(CommandError, "Could not inspect SQLite"):
            call_command("restore_workshop", input=str(backup), confirm_restore=True, stdout=io.StringIO())
        self.assertEqual(self._number(), "WO-SYN-1")


class WebDeliveryTests(unittest.TestCase):
    @staticmethod
    def _unused_local_port():
        with socket.socket() as probe:
            probe.bind(("127.0.0.1", 0))
            return probe.getsockname()[1]

    def _stop_server(self, process):
        try:
            process.stdin.close()
            self.assertEqual(process.wait(timeout=15), 0)
        finally:
            if process.poll() is None:
                process.terminate()
                process.wait(timeout=10)
            process.stdout.close()

    def test_live_and_demo_cookies_do_not_clobber_each_other_on_localhost(self):
        cookie_pairs = []
        with tempfile.TemporaryDirectory() as temporary:
            for mode in ("live", "demo"):
                environment = dict(os.environ, MILENIO_MODE=mode,
                                   MILENIO_DATA_DIR=str(Path(temporary) / mode))
                result = subprocess.run([sys.executable, "-c",
                    "from milenio_web.settings import SESSION_COOKIE_NAME,CSRF_COOKIE_NAME; print(SESSION_COOKIE_NAME,CSRF_COOKIE_NAME)"],
                    cwd=run_web.ROOT, env=environment, capture_output=True, text=True, check=True, timeout=30)
                cookie_pairs.extend(result.stdout.strip().split())
        self.assertEqual(len(cookie_pairs), 4)
        self.assertEqual(len(set(cookie_pairs)), 4, "Localhost cookies must be isolated between live and demo")

    def test_missing_localappdata_falls_back_to_user_local_folder(self):
        from milenio_web import settings as web_settings
        with tempfile.TemporaryDirectory() as temp:
            with mock.patch.dict(os.environ, {"LOCALAPPDATA": "", "XDG_DATA_HOME": ""}), mock.patch.object(
                web_settings.Path, "home", return_value=Path(temp)
            ):
                expected = Path(temp) / "AppData" / "Local" if os.name == "nt" else Path(temp) / ".local" / "share"
                self.assertEqual(web_settings.default_data_root(), expected)

    def test_default_settings_use_local_appdata_for_each_mode(self):
        with tempfile.TemporaryDirectory() as temp:
            for mode in ("live", "demo"):
                environment = dict(os.environ)
                environment.pop("MILENIO_DATA_DIR", None)
                environment["LOCALAPPDATA"] = temp
                environment["XDG_DATA_HOME"] = temp
                environment["MILENIO_MODE"] = mode
                result = subprocess.run(
                    [sys.executable, "-c", "from milenio_web.settings import DATA_DIR; print(DATA_DIR)"],
                    cwd=run_web.ROOT, env=environment, capture_output=True, text=True, check=True,
                )
                expected = Path(temp) / "Milenio" / "operational" / mode
                self.assertEqual(Path(result.stdout.strip()).resolve(), expected.resolve())
                self.assertTrue((expected / ".secret_key").is_file())
                self.assertFalse((expected / "workshop.sqlite3").exists())

    def test_runner_stops_before_new_empty_instance_when_legacy_database_exists(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            legacy = root / "private" / "operational" / "live" / "workshop.sqlite3"
            legacy.parent.mkdir(parents=True)
            legacy.write_bytes(b"old database fixture")
            with mock.patch.object(run_web, "ROOT", root), mock.patch.object(
                run_web.sys, "prefix", str(root / ".venv")
            ), mock.patch.dict(os.environ, {"LOCALAPPDATA": str(root / "AppData" / "Local"),
                                         "XDG_DATA_HOME": str(root / ".local" / "share"),
                                         "MILENIO_DATA_DIR": ""}):
                with self.assertRaisesRegex(RuntimeError, "No se trasladó ni borró"):
                    run_web.run("live", no_browser=True)
            self.assertEqual(legacy.read_bytes(), b"old database fixture")
            local_root = root / "AppData" / "Local" if os.name == "nt" else root / ".local" / "share"
            self.assertFalse((local_root / "Milenio" / "operational" / "live").exists())

    def test_runner_reports_management_error_without_traceback(self):
        output = io.StringIO()
        with mock.patch.object(run_web, "run", side_effect=CommandError("migration failed")):
            with redirect_stderr(output):
                status = run_web.main(["--mode", "live", "--no-browser"])
        self.assertEqual(status, 1)
        self.assertIn("migration failed", output.getvalue())

    def test_disposable_demo_seeds_once_without_reset(self):
        port = self._unused_local_port()
        with tempfile.TemporaryDirectory() as temp:
            environment = dict(os.environ)
            environment["MILENIO_DATA_DIR"] = str(Path(temp) / "demo")
            environment.pop("MILENIO_MODE", None)
            database = Path(temp) / "demo" / "workshop.sqlite3"
            for run_number in (1, 2):
                kwargs = {"creationflags": getattr(subprocess, "CREATE_NO_WINDOW", 0)} if os.name == "nt" else {}
                process = subprocess.Popen([sys.executable, str(run_web.ROOT / "scripts" / "run_web.py"),
                                            "--mode", "demo", "--no-browser", "--port", str(port), "--watch-parent"], cwd=run_web.ROOT,
                                           env=environment, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                                           text=True, **kwargs)
                try:
                    ready = False
                    for _ in range(80):
                        if process.poll() is not None:
                            break
                        try:
                            with urllib.request.urlopen(f"http://127.0.0.1:{port}/health/", timeout=0.5) as response:
                                ready = response.status == 200
                            if ready:
                                break
                        except (OSError, TimeoutError):
                            time.sleep(0.25)
                    if not ready:
                        output = process.stdout.read() if process.poll() is not None else "demo server did not become ready"
                        self.fail(output)
                    with closing(sqlite3.connect(database)) as con:
                        self.assertEqual(con.execute("SELECT COUNT(*) FROM workshop_customer").fetchone()[0], 4)
                        self.assertEqual(con.execute("SELECT COUNT(*) FROM workshop_workorder").fetchone()[0], 38)
                        self.assertEqual(con.execute("SELECT COUNT(*) FROM auth_user WHERE username='demo_admin' AND is_active=1").fetchone()[0], 0)
                finally:
                    self._stop_server(process)

    def test_disposable_live_launcher_serves_health_and_static(self):
        port = self._unused_local_port()
        with tempfile.TemporaryDirectory() as temp:
            environment = dict(os.environ)
            environment["MILENIO_DATA_DIR"] = str(Path(temp) / "live")
            environment.pop("MILENIO_MODE", None)
            kwargs = {"creationflags": getattr(subprocess, "CREATE_NO_WINDOW", 0)} if os.name == "nt" else {}
            process = subprocess.Popen([sys.executable, str(run_web.ROOT / "scripts" / "run_web.py"),
                                        "--mode", "live", "--no-browser", "--port", str(port),
                                        "--stop-file", str(Path(temp) / "live" / ".stop-test")], cwd=run_web.ROOT,
                                       env=environment, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                                       text=True, **kwargs)
            persistent = http.client.HTTPConnection("127.0.0.1", port, timeout=2)
            try:
                ready = False
                for _ in range(80):
                    if process.poll() is not None:
                        break
                    try:
                        with urllib.request.urlopen(f"http://127.0.0.1:{port}/health/", timeout=0.5) as response:
                            ready = response.status == 200
                        if ready:
                            break
                    except (OSError, TimeoutError):
                        time.sleep(0.25)
                if not ready:
                    output = process.stdout.read() if process.poll() is not None else "server did not become ready"
                    self.fail(output)
                with urllib.request.urlopen(f"http://127.0.0.1:{port}/static/workshop/app.css", timeout=2) as response:
                    self.assertEqual(response.status, 200)
                    self.assertIn("text/css", response.headers["Content-Type"])
                persistent.request("GET", "/health/")
                response = persistent.getresponse()
                self.assertEqual(response.status, 200)
                response.read()
                self.assertIsNotNone(persistent.sock)
                self.assertTrue((Path(temp) / "live" / "workshop.sqlite3").is_file())
            finally:
                (Path(temp) / "live" / ".stop-test").write_text("stop")
                try:
                    self.assertEqual(process.wait(timeout=15), 0)
                finally:
                    persistent.close()
                    self._stop_server(process)
            self.assertTrue((Path(temp) / "live" / "workshop.sqlite3").exists())
            self.assertFalse((Path(temp) / "live" / ".stop-test").exists())

    def test_runner_rejects_cross_mode_data_directory(self):
        with tempfile.TemporaryDirectory() as temp:
            with mock.patch.dict(os.environ, {"MILENIO_DATA_DIR": str(Path(temp) / "live")}):
                with self.assertRaisesRegex(RuntimeError, "carpetas separadas"):
                    run_web.run("demo", no_browser=True)

    def test_web_package_manifest_and_private_exclusion(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            for name in (*package_web.ROOT_FILES, *package_web.OTHER_FILES,
                         "workshop/models.py", "workshop/static/workshop/app.css", "milenio_web/settings.py",
                         "workshop/private/client.sqlite3", "private/operational/live/workshop.sqlite3"):
                file = root / name
                file.parent.mkdir(parents=True, exist_ok=True)
                file.write_text("test fixture", encoding="utf-8")
            output = root / "web.zip"
            with mock.patch.object(package_web, "ROOT", root):
                result = package_web.build(output)
            self.assertEqual(result["publication_status"], "local_candidate")
            with zipfile.ZipFile(output) as archive:
                manifest = json.loads(archive.read(package_web.MANIFEST))
                self.assertFalse(manifest["includes_private_data"])
                self.assertNotIn("private/operational/live/workshop.sqlite3", archive.namelist())
                self.assertNotIn("workshop/private/client.sqlite3", archive.namelist())
                self.assertIn("workshop/static/workshop/app.css", archive.namelist())
                self.assertEqual(set(manifest["entries_sha256"]), set(archive.namelist()) - {package_web.MANIFEST})
                for name, expected in manifest["entries_sha256"].items():
                    self.assertEqual(hashlib.sha256(archive.read(name)).hexdigest(), expected)

    def test_web_wheelhouse_requires_exact_pinned_windows_312_set(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            (root / "requirements-web.txt").write_text(
                "Django==5.2.17\nasgiref==3.12.1\nsqlparse==0.6.0\ntzdata==2026.4\n"
                "waitress==3.0.2\nPillow==12.3.0\n", encoding="utf-8")
            wheels = root / "wheels"
            wheels.mkdir()
            names = ["django-5.2.17-py3-none-any.whl", "asgiref-3.12.1-py3-none-any.whl",
                     "sqlparse-0.6.0-py3-none-any.whl", "tzdata-2026.4-py2.py3-none-any.whl",
                     "waitress-3.0.2-py3-none-any.whl", "pillow-12.3.0-cp312-cp312-win_amd64.whl"]
            for name in names:
                (wheels / name).write_bytes(b"wheel fixture")
            with mock.patch.object(package_web, "ROOT", root):
                self.assertEqual(len(package_web._wheels(wheels)), 6)
                (wheels / names[-1]).rename(wheels / "pillow-12.3.0-cp313-cp313-win_amd64.whl")
                with self.assertRaisesRegex(ValueError, "not compatible"):
                    package_web._wheels(wheels)
                (wheels / "pillow-12.3.0-cp313-cp313-win_amd64.whl").rename(wheels / names[-1])
                (wheels / names[0]).unlink()
                with self.assertRaisesRegex(ValueError, "does not match"):
                    package_web._wheels(wheels)

    def test_static_handler_serves_only_workshop_assets(self):
        with tempfile.TemporaryDirectory() as temp:
            static = Path(temp) / "workshop"
            static.mkdir()
            (static / "app.css").write_text("body{color:#123}", encoding="utf-8")
            statuses = []
            def start(status, headers):
                statuses.append(status)
            def downstream(environ, response):
                response("200 OK", [])
                return [b"app"]
            with mock.patch.object(run_web, "STATIC_DIR", static):
                handler = run_web.WorkshopStatic(downstream)
                self.assertEqual(b"".join(handler({"PATH_INFO": "/static/workshop/app.css"}, start)), b"body{color:#123}")
                self.assertEqual(statuses[-1], "200 OK")
                self.assertEqual(b"".join(handler({"PATH_INFO": "/static/workshop/../secret"}, start)), b"Not Found")
                self.assertEqual(statuses[-1], "404 Not Found")
                self.assertEqual(b"".join(handler({"PATH_INFO": "/"}, start)), b"app")


if __name__ == "__main__":
    unittest.main()
