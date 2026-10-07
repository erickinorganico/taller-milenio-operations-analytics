"""Commercial records. Writes go through services; unknown facts remain unknown."""
import uuid
from django.conf import settings
from django.core.validators import MinValueValidator
from django.db import models
from django.utils import timezone


class Stamped(models.Model):
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True


class ResearchBatch(Stamped):
    key = models.CharField(max_length=80, unique=True)
    title = models.CharField(max_length=180)
    source = models.CharField(max_length=40)
    query = models.TextField(blank=True)
    notes = models.TextField(blank=True)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)

    def __str__(self):
        return self.title


class SalesAccount(Stamped):
    class Stage(models.TextChoices):
        RESEARCH = "research", "Investigación"
        READY = "ready", "Listo para explorar"
        CONVERSATION = "conversation", "En conversación"
        QUALIFIED = "qualified", "Necesidad confirmada"
        PROPOSAL = "proposal", "Propuesta"
        PILOT = "pilot", "Primer servicio"
        RECURRENCE_PENDING = "recurrence_pending", "Recurrencia por confirmar"
        ACTIVE = "active", "Cliente recurrente"
        LOST = "lost", "Cerrado sin venta"
        SUPPRESSED = "suppressed", "No contactar"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField("Empresa", max_length=200)
    domain = models.CharField("Dominio empresarial", max_length=253, blank=True, null=True, db_index=True)
    branch = models.CharField("Sucursal / base", max_length=120, blank=True)
    website = models.URLField("Sitio web", blank=True)
    city = models.CharField("Ciudad", max_length=100, default="Tijuana")
    segment = models.CharField("Segmento", max_length=120, blank=True)
    source = models.CharField("Canal de descubrimiento", max_length=40, choices=[("google_maps", "Google / Maps"), ("canacintra", "CANACINTRA"), ("social", "Facebook / Instagram"), ("linkedin", "LinkedIn"), ("referral", "Referencia"), ("website", "Sitio empresarial"), ("manual", "Captura directa")], default="manual")
    source_url = models.URLField("URL de descubrimiento", blank=True)
    identity_confirmed = models.BooleanField("Identidad empresarial revisada", default=False)
    stage = models.CharField(max_length=20, choices=Stage.choices, default=Stage.RESEARCH, db_index=True)
    owner = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="sales_accounts")
    next_action = models.CharField("Próxima acción", max_length=240, blank=True)
    next_action_on = models.DateField("Fecha de seguimiento", blank=True, null=True, db_index=True)
    notes = models.TextField("Notas", blank=True)
    version = models.PositiveIntegerField(default=1)
    batch = models.ForeignKey(ResearchBatch, on_delete=models.PROTECT, blank=True, null=True)
    operational_customer = models.OneToOneField("workshop.Customer", on_delete=models.PROTECT, blank=True, null=True)
    is_demo = models.BooleanField(default=False)
    recurrence_basis = models.CharField("Base de recurrencia", max_length=20, default="pending", choices=[("pending", "Por confirmar"), ("second_order", "Segunda orden real confirmada"), ("current_plan", "Plan vigente confirmado")])
    recurrence_evidence = models.ForeignKey("Evidence", on_delete=models.PROTECT, null=True, blank=True, related_name="recurring_accounts", verbose_name="Evidencia revisada de recurrencia")

    class Meta:
        ordering = ["next_action_on", "name"]

    def __str__(self):
        return f"{self.name} · {self.branch}" if self.branch else self.name


class Evidence(Stamped):
    account = models.ForeignKey(SalesAccount, on_delete=models.CASCADE, related_name="evidence")
    topic = models.CharField("Tipo de evidencia", max_length=30, choices=[("identity", "Identidad"), ("vehicles", "Vehículos y combustible"), ("need", "Necesidad"), ("contact", "Contacto"), ("coverage", "Cobertura de grúa"), ("recurrence", "Segunda orden o plan vigente"), ("website", "Texto de sitio")])
    source_url = models.URLField("Fuente pública", blank=True)
    source_note = models.CharField("Fuente directa / referencia", max_length=240, blank=True)
    excerpt = models.TextField("Hecho o fragmento observado")
    captured_at = models.DateTimeField("Fecha de consulta", default=timezone.now)
    reviewed = models.BooleanField("Revisado por una persona", default=False)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)


class FleetProfile(Stamped):
    account = models.OneToOneField(SalesAccount, on_delete=models.CASCADE, related_name="fleet")
    fuel = models.CharField("Combustible", max_length=20, default="unknown", choices=[("unknown", "Por confirmar"), ("gasoline", "Gasolina"), ("mixed", "Mixta"), ("diesel", "Diésel"), ("electric", "Eléctrica"), ("hybrid", "Híbrida")])
    vehicle_type = models.CharField("Tipo de unidades evaluadas", max_length=20, default="unknown", choices=[("unknown", "Por confirmar"), ("light", "Autos / pickups / vans"), ("truck", "Camiones")])
    total_units = models.PositiveIntegerField("Unidades totales conocidas", blank=True, null=True, validators=[MinValueValidator(1)])
    compatible_units = models.PositiveIntegerField("Unidades ligeras a gasolina confirmadas", blank=True, null=True)
    vehicle_evidence = models.ForeignKey(Evidence, on_delete=models.PROTECT, related_name="vehicle_profiles", blank=True, null=True)
    need_confirmed = models.BooleanField("Necesidad confirmada", default=False)
    need_evidence = models.ForeignKey(Evidence, on_delete=models.PROTECT, related_name="need_profiles", blank=True, null=True)
    towing_confirmed = models.BooleanField("Despacho confirmó capacidad y cobertura para estas unidades", default=False)
    towing_evidence = models.ForeignKey(Evidence, on_delete=models.PROTECT, related_name="tow_profiles", blank=True, null=True)


class BusinessContact(Stamped):
    account = models.ForeignKey(SalesAccount, on_delete=models.CASCADE, related_name="contacts")
    name = models.CharField("Nombre / área", max_length=180)
    role = models.CharField("Cargo", max_length=120, blank=True)
    email = models.EmailField("Correo empresarial", blank=True)
    phone = models.CharField("Teléfono empresarial", max_length=40, blank=True)
    source_url = models.URLField("Fuente del contacto", blank=True)
    source_note = models.CharField("Fuente directa", max_length=240, blank=True)
    published_business = models.BooleanField("Canal empresarial publicado o proporcionado por la empresa", default=False)
    deliverability = models.CharField("Estado del correo", max_length=20, choices=[("unknown", "Sin verificar"), ("confirmed", "Confirmado por respuesta / empresa"), ("bounced", "Rebotó")], default="unknown")
    captured_at = models.DateTimeField(default=timezone.now)

    def __str__(self):
        return f"{self.name} — {self.email or self.phone}"


class Suppression(Stamped):
    account = models.OneToOneField(SalesAccount, on_delete=models.PROTECT, related_name="suppression")
    reason = models.CharField(max_length=240)
    emails = models.JSONField(default=list)
    domain = models.CharField(max_length=253, blank=True)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)


class SalesOpportunity(Stamped):
    account = models.ForeignKey(SalesAccount, on_delete=models.CASCADE, related_name="opportunities")
    title = models.CharField("Oportunidad", max_length=180)
    service = models.CharField("Servicio", max_length=20, choices=[("mechanics", "Mecánica"), ("towing", "Grúa")])
    amount = models.DecimalField("Importe estimado MXN (si se conoce)", max_digits=12, decimal_places=2, blank=True, null=True, validators=[MinValueValidator(0)])
    status = models.CharField(max_length=20, choices=[("open", "Abierta"), ("pending_acceptance", "Revisión pendiente de aceptación"), ("won", "Ganada"), ("lost", "Perdida")], default="open")
    work_order = models.ForeignKey("workshop.WorkOrder", on_delete=models.PROTECT, null=True, blank=True)
    tow_service = models.ForeignKey("workshop.TowService", on_delete=models.PROTECT, null=True, blank=True)
    service_proposal = models.ForeignKey("SalesProposal", on_delete=models.PROTECT, null=True, blank=True, related_name="linked_services", verbose_name="Propuesta aceptada para el servicio vinculado")

    def __str__(self):
        return self.title


class SalesProposal(Stamped):
    opportunity = models.ForeignKey(SalesOpportunity, on_delete=models.CASCADE, related_name="proposals")
    revision = models.PositiveIntegerField()
    scope = models.TextField("Alcance y unidades")
    terms = models.TextField("Condiciones, vigencia y exclusiones")
    amount = models.DecimalField("Importe MXN", max_digits=12, decimal_places=2, validators=[MinValueValidator(0)])
    valid_until = models.DateField("Vigencia")
    accepted_at = models.DateTimeField(blank=True, null=True)
    acceptance_reference = models.CharField(max_length=240, blank=True)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)

    class Meta:
        constraints = [models.UniqueConstraint(fields=["opportunity", "revision"], name="unique_sales_proposal_revision")]


class Interaction(Stamped):
    account = models.ForeignKey(SalesAccount, on_delete=models.CASCADE, related_name="interactions")
    kind = models.CharField("Resultado", max_length=20, choices=[("note", "Nota interna"), ("sent", "Contacto realizado"), ("reply", "Respuesta recibida"), ("meeting", "Conversación / visita"), ("bounce", "Correo rebotado"), ("optout", "Pidió no contactar")])
    summary = models.TextField("Resumen")
    occurred_at = models.DateTimeField("Fecha del evento", default=timezone.now)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)


class AuditEvent(models.Model):
    account = models.ForeignKey(SalesAccount, on_delete=models.PROTECT, null=True)
    action = models.CharField(max_length=60)
    actor = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="commercial_audit_events")
    details = models.JSONField(default=dict)
    created_at = models.DateTimeField(default=timezone.now)


class ImportReceipt(models.Model):
    fingerprint = models.CharField(max_length=64, unique=True)
    summary = models.JSONField(default=dict)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    created_at = models.DateTimeField(default=timezone.now)


from .mail_models import Mailbox, MailEnrollment, MailMessage, MailInbound, MailWorkerLease  # noqa: E402,F401

from .agent_models import AgentCredential, AgentRequest, ConversationClaim, AgentDraft  # noqa: E402,F401
