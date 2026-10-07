"""Bounded public-website research. No platform scraping, logins, or LLM calls."""
from __future__ import annotations
import argparse
import hashlib
import http.client
import ipaddress
import json
import os
from pathlib import Path
import socket
import ssl
import time
from datetime import datetime, timezone
from html.parser import HTMLParser
from urllib.parse import urljoin, urlsplit, urlunsplit
from urllib.robotparser import RobotFileParser

AGENT = "MilenioResearch/1.0"
BLOCKED = ("google.com", "google.com.mx", "maps.app.goo.gl", "goo.gl", "facebook.com", "fb.com", "instagram.com", "linkedin.com", "youtube.com", "tiktok.com", "x.com", "twitter.com")
MAX_BYTES = 1_000_000


def normalize(url):
    p = urlsplit(url)
    if p.scheme not in {"http", "https"} or not p.hostname or p.username or p.password or p.port not in {None, 80, 443}:
        raise ValueError("Solo HTTP(S), sin credenciales y con puertos web estándar.")
    host = p.hostname.lower().rstrip(".")
    if any(host == x or host.endswith("."+x) for x in BLOCKED):
        raise ValueError("Plataforma excluida: usa investigación manual o asistida.")
    if p.query: raise ValueError("La investigación inicial usa páginas sin parámetros de consulta.")
    return urlunsplit((p.scheme, host + (":"+str(p.port) if p.port else ""), p.path or "/", "", ""))


def host_key(url):
    return urlsplit(url).hostname.removeprefix("www.")


def public_addresses(host, port):
    addresses = sorted({row[4][0] for row in socket.getaddrinfo(host, port, type=socket.SOCK_STREAM)})
    if not addresses or any(not ipaddress.ip_address(ip).is_global for ip in addresses):
        raise ValueError("Dirección local, privada o reservada: descarga bloqueada.")
    return addresses


def fetch(url, allowed_host, *, redirects=0, permission=None):
    url = normalize(url)
    if host_key(url) != allowed_host: raise ValueError("La descarga saldría del dominio autorizado.")
    if permission and not permission(url): raise ValueError("robots.txt no permite la página o su redirección.")
    p = urlsplit(url)
    port = p.port or (443 if p.scheme == "https" else 80)
    ip = public_addresses(p.hostname, port)[0]
    connection = http.client.HTTPSConnection(p.hostname, port=port, timeout=12, context=ssl.create_default_context()) if p.scheme == "https" else http.client.HTTPConnection(p.hostname, port=port, timeout=12)
    # Pin the validated IP; HTTPS still verifies the original hostname and uses SNI.
    connection._create_connection = lambda address, timeout=12, source_address=None: socket.create_connection((ip, port), timeout=timeout, source_address=source_address)
    try:
        connection.request("GET", p.path or "/", headers={"User-Agent": AGENT, "Accept": "text/html,text/plain", "Accept-Encoding": "identity"})
        response = connection.getresponse()
        if response.status in {301, 302, 303, 307, 308}:
            target = response.getheader("Location")
            if redirects >= 3 or not target: raise ValueError("Demasiadas redirecciones o destino ausente.")
            return fetch(urljoin(url, target), allowed_host, redirects=redirects+1, permission=permission)
        content_type = response.getheader("Content-Type", "")
        if response.status not in {200, 404}: raise ValueError(f"HTTP {response.status}; no se reintenta ni se elude el bloqueo.")
        if response.status == 200 and not any(t in content_type.lower() for t in ("text/html", "text/plain", "application/xhtml")):
            raise ValueError("Respuesta no textual.")
        if response.getheader("Content-Encoding", "identity") not in {"identity", ""}: raise ValueError("Codificación comprimida no admitida en esta primera versión.")
        body = response.read(MAX_BYTES+1)
        if len(body) > MAX_BYTES: raise ValueError("Página demasiado grande: máximo 1 MB.")
        return response.status, body.decode("utf-8", errors="replace"), url
    finally:
        connection.close()


class Links(HTMLParser):
    def __init__(self):
        super().__init__()
        self.links = []

    def handle_starttag(self, tag, attrs):
        if tag == "a":
            href = dict(attrs).get("href", "")
            if any(word in href.lower() for word in ("contact", "nosotros", "about", "servic", "empresa")):
                self.links.append(href)


def investigate(url, *, cache_dir, refresh=False, delay=2):
    from trafilatura import extract
    url = normalize(url)
    host = host_key(url)
    cache_dir = Path(cache_dir)
    cache_dir.mkdir(parents=True, exist_ok=True)
    cache_path = cache_dir / (hashlib.sha256(url.encode()).hexdigest()+".json")
    if cache_path.exists() and not refresh:
        cached = json.loads(cache_path.read_text(encoding="utf-8"))
        captured = datetime.fromisoformat(cached["created_at"])
        if (datetime.now(timezone.utc)-captured).total_seconds() < 86400:
            return {**cached, "cache_hit": True}
    report = {"schema": "milenio-research-v1", "engine": "trafilatura-local", "created_at": datetime.now(timezone.utc).isoformat(), "origin": url, "cache_hit": False, "pages": [], "notes": ["Texto no revisado. No confirma combustible, intención de compra ni entregabilidad de contactos."]}
    robots_url = urljoin(url, "/robots.txt")
    status, robots_text, _ = fetch(robots_url, host)
    robots = RobotFileParser()
    robots.set_url(robots_url)
    robots.parse(robots_text.splitlines() if status == 200 else [])
    delay = max(delay, robots.crawl_delay(AGENT) or 0)
    if delay > 30: raise ValueError("El sitio requiere una pausa mayor; investigar manualmente.")
    queue, seen = [url], set()
    while queue and len(report["pages"]) < 4:
        target = queue.pop(0)
        if target in seen: continue
        seen.add(target)
        page = {"url": target, "captured_at": datetime.now(timezone.utc).isoformat()}
        try:
            if not robots.can_fetch(AGENT, target): raise ValueError("robots.txt no permite esta página.")
            time.sleep(delay)
            status, body, final_url = fetch(target, host, permission=lambda destination: robots.can_fetch(AGENT, destination))
            if status != 200: raise ValueError(f"HTTP {status}")
            if any(marker in body.lower() for marker in ("cf-chl-", "g-recaptcha", "verify you are human")):
                raise ValueError("Protección de acceso detectada; investigación manual.")
            text = extract(body, include_comments=False, include_tables=False, favor_precision=True, url=final_url) or ""
            if not text.strip(): raise ValueError("Sin texto extraíble; revisar manualmente.")
            page.update(url=final_url, status="ok", text=text[:16000], content_sha256=hashlib.sha256(body.encode()).hexdigest())
            parser = Links()
            parser.feed(body)
            for href in parser.links:
                try:
                    candidate = normalize(urljoin(final_url, href))
                    if host_key(candidate) == host and candidate not in seen and candidate not in queue:
                        queue.append(candidate)
                except ValueError:
                    continue
            queue = queue[:12]
        except (ValueError, OSError, http.client.HTTPException) as exc:
            page.update(status="failed", error=str(exc)[:300])
        report["pages"].append(page)
    report["successful_pages"] = sum(p["status"] == "ok" for p in report["pages"])
    temporary = cache_path.with_suffix(".tmp")
    temporary.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    temporary.replace(cache_path)
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("url")
    parser.add_argument("--fetch", action="store_true", help="Ejecutar descarga. Sin este argumento solo muestra el plan.")
    parser.add_argument("--refresh", action="store_true")
    default = Path(os.environ.get("LOCALAPPDATA", str(Path.home()))) / "Milenio" / "research"
    parser.add_argument("--output", type=Path, default=default / "last-report.json")
    parser.add_argument("--cache-dir", type=Path, default=default / "cache")
    args = parser.parse_args()
    try:
        url = normalize(args.url)
        if not args.fetch:
            print(json.dumps({"url": url, "max_pages": 4, "platform_scraping": False, "paid_calls": False, "run": "Agregar --fetch para descargar"}, ensure_ascii=False))
            return 0
        report = investigate(url, cache_dir=args.cache_dir, refresh=args.refresh)
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
        print(json.dumps({"report": str(args.output.resolve()), "pages": len(report["pages"]), "successful_pages": report["successful_pages"], "cache_hit": report["cache_hit"]}))
        return 0 if report["successful_pages"] else 2
    except (ValueError, OSError, http.client.HTTPException) as exc:
        print(json.dumps({"status": "failed", "error": str(exc)}, ensure_ascii=False))
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
