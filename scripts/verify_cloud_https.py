"""Exercise the cloud stack over real TLS using disposable containers and synthetic data."""
import argparse
import base64
import hashlib
import http.client
import json
import os
import re
import secrets
import socket
import ssl
import subprocess
import tempfile
from http.cookies import SimpleCookie
from pathlib import Path
from urllib.parse import parse_qs, urlencode, urlsplit


ROOT = Path(__file__).resolve().parents[1]
DEPLOY = ROOT / "infra" / "nube"
HOST = "taller.example.test"
PNG = base64.b64decode("iVBORw0KGgoAAAANSUhEUgAAAAgAAAAICAIAAABLbSncAAAAE0lEQVR4nGNkaGDACpiwCw9WCQBqCACQJ5at+QAAAABJRU5ErkJggg==")


class Session:
    def __init__(self, port, ca, agent):
        self.port = port
        self.ctx = ssl.create_default_context(cadata=ca)
        self.agent = agent
        self.cookies = {}

    def request(self, path, fields=None, photo=False):
        # Send the real Host/SNI while physically connecting only to a random loopback port.
        conn = http.client.HTTPSConnection(HOST, timeout=12, context=self.ctx)
        raw = socket.create_connection(("127.0.0.1", self.port), timeout=12)
        conn.sock = self.ctx.wrap_socket(raw, server_hostname=HOST)
        headers = {"Host": HOST, "User-Agent": self.agent,
                   "Cookie": "; ".join(f"{k}={v}" for k, v in self.cookies.items())}
        payload = None
        if fields is not None:
            headers["Origin"] = f"https://{HOST}"
            if photo:
                boundary = "milenio-" + secrets.token_hex(12)
                chunks = [f'--{boundary}\r\nContent-Disposition: form-data; name="{k}"\r\n\r\n{v}\r\n'.encode() for k, v in fields.items()]
                chunks.extend([f'--{boundary}\r\nContent-Disposition: form-data; name="photo"; filename="prueba.png"\r\nContent-Type: image/png\r\n\r\n'.encode(), PNG, f"\r\n--{boundary}--\r\n".encode()])
                headers["Content-Type"] = f"multipart/form-data; boundary={boundary}"
                payload = b"".join(chunks)
            else:
                payload = urlencode(fields).encode()
                headers["Content-Type"] = "application/x-www-form-urlencoded"
        try:
            conn.request("GET" if fields is None else "POST", path, payload, headers)
            res = conn.getresponse()
            for name, value in res.getheaders():
                if name.lower() == "set-cookie":
                    for cookie in SimpleCookie(value).values():
                        if cookie["max-age"] == "0":
                            self.cookies.pop(cookie.key, None)
                            continue
                        assert cookie["secure"], f"cookie without Secure: {cookie.key}"
                        self.cookies[cookie.key] = cookie.value
            return res.status, res.getheader("Location", ""), res.read()
        finally:
            conn.close()

    def form(self, path, *, target=None, photo=False, **fields):
        status, _, page = self.request(path)
        assert status == 200, (path, status)
        for name in ("csrfmiddlewaretoken", "reception_token"):
            match = re.search(rb'name="' + name.encode() + rb'"[^>]+value="([^"]+)"', page)
            if match:
                fields[name] = match.group(1).decode()
        assert "csrfmiddlewaretoken" in fields, path
        status, location, _ = self.request(target or path, fields, photo)
        assert status in (302, 303), (target or path, status)
        return location


def exercise(port, cert, password, restart):
    mobile = Session(port, cert, "Milenio-QA/Mobile")
    desk = Session(port, cert, "Milenio-QA/Desktop")
    anonymous = Session(port, cert, "Milenio-QA/Guest")
    assert anonymous.request("/setup/")[0] == 404
    assert anonymous.request("/health/")[0] == 404
    assert anonymous.request("/orders/")[1].startswith("/login/")
    for session, name in ((mobile, "prueba-recepcion"), (desk, "prueba-gerencia")):
        session.form("/login/", username=name, password=password)
    vehicle_path = mobile.form("/records/customers/new/?flow=reception", name="Prueba nube", kind="individual")
    customer = parse_qs(urlsplit(vehicle_path).query)["customer"][0]
    intake = mobile.form(vehicle_path, customer=customer, plate="QA2026", make="Marca QA", model="Modelo QA")
    vehicle = parse_qs(urlsplit(intake).query)["vehicle"][0]
    order = mobile.form(intake, vehicle=vehicle, complaint="Recepción de prueba nube")
    assert re.fullmatch(r"/orders/\d+/", order), order
    status, _, page = mobile.request(order)
    assert status == 200
    folio = re.search(rb"WO-\d{8}-[A-Z0-9]+", page).group()
    version = re.search(rb'name="version"[^>]+value="(\d+)"', page).group(1).decode()
    mobile.form(order, target=order+"transition/", status="inspection", version=version)
    mobile.form(order, target=order+"inspection/", photo=True, area="Frente", result="okay", notes="Prueba local")
    status, _, page = desk.request(order)
    assert status == 200 and folio in page
    photo_url = re.search(rb"/inspection/\d+/photo/", page).group().decode()
    assert anonymous.request(photo_url)[1].startswith("/login/")
    status, _, original = desk.request(photo_url)
    assert status == 200 and original.startswith(b"\x89PNG")
    restart()
    assert folio in desk.request(order)[2]
    assert hashlib.sha256(desk.request(photo_url)[2]).digest() == hashlib.sha256(original).digest()
    return {"tls_verified": True, "public_setup_closed": True, "private_photo": True,
            "separate_mobile_desktop_sessions": True, "order_and_photo_after_restart": True}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--receipt", type=Path)
    args = parser.parse_args()
    prefix = "nubeqa" + secrets.token_hex(6)
    env = dict(os.environ, MILENIO_CLOUD_HOST=HOST, MILENIO_BUILD_REVISION=prefix)
    def run(command, **kwargs):
        return subprocess.run(command, cwd=ROOT, env=env, check=True, **kwargs)
    endpoint = env.get("DOCKER_HOST") or run(["docker", "context", "inspect", "--format", "{{.Endpoints.docker.Host}}"], capture_output=True, text=True).stdout.strip()
    if not endpoint.startswith(("npipe://", "unix://")):
        raise SystemExit("This check requires a local Docker engine.")
    with tempfile.TemporaryDirectory(prefix="milenio-https-") as temp:
        folder = Path(temp)
        proxy = folder / "Caddyfile"
        proxy.write_text((DEPLOY / "Caddyfile").read_text(encoding="utf-8").replace("{\n", "{\n\tlocal_certs\n", 1), encoding="utf-8")
        mounts = {"data":"/var/lib/milenio", "socket":"/run/milenio", "certs":"/data", "config":"/config"}
        volumes = {service: {"volumes": [name + ":" + mounts[name] for name in names]} for service, names in
                   {"app": ["data","socket"], "analytics": ["data"], "capture": ["data"], "caddy": ["socket","certs","config"]}.items()}
        volumes["caddy"]["volumes"][0] += ":ro"
        volumes["caddy"]["volumes"].append({"type":"bind","source":proxy.as_posix(),"target":"/etc/caddy/Caddyfile","read_only":True})
        # Compose merges production mount definitions by container target. Replace all published ports.
        override = folder / "test.yml"
        override.write_text("volumes: " + json.dumps({n:{} for n in mounts}) + "\nservices:\n" +
                            "".join(f"  {svc}:\n    volumes: {json.dumps(conf['volumes'])}\n" +
                                    ('    ports: !override ["127.0.0.1::443"]\n' if svc == "caddy" else "")
                                    for svc, conf in volumes.items()), encoding="utf-8")
        base = ["docker","compose","--project-name",prefix,"-f",str(DEPLOY/"compose.yaml"),"-f",str(override)]
        def compose(*parts, **kwargs):
            return run([*base,*parts], **kwargs)
        result = None
        try:
            cfg = json.loads(compose("config","--format","json", capture_output=True,text=True).stdout)
            for service in cfg["services"].values():
                for volume in service["volumes"]:
                    if volume["type"] == "bind":
                        assert Path(volume["source"]).resolve() == proxy.resolve()
            compose("build","app")
            compose("create","app","caddy")
            init = ["docker","run","--rm","--network","none","--user","0:0","--entrypoint","sh"]
            for name, target in mounts.items():
                init += ["-v", f"{prefix}_{name}:{target}"]
            run([*init, cfg["services"]["caddy"]["image"], "-ec",
                 "chown 10001:10001 /var/lib/milenio /run/milenio; chmod 700 /var/lib/milenio; chmod 770 /run/milenio; chown 10002:10001 /data /config"])
            compose("run","--rm","--no-deps","-T","app","python","manage.py","migrate","--noinput",stdout=subprocess.DEVNULL)
            password = secrets.token_urlsafe(36)
            seed = ("from django.contrib.auth.models import User, Group\n" +
                    "Group.objects.get_or_create(name='advisor')\n" +
                    f"User.objects.create_superuser('prueba-gerencia',password={password!r})\n" +
                    f"u=User.objects.create_user('prueba-recepcion',password={password!r})\n" +
                    "u.groups.add(Group.objects.get(name='advisor'))\n")
            compose("run","--rm","--no-deps","-T","app","python","manage.py","shell", input=seed,text=True,stdout=subprocess.DEVNULL)
            compose("up","-d","--wait","--wait-timeout","120")
            port = int(compose("port","caddy","443",capture_output=True,text=True).stdout.rsplit(":",1)[1])
            cert = compose("exec","-T","caddy","cat","/data/caddy/pki/authorities/local/root.crt",capture_output=True,text=True).stdout
            def restart():
                compose("restart","app","analytics","capture",stdout=subprocess.DEVNULL)
                compose("up","-d","--wait","--wait-timeout","120",stdout=subprocess.DEVNULL)
            result = exercise(port, cert, password, restart)
        finally:
            compose("down","--volumes","--remove-orphans")
            # Only this randomly tagged synthetic app image can be removed here.
            subprocess.run(["docker","image","rm",f"milenio-taller:{prefix}"],cwd=ROOT,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
        output = json.dumps({"status":"pass","scope":"isolated Docker; Caddy local CA; synthetic users, order and photo",**result},indent=2)
        print(output)
        if args.receipt:
            args.receipt.write_text(output+"\n",encoding="utf-8")


if __name__ == "__main__":
    main()
