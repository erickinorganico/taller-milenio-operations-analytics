"""Isolated browser verification; synthetic database and temporary session only."""
import json
import os
from pathlib import Path
import secrets
import subprocess
import sys
import tempfile
import time
import urllib.request

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))


def main():
    with tempfile.TemporaryDirectory(prefix="milenio-commercial-ui-") as directory:
        os.environ.update(MILENIO_MODE="demo", MILENIO_DATA_DIR=str(Path(directory)/"demo"), DJANGO_SETTINGS_MODULE="milenio_web.settings")
        import django
        django.setup()
        from django.conf import settings
        from django.contrib.auth.models import User
        from django.core.management import call_command
        from django.db import connections
        from django.test import Client
        call_command("migrate", verbosity=0)
        actor=User.objects.create_superuser("qa-synthetic", password=secrets.token_urlsafe(32))
        call_command("seed_commercial_demo", verbosity=0)
        client=Client()
        client.force_login(actor)
        cookie=client.cookies[settings.SESSION_COOKIE_NAME].value
        output=ROOT/"private"/"commercial-qa"
        output.mkdir(parents=True, exist_ok=True)
        children=[]
        try:
            children.append(subprocess.Popen([sys.executable,"-m","waitress","--listen=127.0.0.1:18771","milenio_web.wsgi:application"], cwd=ROOT, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL))
            children.append(subprocess.Popen([sys.executable,"-m","http.server","18772","--bind","127.0.0.1","--directory",str(ROOT.parent/"milenio-sitio"/"dist")], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL))
            for _ in range(40):
                try:
                    with urllib.request.urlopen("http://127.0.0.1:18771/health/", timeout=1) as response:
                        if response.status==200: break
                except OSError: time.sleep(.2)
            else: raise RuntimeError("QA server did not start")
            result=subprocess.run(["node",str(ROOT/"scripts/check_commercial_browser.cjs")], input=json.dumps({"cookie":cookie,"cookie_name":settings.SESSION_COOKIE_NAME,"origin":"http://127.0.0.1:18771","site_origin":"http://127.0.0.1:18772","output":str(output)}), text=True, encoding="utf-8", capture_output=True, cwd=ROOT, timeout=90)
            print(result.stdout)
            if result.returncode: raise RuntimeError(result.stderr)
            (output/"result.json").write_text(result.stdout, encoding="utf-8")
        finally:
            for child in children:
                child.terminate()
                child.wait(timeout=10)
            connections.close_all()


if __name__=="__main__": main()
