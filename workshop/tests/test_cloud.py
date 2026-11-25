"""Cloud boundaries using temporary data and synthetic users only."""
from concurrent.futures import ThreadPoolExecutor
from io import StringIO
from pathlib import Path
import tempfile
from types import SimpleNamespace
from unittest.mock import patch

from django.contrib.auth.models import Group, User
from django.core.management import call_command, CommandError
from django.test import TestCase, override_settings

from commercial.gmail import GmailClient, token_request
from milenio_web.login_limit import release_success, reserve_login
from workshop import models as m
from workshop.document_capture import process_one
from workshop.tests.test_document_capture import photo


@override_settings(MILENIO_CLOUD=True, ROOT_URLCONF="milenio_web.cloud_urls")
class CloudTests(TestCase):
    def setUp(self):
        directory = self.enterContext(tempfile.TemporaryDirectory())
        self.enterContext(override_settings(DATA_DIR=Path(directory), MEDIA_ROOT=Path(directory) / "media"))

    def test_fresh_site_ready_but_manager_cannot_be_claimed_via_web(self):
        self.assertEqual(self.client.get("/health/").json(), {"status": "ok"})
        self.assertEqual(self.client.get("/setup/").status_code, 404)
        self.assertEqual(self.client.post("/setup/", {"username": "someone"}).status_code, 404)
        self.assertEqual(self.client.get("/login/").status_code, 503)
        self.assertFalse(User.objects.exists())
        with patch("sys.stdin.isatty", return_value=False), self.assertRaises(CommandError):
            call_command("cloud_manager", "encargada")
        with patch("sys.stdin.isatty", return_value=True), patch("builtins.input", return_value="Encargada"), \
                patch("getpass.getpass", return_value="Muestra-de-acceso-52714"):
            call_command("cloud_manager", "encargada", stdout=StringIO())
            with self.assertRaisesRegex(CommandError, "Ya existe"):
                call_command("cloud_manager", "otra")
        user = User.objects.get()
        self.assertTrue(user.is_superuser and user.groups.filter(name="manager").exists())
        self.assertEqual(self.client.post("/login/", {"username": "encargada", "password": "Muestra-de-acceso-52714"}).status_code, 302)

    def test_account_and_photos_stay_usable_while_external_surfaces_are_closed(self):
        manager = User.objects.create_superuser("operadora")
        self.client.force_login(manager)
        for url in ("/", "/orders/", "/commercial/", "/capture/", "/team/"):
            self.assertEqual(self.client.get(url).status_code, 200, url)
        for url in ("/commercial/mail/", "/agent/v1/action", "/capture/ai/"):
            self.assertEqual(self.client.get(url).status_code, 404, url)
        self.assertNotContains(self.client.get("/capture/"), 'href="/capture/ai/"')
        denied = self.client.post("/capture/", {"provider": "codex", "photo": photo()})
        self.assertEqual(denied.status_code, 200)
        self.assertFalse(m.DocumentCapture.objects.exists())
        self.assertEqual(self.client.post("/capture/", {"provider": "local", "photo": photo()}).status_code, 302)
        capture = m.DocumentCapture.objects.get()
        with patch("workshop.document_capture.subprocess.run", return_value=SimpleNamespace(returncode=0, stdout="Placas: QA123")) as ocr:
            self.assertTrue(process_one())
        self.assertEqual(ocr.call_args.args[0][0], "/usr/bin/tesseract")
        self.assertEqual(ocr.call_args.args[0][-2:], ["-l", "spa"])
        capture.refresh_from_db()
        self.assertEqual(capture.data["vehicle_plate"], "QA123")
        self.assertEqual(capture.extraction["model"], "tesseract-spa")
        photo_url = f"/capture/{capture.pk}/photo/"
        response = self.client.get(photo_url)
        self.assertEqual(response.status_code, 200)
        response.close()
        self.client.logout()
        self.assertRedirects(self.client.get(photo_url), "/login/", fetch_redirect_response=False)

    def test_manager_and_evidence_require_proper_role_after_login(self):
        User.objects.create_superuser("gerencia")
        self.assertRedirects(self.client.get("/team/"), "/login/", fetch_redirect_response=False)
        member = User.objects.create_user("sin-rol")
        self.client.force_login(member)
        self.assertEqual(self.client.get("/today/").status_code, 403)
        self.assertEqual(self.client.get("/inspection/1/photo/").status_code, 403)
        self.assertEqual(self.client.get("/account/").status_code, 200)
        member.groups.add(Group.objects.create(name="technician"))
        self.assertEqual(self.client.get("/today/").status_code, 200)
        self.assertEqual(self.client.get("/team/").status_code, 403)
        self.assertEqual(self.client.get("/capture/1/photo/").status_code, 403)

    def test_restored_external_queue_cannot_invoke_paid_ai_or_gmail(self):
        self.client.force_login(User.objects.create_superuser("gerencia"))
        self.client.post("/capture/", {"provider": "local", "photo": photo()})
        m.DocumentCapture.objects.update(provider="codex", model_name="gpt-6-luna")
        with patch("workshop.capture_vision.extract_photo") as external:
            self.assertTrue(process_one())
            external.assert_not_called()
        self.assertEqual(m.DocumentCapture.objects.get().status, "review")
        with patch("commercial.gmail.urlopen") as request:
            with self.assertRaises(RuntimeError):
                GmailClient(access_token="synthetic")
            with self.assertRaises(RuntimeError):
                token_request({})
            with self.assertRaises(CommandError):
                call_command("run_mail", once=True)
            request.assert_not_called()

    def test_login_reservations_serialize_across_connections_and_expire(self):
        with patch("milenio_web.login_limit.time.time", return_value=1000):
            with ThreadPoolExecutor(max_workers=4) as pool:
                reservations = list(pool.map(reserve_login, ["192.0.2.1"] * 16))
            waits = [wait for _, wait in reservations]
            self.assertEqual(waits.count(0), 10)
            self.assertEqual(waits.count(300), 6)
            self.assertEqual(reserve_login("192.0.2.2")[1], 0)
            User.objects.create_superuser("encargada")
            response = self.client.post("/login/", {"username":"test"}, REMOTE_ADDR="192.0.2.1")
            self.assertEqual(response.status_code, 429)
            self.assertEqual(response["Retry-After"], "300")
            release_success(next(token for token, wait in reservations if not wait))
            self.assertEqual(reserve_login("192.0.2.1")[1], 0)
            self.assertEqual(reserve_login("192.0.2.1")[1], 300)
        with patch("milenio_web.login_limit.time.time", return_value=1301):
            self.assertEqual(reserve_login("192.0.2.1")[1], 0)

    @override_settings(PASSWORD_HASHERS=["django.contrib.auth.hashers.MD5PasswordHasher"])
    def test_shift_logins_behind_one_address_only_count_failed_attempts(self):
        User.objects.create_superuser("turno", password="Prueba-de-turno-302")
        address = {"REMOTE_ADDR": "192.0.2.41"}
        good = {"username": "turno", "password": "Prueba-de-turno-302"}
        bad = {"username": "turno", "password": "ejemplo-no-valido"}
        with patch("milenio_web.login_limit.time.time", return_value=2000):
            for _ in range(12):
                self.assertEqual(self.client.post("/login/", good, **address).status_code, 302)
                self.client.logout()
            for _ in range(10):
                self.assertEqual(self.client.post("/login/", bad, **address).status_code, 200)
            self.assertEqual(self.client.post("/login/", good, **address).status_code, 429)
            self.assertEqual(self.client.post("/login/", good, REMOTE_ADDR="192.0.2.42").status_code, 302)
            self.client.logout()
        with patch("milenio_web.login_limit.time.time", return_value=2301):
            self.assertEqual(self.client.post("/login/", good, **address).status_code, 302)
