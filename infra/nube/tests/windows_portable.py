"""Create a fictional, pre-0008 portable backup for an actual Windows-to-Linux rehearsal."""
import hashlib
from contextlib import ExitStack
import os
from pathlib import Path
import sys
import tempfile

root = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(root))
destination = Path(sys.argv[1]).resolve()
if destination.exists():
    raise SystemExit("Elige un destino de prueba nuevo.")
with tempfile.TemporaryDirectory(prefix="milenio-windows-origen-") as temp, ExitStack() as cleanup:
    os.environ.update(DJANGO_SETTINGS_MODULE="milenio_web.settings", MILENIO_MODE="live", MILENIO_DATA_DIR=temp,
                      MILENIO_DEPLOYMENT_CONFIG=str(Path(temp) / "fixture-no-server.json"))
    import django
    django.setup()
    from django.conf import settings
    assert Path(settings.DATA_DIR).resolve() == Path(temp).resolve()
    from django.contrib.auth import get_user_model
    from django.contrib.sessions.models import Session
    from django.core.management import call_command
    from django.db import connections
    from django.db.migrations.executor import MigrationExecutor
    cleanup.callback(connections.close_all)
    from django.utils.timezone import now
    from PIL import Image

    call_command("migrate", interactive=False, verbosity=0)
    call_command("migrate", "workshop", "0007", interactive=False, verbosity=0)
    legacy = MigrationExecutor(connections["default"]).loader.project_state(
        [("workshop", "0007_photo_ai_controls")]
    ).apps
    Customer, Vehicle, WorkOrder, Invoice, Payment, Inspection = [
        legacy.get_model("workshop", name)
        for name in ("Customer", "Vehicle", "WorkOrder", "Invoice", "Payment", "Inspection")
    ]
    actor = get_user_model().objects.create_user("operador-sintetico")
    customer = Customer.objects.create(name="Cliente sintético")
    car = Vehicle.objects.create(customer=customer, make="Prueba", model="A", plate="DEMO01")
    order = WorkOrder.objects.create(vehicle=car, number="WO-PRUEBA", complaint="Ensayo")
    invoice = Invoice.objects.create(work_order=order, number="F-1", subtotal="100", tax="16", total="116", due_at=now())
    Payment.objects.create(invoice=invoice, amount="50", method="efectivo", reference="ensayo", idempotency_key="test", created_by_id=actor.pk)
    settings.MEDIA_ROOT.mkdir()
    photo = "prueba.png"
    Image.new("RGB", (8, 8), "green").save(settings.MEDIA_ROOT / photo)
    Inspection.objects.create(work_order=order, area="Prueba", result="okay", photo=photo, created_by_id=actor.pk)
    Session.objects.create(session_key="synthetic", session_data="x", expire_date=now())
    call_command("backup_workshop", output=str(destination))
with (destination / "manifest.json").open("rb") as stream:
    print(hashlib.file_digest(stream, "sha256").hexdigest())
