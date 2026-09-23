"""Exercise V5-to-V6 migration and backup/restore on disposable local data.

This script never points at a configured live or demo instance. Child processes
receive an explicit MILENIO_MODE=test and a fresh temporary data directory.
"""
from __future__ import annotations

import argparse
import hashlib
from http.cookiejar import CookieJar
import json
import os
import queue
import re
import secrets
import sqlite3
import subprocess
import sys
import tempfile
import threading
import time
from urllib.parse import urlencode
from urllib.request import HTTPCookieProcessor, Request, build_opener
import venv
import zipfile
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
MARKER = "V6-VERIFY-JSON:"

SEED_V5 = r'''
import django, json
django.setup()
from datetime import timedelta
from decimal import Decimal
from django.contrib.auth import get_user_model
from django.utils import timezone
from workshop.models import AuditEvent, Customer, Invoice, Part, Payment, Quote, QuoteLine, StockMovement, Vehicle, WorkOrder
actor = get_user_model()(username='v6-disposable-fixture', is_active=True, is_superuser=True)
actor.set_unusable_password()
actor.save()
now = timezone.now()
person = Customer.objects.create(name='Fictitious migration fixture', kind='individual')
fleet = Customer.objects.create(name='Fictitious fleet fixture', kind='fleet')
car = Vehicle.objects.create(customer=person, make='Fixture', model='A')
van = Vehicle.objects.create(customer=fleet, make='Fixture', model='B')
delivered = WorkOrder.objects.create(vehicle=car, number='V5-MIGRATION-1', status='delivered',
    complaint='Synthetic service', created_at=now-timedelta(days=10), promised_at=now-timedelta(days=6))
WorkOrder.objects.create(vehicle=van, number='V5-MIGRATION-2', status='in_progress',
    complaint='Synthetic open service', created_at=now-timedelta(days=3), promised_at=now-timedelta(days=1))
part = Part.objects.create(sku='V5-MIGRATION-PART', name='Fixture filter', stock=Decimal('5.000'),
    cost=Decimal('8.00'), sale_price=Decimal('15.00'))
StockMovement.objects.create(part=part, kind='consume', quantity=Decimal('-1.000'),
    unit_cost=part.cost, work_order=delivered, created_by=actor, created_at=now-timedelta(days=9))
quote = Quote.objects.create(work_order=delivered, version=1, status='approved',
    authorized_at=now-timedelta(days=9))
QuoteLine.objects.create(quote=quote, kind='service', description='Fixture service',
    quantity=Decimal('1.000'), unit_price=Decimal('120.00'), unit_cost=Decimal('60.00'))
invoice = Invoice.objects.create(work_order=delivered, number='V5-MIGRATION-INVOICE',
    subtotal=Decimal('120.00'), tax=Decimal('0.00'), total=Decimal('120.00'),
    issued_at=now-timedelta(days=8), due_at=now+timedelta(days=5))
Payment.objects.create(invoice=invoice, amount=Decimal('20.00'), method='fixture', reference='synthetic',
    idempotency_key='v6-migration-payment', received_at=now-timedelta(days=7), created_by=actor)
AuditEvent.objects.create(actor=actor, entity_type='WorkOrder', entity_id=str(delivered.pk),
    action='status_changed', before={'status':'ready'}, after={'status':'delivered'},
    created_at=now-timedelta(days=9))
print('V6-VERIFY-JSON:'+json.dumps({'orders':WorkOrder.objects.count(), 'invoice_total':'120.00',
    'balance':'100.00', 'customers':Customer.objects.count()}))
'''

MATERIALIZE = r'''
import django, json
django.setup()
from datetime import timedelta
from django.contrib.auth import get_user_model
from django.contrib.sessions.backends.db import SessionStore
from django.utils import timezone
from workshop import analytics, automation
from workshop.models import AnalyticsRow, AnalyticsSnapshot, AutomationJob, AutomationPolicy, Customer, Invoice, Payment, WorkOrder
actor = get_user_model().objects.get(username='v6-disposable-fixture')
assert WorkOrder.objects.filter(number__startswith='V5-MIGRATION-').count() == 2
invoice = Invoice.objects.get(number='V5-MIGRATION-INVOICE')
assert str(invoice.total) == '120.00'
assert str(invoice.total - sum((p.amount for p in Payment.objects.filter(invoice=invoice)), 0)) == '100.00'
snapshot = analytics.refresh_analytics(actor=actor, trigger='verification')
dashboard = analytics.build_analytics_dashboard(snapshot=snapshot)
assert len(dashboard['marts']) == 6 and dashboard['kpis']['wip_current']['value'] == 1
assert dashboard['kpis']['open_balance_current']['value'] == '100.00'
policy, state = automation.initialize_defaults()
state.next_periodic_at = timezone.now() + timedelta(days=1)
state.save(update_fields=['next_periodic_at'])
job = automation.enqueue_manual(actor, mode='rules')
result = automation.run_once(worker_id='v6-delivery-verifier')
job.refresh_from_db()
assert result['status'] == 'completed' and job.status == 'completed' and job.snapshot_id
session = SessionStore()
session['verification_only'] = True
session.save()
print('V6-VERIFY-JSON:'+json.dumps({'orders':WorkOrder.objects.count(),
    'customers':Customer.objects.count(), 'invoice_total':str(invoice.total), 'balance':'100.00',
    'snapshots':AnalyticsSnapshot.objects.count(), 'rows':AnalyticsRow.objects.count(),
    'policy':AutomationPolicy.objects.count(), 'jobs':AutomationJob.objects.count(),
    'completed_jobs':AutomationJob.objects.filter(status='completed').count(),
    'sessions':1, 'snapshot_fingerprint':snapshot.source_fingerprint,
    'rules_job_status':job.status, 'native_invoked':False}))
'''

MUTATE = r'''
import django
django.setup()
from workshop.models import Customer, Invoice
Customer.objects.create(name='Disposable post-backup mutation')
invoice=Invoice.objects.get(number='V5-MIGRATION-INVOICE')
invoice.total=999
invoice.save(update_fields=['total'])
'''

INSPECT = r'''
import django, json
django.setup()
from django.contrib.sessions.models import Session
from workshop.models import AnalyticsRow, AnalyticsSnapshot, AutomationJob, AutomationPolicy, Customer, Invoice, Payment, WorkOrder
invoice = Invoice.objects.get(number='V5-MIGRATION-INVOICE')
paid = sum((payment.amount for payment in Payment.objects.filter(invoice=invoice)), 0)
print('V6-VERIFY-JSON:'+json.dumps({'orders':WorkOrder.objects.count(),
    'customers':Customer.objects.count(), 'invoice_total':str(invoice.total),
    'balance':str(invoice.total-paid), 'snapshots':AnalyticsSnapshot.objects.count(),
    'rows':AnalyticsRow.objects.count(), 'policy':AutomationPolicy.objects.count(),
    'jobs':AutomationJob.objects.count(),
    'completed_jobs':AutomationJob.objects.filter(status='completed').count(),
    'sessions':Session.objects.count(),
    'snapshot_fingerprint':AnalyticsSnapshot.objects.order_by('pk').first().source_fingerprint}))
'''


def _run(arguments: list[str], env: dict[str, str], *, cwd: Path = ROOT) -> str:
    result = subprocess.run(arguments, cwd=cwd, env=env, text=True,
                            stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=180)
    if result.returncode:
        raise RuntimeError(f"command failed ({result.returncode}): {Path(arguments[0]).name} "
                           f"{arguments[1] if len(arguments)>1 else ''}: {result.stderr[-4000:] or result.stdout[-4000:]}")
    return result.stdout


def _child_json(code: str, env: dict[str, str], *, root: Path = ROOT, python: Path | str = sys.executable) -> dict:
    output = _run([str(python), "-c", code], env, cwd=root)
    marked = [line[len(MARKER):] for line in output.splitlines() if line.startswith(MARKER)]
    if len(marked) != 1:
        raise RuntimeError("child did not return one structured verification record")
    return json.loads(marked[0])


def _manage(*args: str, env: dict[str, str], root: Path = ROOT, python: Path | str = sys.executable) -> str:
    return _run([str(python), str(root / "manage.py"), *args], env, cwd=root)


def _sha(content: bytes) -> str:
    return hashlib.sha256(content).hexdigest()


def _http_smoke(base_url: str, username: str, password: str) -> dict:
    opener = build_opener(HTTPCookieProcessor(CookieJar()))
    login = opener.open(base_url + "login/", timeout=10).read().decode("utf-8")
    match = re.search(r'name="csrfmiddlewaretoken" value="([^"]+)"', login)
    if not match:
        raise RuntimeError("login form did not expose a CSRF token")
    payload = urlencode({"username": username, "password": password,
                         "csrfmiddlewaretoken": match.group(1)}).encode("utf-8")
    response = opener.open(Request(base_url + "login/", data=payload,
                                   headers={"Content-Type": "application/x-www-form-urlencoded",
                                            "Referer": base_url + "login/"}), timeout=10)
    if response.geturl().rstrip("/").endswith("login"):
        raise RuntimeError("temporary demo manager could not authenticate")
    pages = {}
    for path, expected in (("analytics/", "Qué mueve tu taller"),
                           ("automations/", "El análisis sigue trabajando")):
        response = opener.open(base_url + path, timeout=10)
        body = response.read().decode("utf-8")
        if response.status != 200 or expected not in body:
            raise RuntimeError(f"authenticated {path} page did not render")
        pages[path] = response.status
    return pages


def _wait_for_worker(db: Path, timeout_seconds: float = 30) -> dict:
    deadline = time.monotonic() + timeout_seconds
    latest = {}
    while time.monotonic() < deadline:
        try:
            con = sqlite3.connect(db.as_uri() + "?mode=ro", uri=True, timeout=2)
            try:
                snapshots = con.execute("SELECT COUNT(*) FROM workshop_analyticssnapshot").fetchone()[0]
                completed = con.execute("SELECT COUNT(*) FROM workshop_automationjob WHERE status='completed'").fetchone()[0]
                worker = con.execute("SELECT status, heartbeat_at FROM workshop_automationworkerstate WHERE id=1").fetchone()
                latest = {"snapshots": snapshots, "completed_jobs": completed,
                          "worker_status": worker[0] if worker else None,
                          "heartbeat_recorded": bool(worker and worker[1])}
                if completed and latest["heartbeat_recorded"]:
                    return latest
            finally:
                con.close()
        except sqlite3.OperationalError:
            pass
        time.sleep(0.5)
    raise RuntimeError(f"extracted worker did not complete a rules job: {latest}")


def _launch_extracted(extracted: Path, python: Path, environment: Path,
                      package_env: dict[str, str], password: str) -> dict:
    logs: queue.Queue[str] = queue.Queue()
    process = subprocess.Popen(
        [str(python), str(extracted / "scripts" / "run_web.py"), "--mode", "demo",
         "--no-browser", "--port", "0", "--watch-parent"],
        cwd=extracted, env=package_env, stdin=subprocess.PIPE,
        stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, bufsize=1,
    )

    def reader():
        for line in process.stdout:
            logs.put(line.strip())

    threading.Thread(target=reader, daemon=True).start()
    try:
        base_url = None
        deadline = time.monotonic() + 45
        while time.monotonic() < deadline:
            if process.poll() is not None:
                raise RuntimeError("extracted server exited before announcing its URL")
            try:
                line = logs.get(timeout=0.5)
            except queue.Empty:
                continue
            match = re.search(r"Milenio demo: (http://127\.0\.0\.1:\d+/)", line)
            if match:
                base_url = match.group(1)
                break
        if base_url is None:
            raise RuntimeError("extracted server did not announce an ephemeral URL")
        pages = _http_smoke(base_url, "v6-package-smoke", password)
        worker = _wait_for_worker(environment / "workshop.sqlite3")
        if process.stdin:
            process.stdin.close()
        try:
            exit_code = process.wait(timeout=15)
        except subprocess.TimeoutExpired as exc:
            raise RuntimeError("extracted server did not stop after stdin closed") from exc
        if exit_code:
            raise RuntimeError(f"extracted server exited with code {exit_code}")
        return {"authenticated_pages": pages, "worker": worker,
                "server_stopped_on_stdin_close": True, "ephemeral_port": True}
    finally:
        if process.poll() is None:
            process.terminate()
            try:
                process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait(timeout=5)
        if process.stdout:
            process.stdout.close()


def _package_smoke(package: Path, temporary: Path, env: dict[str, str]) -> dict:
    """Validate an optional ZIP; install its wheels in a clean venv if present."""
    if not package.is_file():
        raise ValueError("package path is not a file")
    extracted = temporary / "extracted"
    extracted.mkdir()
    with zipfile.ZipFile(package) as archive:
        names = archive.namelist()
        if len(names) != len(set(names)) or "WEB-PACKAGE-MANIFEST.json" not in names:
            raise ValueError("package manifest missing or duplicate entries")
        manifest = json.loads(archive.read("WEB-PACKAGE-MANIFEST.json"))
        if manifest.get("format") != "milenio-web-v6" or manifest.get("includes_private_data") is not False:
            raise ValueError("not a V6 public web package")
        hashes = manifest.get("entries_sha256", {})
        if set(names) != set(hashes) | {"WEB-PACKAGE-MANIFEST.json"}:
            raise ValueError("package file list does not match manifest")
        for name, expected in hashes.items():
            target = extracted / name
            if (name.startswith("/") or "\\" in name or ":" in name
                    or any(part in ("", ".", "..") for part in name.split("/"))
                    or not target.resolve().is_relative_to(extracted.resolve())):
                raise ValueError("unsafe archive path")
            content = archive.read(name)
            if _sha(content) != expected:
                raise ValueError("package content hash mismatch")
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(content)
    result = {"manifest": "milenio-web-v6", "files_verified": len(hashes),
              "sha256": _sha(package.read_bytes()), "offline_fresh_venv": "not_run_no_wheels"}
    wheels = extracted / ".runtime" / "wheels"
    if wheels.is_dir():
        virtualenv = extracted / ".venv"
        venv.EnvBuilder(with_pip=True).create(virtualenv)
        python = virtualenv / ("Scripts/python.exe" if os.name == "nt" else "bin/python")
        _run([str(python), "-m", "pip", "install", "--no-index", "--find-links", str(wheels),
              "-r", str(extracted / "requirements-web.txt")], env, cwd=extracted)
        demo_data = temporary / "demo"
        package_env = dict(env, MILENIO_MODE="demo", MILENIO_DATA_DIR=str(demo_data))
        _manage("check", env=package_env, root=extracted, python=python)
        _manage("migrate", "--noinput", env=package_env, root=extracted, python=python)
        _manage("seed_workshop", "--demo", env=package_env, root=extracted, python=python)
        seeded = _child_json('''
import django, json
django.setup()
from django.contrib.auth import get_user_model
from workshop.models import AnalyticsSnapshot, WorkOrder
actor = get_user_model().objects.get(username='demo_admin')
assert WorkOrder.objects.filter(number__startswith='WO-V6DEMO-').count() == 36
assert AnalyticsSnapshot.objects.count() == 1
assert not actor.is_active and not actor.is_superuser and not actor.has_usable_password()
print('V6-VERIFY-JSON:'+json.dumps({'v6_orders':36,'initial_snapshots':1,'temporary_actor_disabled':True}))
''', package_env, root=extracted, python=python)
        password = secrets.token_urlsafe(30)
        account_env = dict(package_env, MILENIO_SMOKE_PASSWORD=password)
        _child_json('''
import django, json, os
django.setup()
from django.contrib.auth import get_user_model
get_user_model().objects.create_superuser('v6-package-smoke', '', os.environ['MILENIO_SMOKE_PASSWORD'])
print('V6-VERIFY-JSON:{}')
''', account_env, root=extracted, python=python)
        result["offline_fresh_venv"] = "django_check_pass"
        result["first_run_demo"] = seeded
        result["launch"] = _launch_extracted(extracted, python, demo_data, package_env, password)
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", default="artifacts/v6-delivery-verification.json")
    parser.add_argument("--package", type=Path, help="Optional V6 ZIP for hash and offline wheel smoke checks")
    args = parser.parse_args()
    output = Path(args.output).resolve()
    receipt = {"version": "6.0", "checked_at_utc": datetime.now(timezone.utc).isoformat(),
               "status": "fail", "data_scope": "fresh disposable synthetic MILENIO_MODE=test only",
               "migration": {}, "automation": {}, "backup_restore": {}, "package": None,
               "limitations": ["No real customer data, native Codex invocation, client acceptance, or deployment tested."]}
    try:
        with tempfile.TemporaryDirectory(prefix="milenio-v6-delivery-") as directory:
            temporary = Path(directory)
            env = dict(os.environ, MILENIO_MODE="test", MILENIO_DATA_DIR=str(temporary / "instance"),
                       DJANGO_SETTINGS_MODULE="milenio_web.settings", MILENIO_CODEX_ENABLED="0")
            _manage("migrate", "auth", "--noinput", env=env)
            _manage("migrate", "workshop", "0001", "--noinput", env=env)
            old = _child_json(SEED_V5, env)
            _manage("migrate", "--noinput", env=env)
            materialized = _child_json(MATERIALIZE, env)
            receipt["migration"] = {"v5_fixture": old, "v6_preserved": {
                "orders": materialized["orders"], "customers": materialized["customers"],
                "invoice_total": materialized["invoice_total"], "balance": materialized["balance"]},
                "preserved": all(old[key] == materialized[key] for key in old)}
            if not receipt["migration"]["preserved"]:
                raise AssertionError("V5 operational records changed during migration")
            receipt["automation"] = {key: materialized[key] for key in
                                     ("snapshots", "rows", "policy", "jobs", "completed_jobs",
                                      "rules_job_status", "native_invoked")}
            receipt["automation"]["snapshot_fingerprint"] = materialized["snapshot_fingerprint"]
            if not (materialized["snapshots"] >= 2 and materialized["rows"] >= 1 and
                    materialized["policy"] == materialized["jobs"] == materialized["completed_jobs"] == 1):
                raise AssertionError("analytical refresh or queued rules job missing")
            backup = temporary / "verified-backup"
            _manage("backup_workshop", "--output", str(backup), env=env)
            _child_json(MUTATE + "\nprint('V6-VERIFY-JSON:{}')", env)
            _manage("restore_workshop", "--input", str(backup), "--confirm-restore", env=env)
            restored = _child_json(INSPECT, env)
            stable = ("orders", "customers", "invoice_total", "balance", "snapshots", "rows",
                      "policy", "jobs", "completed_jobs", "snapshot_fingerprint")
            receipt["backup_restore"] = {"matching_counts_and_balance": all(restored[key] == materialized[key] for key in stable),
                                         "sessions_before": materialized["sessions"],
                                         "sessions_after": restored["sessions"],
                                         "sessions_purged": restored["sessions"] == 0,
                                         "mode": "test", "restore_command_guard": "unchanged"}
            if not receipt["backup_restore"]["matching_counts_and_balance"] or not receipt["backup_restore"]["sessions_purged"]:
                raise AssertionError("backup/restore did not preserve V6 facts or purge sessions")
            if args.package:
                receipt["package"] = _package_smoke(args.package.resolve(), temporary, env)
            receipt["status"] = "pass"
    except Exception as error:
        receipt["status"] = "fail"
        receipt["error"] = f"{type(error).__name__}: {str(error)[-2500:]}"
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(receipt, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({"status": receipt["status"], "receipt": str(output)}, ensure_ascii=False))
    return 0 if receipt["status"] == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())
