"""Run a disposable mobile/desktop inspection test with Playwright Chromium."""
import argparse
from concurrent.futures import ThreadPoolExecutor
from io import BytesIO
import json
import os
from pathlib import Path
import secrets
import subprocess
import sys
import tempfile
import time
from urllib.parse import urlencode, urlsplit
from urllib.request import Request, urlopen
from uuid import uuid4

from PIL import Image
from playwright.sync_api import expect, sync_playwright


ROOT = Path(__file__).resolve().parents[3]
HOST = """
import os, pathlib, sys, threading, time
import django
django.setup()
from django.core.management import call_command
from django.contrib.auth.models import Group, User
from workshop.models import Customer, Vehicle, WorkOrder
from waitress import create_server
from milenio_web.wsgi import application
call_command("migrate", interactive=False, verbosity=0)
pw = os.environ["QA_SYNTHETIC_PASSWORD"]
User.objects.create_superuser("mesa", password=pw)
car = Vehicle.objects.create(customer=Customer.objects.create(name="Prueba"),
                             make="Marca", model="Modelo", plate="QA")
Vehicle.objects.create(customer=Customer.objects.create(name="María de prueba"),
                       make="Otra", model="Unidad", plate="QA-2026")
role = Group.objects.create(name="technician")
for name in ["tecnico1","tecnico2"]:
    user = User.objects.create_user(name,password=pw)
    user.groups.add(role)
    WorkOrder.objects.create(vehicle=car, number="QA-" + name, assigned_to=user,
                             status="inspection", complaint="Caso sintetico")
server = create_server(application, host="127.0.0.1", port=0, threads=4)
port = pathlib.Path(sys.argv[1])
port.write_text(str(server.effective_port))
def stop_on_request():
    deadline = time.monotonic() + 300
    while not port.with_suffix(".stop").exists() and time.monotonic() < deadline:
        time.sleep(0.1)
    server.close()
    os._exit(0)
threading.Thread(target=stop_on_request, daemon=True).start()
server.run()
"""


def session(browser, base, name, password, width):
    ctx = browser.new_context(viewport={"width": width, "height": 844},
                              is_mobile=width < 600, has_touch=width < 600)
    ctx.route("**/*", lambda route: route.continue_() if urlsplit(route.request.url).hostname == "127.0.0.1" else route.abort())
    page = ctx.new_page()
    page.goto(base + "/login/")
    page.locator("[name=username]").fill(name)
    page.locator("[name=password]").fill(password)
    page.get_by_role("button", name="Entrar al taller").click()
    page.wait_for_url(base + "/")
    return page


def direct_upload(target):
    # Reproduce native multipart uploads from two techs without JS resizing.
    url, cookies, csrf, file, key = target
    boundary = "qa-" + uuid4().hex
    fields = {"csrfmiddlewaretoken": csrf, "area": "Cofre", "result": "okay", "submission_key": key}
    body = [f'--{boundary}\r\nContent-Disposition: form-data; name="{key}"\r\n\r\n{value}\r\n'.encode()
            for key, value in fields.items()]
    body.extend([f'--{boundary}\r\nContent-Disposition: form-data; name="photo"; filename="grande.jpg"\r\nContent-Type: image/jpeg\r\n\r\n'.encode(),
                 file, f"\r\n--{boundary}--\r\n".encode()])
    request = Request(url, data=b"".join(body), headers={"Content-Type": f"multipart/form-data; boundary={boundary}",
                      "Accept": "application/json", "Cookie": cookies})
    with urlopen(request, timeout=60) as response:
        return json.load(response)["id"]


def exercise(browser, base, password):
    phone = session(browser, base, "tecnico1", password, 390)
    second = session(browser, base, "tecnico2", password, 390)
    desk = session(browser, base, "mesa", password, 1280)
    reception = session(browser, base, "mesa", password, 390)
    reception.goto(f"{base}/orders/new/")
    vehicle = reception.locator("#id_vehicle")
    lookup = reception.get_by_label("Buscar vehículo registrado")
    lookup.fill("maria")
    expect(vehicle.locator("option")).to_have_count(2)
    vehicle.select_option(index=1)
    lookup.fill("no existe")
    expect(vehicle).to_have_value("")
    expect(reception.locator("[data-vehicle-count]")).to_contain_text("Sin coincidencias")
    lookup.fill("qa2026")
    lookup.press("Enter")
    expect(vehicle).to_be_focused()
    expect(vehicle).to_have_value("")
    lookup.fill("")
    vehicle.select_option("1")
    reception.locator("#id_complaint").fill("Visita separada de prueba")
    reception.get_by_role("button", name="Crear orden de trabajo").click()
    expect(reception.get_by_role("link", name="Abrir QA-tecnico1")).to_be_visible()
    reception.get_by_role("button", name="Crear otra orden").click()
    expect(reception.locator("[name=confirm_open_orders]")).to_be_focused()
    reception.get_by_label("Es un trabajo distinto").check()
    reception.get_by_role("button", name="Crear otra orden").click()
    reception.wait_for_url(f"{base}/orders/3/")
    # Two desks receive the same second vehicle with independently issued forms.
    url = f"{base}/orders/new/"
    visits = []
    for _ in range(2):
        reception.goto(url)
        visits.append(urlencode({
            "vehicle": 2, "complaint": "Revisión simultánea",
            "reception_token": reception.locator("[name=reception_token]").input_value(),
            "csrfmiddlewaretoken": reception.locator(".form-panel [name=csrfmiddlewaretoken]").input_value(),
        }).encode())
    cookies = "; ".join(f'{c["name"]}={c["value"]}' for c in reception.context.cookies())

    def receive(data):
        with urlopen(Request(url, data=data, headers={"Cookie": cookies}), timeout=30) as response:
            return urlsplit(response.url).path, "confirm_open_orders" in response.read().decode()

    with ThreadPoolExecutor(max_workers=2) as pool:
        outcomes = list(pool.map(receive, visits))
    assert sorted(outcomes) == [("/orders/4/", False), ("/orders/new/", True)], outcomes
    reception.context.close()
    pages = [phone, second, desk]
    errors = []
    for page, order_id in zip(pages, [1, 2, 1]):
        page.on("pageerror", lambda exc: errors.append(str(exc)))
        page.goto(f"{base}/orders/{order_id}/")
    assert phone.evaluate("document.documentElement.scrollWidth <= innerWidth")
    desk.locator("#id_area").fill("Borrador en recepción")
    assert desk.locator("[data-inspections] img").count() == 0
    raw = BytesIO()
    Image.new("RGB", (4032, 3024), "#3568b2").save(raw, format="JPEG")
    phone.locator("#id_area").fill("Frenos")
    phone.locator("#id_result").select_option("watch")
    phone.locator("#id_notes").fill("Hallazgo sintético")
    phone.locator('[name=photo]').set_input_files({"name":"imagen.jpg", "mimeType":"image/jpeg", "buffer":raw.getvalue()})
    preview = phone.locator("[data-preview]")
    expect(preview).to_be_visible()
    assert preview.evaluate("img => img.naturalWidth") == 2400
    phone.get_by_role("button", name="Quitar foto").click()
    expect(phone.locator("[data-remove-photo]")).to_be_hidden()
    expect(preview).to_be_hidden()
    expect(phone.locator("[name=photo]")).to_have_value("")
    expect(phone.locator("#id_notes")).to_have_value("Hallazgo sintético")
    assert phone.evaluate("!window.dispatchEvent(new Event('beforeunload', {cancelable:true}))")
    phone.locator("[data-gallery] summary").click()
    phone.locator('[name=gallery_photo]').set_input_files({"name":"otra.jpg", "mimeType":"image/jpeg", "buffer":raw.getvalue()})
    expect(preview).to_be_visible()
    target = base + "/orders/1/inspection/"
    receipts = []

    def lose_confirmation(route):
        response = route.fetch()
        assert response.ok, response.status
        receipts.append(response.json()["id"])
        route.abort()

    phone.route(target, lose_confirmation, times=1)
    button = phone.get_by_role("button", name="Guardar inspección")
    button.click()
    expect(phone.locator("[data-upload-status]")).to_contain_text("Sin confirmación")
    expect(phone.locator("#id_area")).to_have_value("Frenos")
    expect(preview).to_be_visible()
    # A login change in another tab must keep the original draft on this phone.
    login_tab = phone.context.new_page()
    for account in ("mesa", "tecnico1"):
        login_tab.goto(base + "/orders/1/")
        with login_tab.expect_navigation(wait_until="domcontentloaded"):
            login_tab.locator("form[action='/logout/']").evaluate("form => form.requestSubmit()")
        login_tab.wait_for_url(base + "/login/")
        login_tab.locator("[name=username]").fill(account)
        login_tab.locator("[name=password]").fill(password)
        login_tab.get_by_role("button", name="Entrar al taller").click()
        login_tab.wait_for_url(base + "/")
        phone.bring_to_front()
        button.click()
        if account == "mesa":
            expect(phone.locator("[data-upload-status]")).to_contain_text("Cambió la cuenta")
            expect(preview).to_be_visible()
    expect(phone.locator("[data-upload-status]")).to_contain_text("Inspección guardada en la orden QA-tecnico1")
    assert phone.evaluate("window.dispatchEvent(new Event('beforeunload', {cancelable:true}))")
    # Wait for the second session's unattended poll; it must preserve the desk draft.
    expect(desk.locator("[data-inspections] img")).to_have_count(1, timeout=35000)
    expect(desk.locator("#id_area")).to_have_value("Borrador en recepción")
    assert len(receipts) == 1
    assert desk.locator("[data-inspections] img").get_attribute("src") == f"/inspection/{receipts[0]}/photo/"
    assert not errors, errors
    jobs = []
    for i, page in enumerate([phone, second], start=1):
        cookies = "; ".join(f'{c["name"]}={c["value"]}' for c in page.context.cookies())
        token = page.request.get(f"{base}/orders/{i}/inspection-feed/?session=1").json()["csrf"]
        jobs.append((f"{base}/orders/{i}/inspection/", cookies, token, raw.getvalue(), str(uuid4())))
    with ThreadPoolExecutor(max_workers=2) as pool:
        ids = list(pool.map(direct_upload, jobs))
        retry_ids = list(pool.map(direct_upload, [jobs[0], jobs[0]]))
    assert retry_ids == [ids[0], ids[0]]
    assert len(set(ids + receipts)) == 3
    return {"viewport": 390, "desk": 1280, "camera_input": True, "local_preview_width": 2400,
            "vehicle_filter": True, "separate_visit_acknowledged": True,
            "simultaneous_reception": "one folio and one review", "photo_replaced": True,
            "retry_after_lost_confirmation": "one inspection", "automatic_desk_refresh": True,
            "desk_draft_preserved": True, "reauth_same_person": True, "account_switch_blocked": True, "concurrent_native_12MP_uploads": len(ids), "concurrent_retries_reused_id": True}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--app-python", required=True, help="Interpreter with requirements-web installed")
    parser.add_argument("--chromium", help="Optional path to a Playwright-compatible Chromium")
    args = parser.parse_args()
    with tempfile.TemporaryDirectory(prefix="milenio-fotos-e2e-") as temp:
        port = Path(temp) / "port"
        password = secrets.token_urlsafe(24)
        env = {**os.environ, "MILENIO_MODE":"test", "MILENIO_DATA_DIR":temp,
               "DJANGO_SETTINGS_MODULE":"milenio_web.settings", "MILENIO_ALLOWED_HOSTS":"127.0.0.1",
               "QA_SYNTHETIC_PASSWORD": password}
        host = subprocess.Popen([args.app_python, "-c", HOST, str(port)], cwd=ROOT, env=env)
        try:
            deadline = time.monotonic() + 90
            while not port.exists():
                if time.monotonic() > deadline or host.poll() is not None:
                    raise RuntimeError("No arrancó el taller de prueba.")
                time.sleep(0.1)
            with sync_playwright() as runner:
                browser = runner.chromium.launch(headless=True, executable_path=args.chromium)
                try:
                    print(json.dumps(exercise(browser, f"http://127.0.0.1:{port.read_text()}", password)))
                finally:
                    browser.close()
        finally:
            port.with_suffix(".stop").touch()
            try:
                host.wait(timeout=15)
            except subprocess.TimeoutExpired:
                host.terminate()
                host.wait(timeout=10)


if __name__ == "__main__":
    main()
