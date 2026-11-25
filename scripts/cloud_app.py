"""Run the private socket backend or probe it from the same container."""
import argparse
from contextlib import closing
from http.client import HTTPConnection
import json
import os
from pathlib import Path
import socket
import sys

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))


class SocketProbe(HTTPConnection):
    def __init__(self, host, path):
        super().__init__(host, timeout=4)
        self.path = path

    def connect(self):
        self.sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        self.sock.settimeout(self.timeout)
        self.sock.connect(self.path)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=("serve", "healthcheck"))
    args = parser.parse_args()
    if os.environ.get("DJANGO_SETTINGS_MODULE") != "milenio_web.cloud_settings":
        parser.error("Se requiere DJANGO_SETTINGS_MODULE=milenio_web.cloud_settings.")
    if not sys.platform.startswith("linux") or not hasattr(socket, "AF_UNIX"):
        parser.error("El despliegue en la nube requiere Linux con sockets Unix.")
    path = Path(os.environ.get("MILENIO_CLOUD_SOCKET", "/run/milenio/web.sock"))
    if not path.is_absolute() or not path.parent.is_dir():
        parser.error("Monta el directorio privado del socket en una ruta absoluta.")
    if args.action == "healthcheck":
        with closing(SocketProbe(os.environ["MILENIO_CLOUD_HOST"], str(path))) as connection:
            connection.request("GET", "/health/", headers={"X-Forwarded-Proto": "https", "X-Forwarded-For": "127.0.0.1"})
            response = connection.getresponse()
            return int(response.status != 200 or json.loads(response.read(256)) != {"status": "ok"})
    from milenio_web.wsgi import application
    from django.conf import settings
    from django.core.management import call_command
    from scripts.run_web import WorkshopStatic
    from waitress import serve
    from workshop.management.commands.backup_workshop import instance_lock
    with instance_lock(settings.DATA_DIR):
        call_command("migrate", check_unapplied=True, interactive=False, verbosity=0)
        serve(WorkshopStatic(application), unix_socket=str(path), unix_socket_perms="660",
              trusted_proxy="localhost", trusted_proxy_count=1,
              trusted_proxy_headers="x-forwarded-proto x-forwarded-for",
              threads=4, connection_limit=64, channel_timeout=120,
              max_request_header_size=16384, max_request_body_size=12 * 1024 * 1024)
    return 0


if __name__ == "__main__":
    sys.exit(main())
