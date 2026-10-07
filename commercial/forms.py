from django import forms
from django.contrib.auth import get_user_model
from django.db.models import Q
from .models import BusinessContact, Evidence, FleetProfile, Interaction, SalesAccount, SalesOpportunity, SalesProposal


class StyledModelForm(forms.ModelForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            if isinstance(field, forms.DateField) and not isinstance(field, forms.DateTimeField):
                field.widget = forms.DateInput(attrs={"type": "date"}, format="%Y-%m-%d")
            if isinstance(field.widget, forms.Textarea): field.widget.attrs["rows"] = 3


class AccountForm(StyledModelForm):
    class Meta:
        model = SalesAccount
        fields = ["name", "branch", "website", "city", "segment", "source", "source_url", "identity_confirmed", "owner", "next_action", "next_action_on", "recurrence_basis", "recurrence_evidence", "notes"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["owner"].queryset = get_user_model().objects.filter(is_active=True).filter(Q(is_superuser=True) | Q(groups__name__in=["manager", "advisor"])).distinct()
        self.fields["recurrence_evidence"].queryset = Evidence.objects.filter(account=self.instance, topic="recurrence", reviewed=True) if not self.instance._state.adding else Evidence.objects.none()
        self.fields["recurrence_evidence"].label_from_instance = lambda obj: f"#{obj.pk} · {obj.excerpt[:100]}"
        self.fields["recurrence_evidence"].help_text = "Cita la segunda orden o el plan vigente y su fuente. Sin confirmación, conserva Por confirmar."


class EvidenceForm(StyledModelForm):
    class Meta:
        model = Evidence
        fields = ["topic", "source_url", "source_note", "excerpt", "captured_at", "reviewed"]


class ContactForm(StyledModelForm):
    existing_contact = forms.ModelChoiceField(queryset=BusinessContact.objects.none(), required=False, label="Contacto a corregir (vacío: nuevo)")

    class Meta:
        model = BusinessContact
        fields = ["name", "role", "email", "phone", "source_url", "source_note", "published_business", "deliverability"]

    def __init__(self, *args, account=None, **kwargs):
        super().__init__(*args, **kwargs)
        if account: self.fields["existing_contact"].queryset = account.contacts.all()


class FleetForm(StyledModelForm):
    class Meta:
        model = FleetProfile
        fields = ["fuel", "vehicle_type", "total_units", "compatible_units", "vehicle_evidence", "need_confirmed", "need_evidence", "towing_confirmed", "towing_evidence"]

    def __init__(self, *args, account, **kwargs):
        super().__init__(*args, **kwargs)
        for field, topic in [("vehicle_evidence", "vehicles"), ("need_evidence", "need"), ("towing_evidence", "coverage")]:
            self.fields[field].queryset = account.evidence.filter(topic=topic, reviewed=True)
            self.fields[field].label_from_instance = lambda obj: f"#{obj.pk} · {obj.excerpt[:100]}"


class InteractionForm(StyledModelForm):
    class Meta:
        model = Interaction
        fields = ["kind", "summary", "occurred_at"]


class OpportunityForm(StyledModelForm):
    class Meta:
        model = SalesOpportunity
        fields = ["title", "service", "amount"]


class ProposalForm(StyledModelForm):
    class Meta:
        model = SalesProposal
        fields = ["opportunity", "scope", "terms", "amount", "valid_until"]

    def __init__(self, *args, account, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["opportunity"].queryset = account.opportunities.exclude(status="lost")


class StageForm(forms.Form):
    stage = forms.ChoiceField(label="Nueva etapa", choices=[c for c in SalesAccount.Stage.choices if c[0] != "suppressed"])


class AcceptForm(forms.Form):
    proposal_id = forms.IntegerField(min_value=1, label="Número de propuesta")
    reference = forms.CharField(max_length=240, label="Quién aceptó, cuándo y referencia")


class HandoffForm(forms.Form):
    customer = forms.ModelChoiceField(queryset=None, required=False, label="Cliente operativo existente (vacío: crear)")

    def __init__(self, *args, **kwargs):
        from workshop.models import Customer
        super().__init__(*args, **kwargs)
        self.fields["customer"].queryset = Customer.objects.order_by("name")


class LinkForm(forms.Form):
    opportunity = forms.ModelChoiceField(queryset=None, label="Oportunidad")
    work_order = forms.ModelChoiceField(queryset=None, required=False, label="Orden de mecánica")
    tow_service = forms.ModelChoiceField(queryset=None, required=False, label="Servicio de grúa")

    def __init__(self, *args, account, **kwargs):
        from workshop.models import WorkOrder, TowService
        super().__init__(*args, **kwargs)
        self.fields["opportunity"].queryset = account.opportunities.all()
        self.fields["work_order"].queryset = WorkOrder.objects.filter(vehicle__customer_id=account.operational_customer_id) if account.operational_customer_id else WorkOrder.objects.none()
        self.fields["tow_service"].queryset = TowService.objects.filter(customer_id=account.operational_customer_id) if account.operational_customer_id else TowService.objects.none()


class ImportForm(forms.Form):
    file = forms.FileField(label="CSV de candidatos", widget=forms.ClearableFileInput(attrs={"accept": ".csv"}))


class ExtractForm(forms.Form):
    file = forms.FileField(label="Reporte JSON del extractor local", widget=forms.ClearableFileInput(attrs={"accept": ".json"}))
