"""Start the local Milenio workshop through Waitress on loopback only."""
from __future__ import annotations

import argparse
import mimetypes
import os
import socket
import sys
import threading
import webbrowser
from pathlib import Path

from django.core.management.base import CommandError


ROOT = Path(__file__).resolve().parent.parent
PORTS = {"live": 8765, "demo": 8766}
STATIC_DIR = ROOT / "workshop" / "static" / "workshop"


class WorkshopStatic:
    """Serve only bundled workshop assets; evidence uploads stay behind Django."""

    def __init__(self, app):
        self.app = app

    def __call__(self, environ, start_response):
        path = environ.get("PATH_INFO", "")
        prefix = "/static/workshop/"
        if not path.startswith(prefix):
            return self.app(environ, start_response)
        relative = path[len(prefix):]
        if (not relative or "\\" in relative or ":" in relative
                or any(part in ("", ".", "..") or part.startswith(".") for part in relative.split("/"))):
            start_response("404 Not Found", [("Content-Type", "text/plain; charset=utf-8")])
            return [b"Not Found"]
        file = STATIC_DIR.joinpath(*relative.split("/"))
        if file.is_symlink() or not file.resolve().is_relative_to(STATIC_DIR.resolve()) or not file.is_file():
            start_response("404 Not Found", [("Content-Type", "text/plain; charset=utf-8")])
            return [b"Not Found"]
        content = file.read_bytes()
        mime = mimetypes.guess_type(file.name)[0] or "application/octet-stream"
        start_response("200 OK", [("Content-Type", mime), ("Content-Length", str(len(content))),
                                  ("X-Content-Type-Options", "nosniff"), ("Cache-Control", "private, max-age=300")])
        return [content]


def _available_port(port: int) -> None:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as probe:
        probe.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        try:
            probe.bind(("127.0.0.1", port))
        except OSError as exc:
            raise RuntimeError(f"El puerto local {port} ya está ocupado. Cierre el otro servidor; no se detuvo ningún proceso.") from exc


def _demo_empty() -> bool:
    from workshop.models import Customer, Part, WorkOrder
    return not (Customer.objects.exists() or Part.objects.exists() or WorkOrder.objects.exists())


def run(mode: str, *, no_browser=False) -> None:
    if mode not in PORTS:
        raise ValueError("mode must be live or demo")
    if sys.version_info < (3, 12):
        raise RuntimeError("Se requiere Python 3.12 o posterior")
    if Path(sys.prefix).resolve() != (ROOT / ".venv").resolve():
        raise RuntimeError("Use Setup-Web.ps1 y el Python de .venv para iniciar Milenio")
    configured_data = os.environ.get("MILENIO_DATA_DIR")
    if configured_data and Path(configured_data).name.casefold() != mode:
        raise RuntimeError("MILENIO_DATA_DIR debe terminar en /live o /demo según el modo; use carpetas separadas")
    if not configured_data:
        legacy = ROOT / "private" / "operational" / mode / "workshop.sqlite3"
        if os.name == "nt":
            local_root = Path(os.environ.get("LOCALAPPDATA") or Path.home() / "AppData" / "Local")
        else:
            local_root = Path(os.environ.get("XDG_DATA_HOME") or Path.home() / ".local" / "share")
        target = local_root / "Milenio" / "operational" / mode / "workshop.sqlite3"
        if legacy.is_file() and not target.is_file():
            raise RuntimeError(
                f"Hay una base anterior en {legacy}. No se trasladó ni borró. "
                "Use MILENIO_DATA_DIR para abrir esa instancia o haga respaldo y restauración "
                "explícitos antes de usar la nueva ubicación local."
            )
    os.environ["DJANGO_SETTINGS_MODULE"] = "milenio_web.settings"
    os.environ["MILENIO_MODE"] = mode
    sys.path.insert(0, str(ROOT))
    import django
    from django.conf import settings
    from django.core.management import call_command
    from waitress import create_server
    from workshop.management.commands.backup_workshop import instance_lock

    django.setup()
    if settings.MILENIO_MODE != mode:
        raise RuntimeError("La configuración activa no coincide con el modo solicitado")
    port = PORTS[mode]
    _available_port(port)
    with instance_lock(settings.DATA_DIR):
        call_command("check", verbosity=0)
        call_command("migrate", interactive=False, verbosity=0)
        if mode == "demo" and _demo_empty():
            call_command("seed_workshop", demo=True)
        from milenio_web.wsgi import application
        server = create_server(WorkshopStatic(application), host="127.0.0.1", port=port, threads=4)
        url = f"http://127.0.0.1:{port}/"
        print(f"Milenio {mode}: {url}", flush=True)
        print(f"Datos: {settings.DATA_DIR}", flush=True)
        print("Presione Ctrl+C para detener el servidor sin borrar datos.", flush=True)
        if not no_browser:
            opener = threading.Timer(0.5, webbrowser.open, args=(url,))
            opener.daemon = True
            opener.start()
        try:
            server.run()
        except KeyboardInterrupt:
            print("Servidor detenido. Los datos permanecen guardados.", flush=True)
        finally:
            server.close()


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--mode", choices=tuple(PORTS), default="live")
    parser.add_argument("--no-browser", action="store_true", help="No abrir el navegador (CI o servicio supervisado)")
    args = parser.parse_args(argv)
    try:
        run(args.mode, no_browser=args.no_browser)
    except (RuntimeError, ValueError, CommandError, OSError) as exc:
        print(f"No se pudo iniciar Milenio: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
