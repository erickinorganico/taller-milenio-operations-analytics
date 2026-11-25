"""Capture the current review branch using a disposable workshop and browser."""
import os
import runpy
import secrets
import subprocess
import sys
import tempfile
import time
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont
from playwright.sync_api import expect, sync_playwright

PIECE = Path(__file__).resolve().parent
ROOT = PIECE.parents[1]
ASSETS = PIECE / "hyperframes" / "assets"
CHROMIUM = os.environ.get("MILENIO_DEMO_CHROMIUM")
SMOKE = runpy.run_path(str(ROOT / "infra/nube/tests/fotos_navegador.py"))


def proof_image():
    image = Image.new("RGB", (800, 580), "#26333a")
    draw = ImageDraw.Draw(image)
    for radius in range(240, 110, -1):
        shade = 122 + radius % 49
        draw.ellipse((400-radius, 284-radius, 400+radius, 284+radius),
                     fill=(shade, shade + 6, shade + 9))
    draw.ellipse((286, 170, 514, 398), fill="#4c5559", outline="#aeb5b8", width=6)
    draw.rounded_rectangle((535, 197, 658, 381), 25, fill="#a93925", outline="#ee896e", width=5)
    draw.rounded_rectangle((32, 480, 308, 550), 12, fill="#12191c")
    try:
        font = ImageFont.truetype("arial.ttf", 22)
    except OSError:
        font = ImageFont.load_default(size=22)
    draw.text((52, 503), "MUESTRA FICTICIA · FRENO", fill="#ffffff", font=font)
    image.save(ASSETS / "muestra.jpg", quality=92)


def capture(browser, base, password):
    desk = SMOKE["session"](browser, base, "mesa", password, 1280)
    phone = SMOKE["session"](browser, base, "tecnico1", password, 390)
    desk.goto(base + "/orders/new/")
    search = desk.get_by_label("Buscar vehículo registrado")
    desk.locator("[data-vehicle-filter]").screenshot(path=ASSETS / "buscador-vacio.png")
    search.fill("MLN825")
    desk.locator("#id_vehicle").select_option("1")
    desk.locator("#id_complaint").fill("Revisar vibración al frenar")
    desk.locator("main .page-head").screenshot(path=ASSETS / "recepcion-titulo.png")
    desk.locator(".form-panel").screenshot(path=ASSETS / "recepcion-buscar.png")
    desk.get_by_role("button", name="Crear orden de trabajo").click()
    expect(desk.get_by_role("heading", name="Este vehículo ya tiene una orden abierta")).to_be_visible()
    desk.locator("[data-review-vehicle]").screenshot(path=ASSETS / "recepcion-folio.png")
    desk.get_by_role("link", name="Abrir WO-DEMO-042").click()
    desk.wait_for_url(base + "/orders/1/")
    desk.locator("[data-inspections]").screenshot(path=ASSETS / "recepcion-sin-foto.png")
    phone.goto(base + "/orders/?mine=1")
    phone.locator("main").screenshot(path=ASSETS / "celular-ordenes.png")
    phone.goto(base + "/orders/1/#inspection")
    phone.locator("#id_area").fill("Frenos delanteros")
    phone.locator("#id_result").select_option("watch")
    phone.locator("#id_notes").fill("Revisar vibración al frenar")
    phone.locator("[name=photo]").set_input_files({
        "name": "muestra.jpg", "mimeType": "image/jpeg",
        "buffer": (ASSETS / "muestra.jpg").read_bytes(),
    })
    expect(phone.locator("[data-preview]")).to_be_visible()
    phone.locator("[data-entry]").screenshot(path=ASSETS / "celular-foto.png")
    phone.route(base + "/orders/1/inspection/", lambda route: route.abort(), times=1)
    save = phone.get_by_role("button", name="Guardar inspección")
    save.click()
    expect(phone.locator("[data-upload-status]")).to_contain_text("Sin confirmación")
    phone.locator("[data-upload-status]").screenshot(path=ASSETS / "celular-reintento.png")
    save.click()
    expect(phone.locator("[data-upload-status]")).to_contain_text("WO-DEMO-042")
    expect(phone.locator("[data-inspections] img")).to_have_count(1)
    phone.locator("[data-inspections]").screenshot(path=ASSETS / "celular-guardado.png")
    desk.bring_to_front()
    desk.locator("[data-refresh]").click()
    expect(desk.locator("[data-inspections] img")).to_have_count(1)
    desk.locator("[data-inspections]").screenshot(path=ASSETS / "recepcion-foto.png")
    desk.goto(base + "/agents/")
    desk.locator("main .page-head").screenshot(path=ASSETS / "agentes.png")


def main():
    ASSETS.mkdir(parents=True, exist_ok=True)
    proof_image()
    fixture = SMOKE["HOST"].replace('number="QA-" + name', 'number="WO-DEMO-042" if name == "tecnico1" else "WO-DEMO-043"')
    fixture = fixture.replace('name="Prueba"', 'name="Lucía Demo"').replace(
        'make="Marca", model="Modelo", plate="QA"', 'make="Nissan", model="Versa", plate="MLN-825"')
    with tempfile.TemporaryDirectory(prefix="milenio-video-demo-") as directory:
        port = Path(directory) / "port"
        password = secrets.token_urlsafe(24)
        env = {**os.environ, "MILENIO_MODE": "test", "MILENIO_DATA_DIR": directory,
               "DJANGO_SETTINGS_MODULE": "milenio_web.settings", "MILENIO_ALLOWED_HOSTS": "127.0.0.1",
               "QA_SYNTHETIC_PASSWORD": password}
        host = subprocess.Popen([sys.executable, "-c", fixture, str(port)],
                                cwd=ROOT, env=env)
        try:
            end = time.monotonic() + 75
            while not port.exists():
                if host.poll() is not None or time.monotonic() > end:
                    raise RuntimeError("El taller de prueba no arrancó")
                time.sleep(0.1)
            with sync_playwright() as playback:
                browser = playback.chromium.launch(headless=True, executable_path=CHROMIUM)
                try:
                    capture(browser, f"http://127.0.0.1:{port.read_text()}", password)
                finally:
                    browser.close()
        finally:
            port.with_suffix(".stop").touch()
            try:
                host.wait(timeout=10)
            except subprocess.TimeoutExpired:
                host.terminate()
                host.wait(timeout=10)


if __name__ == "__main__":
    main()
