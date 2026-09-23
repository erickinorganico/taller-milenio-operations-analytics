from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User
from .access import ROLES
from . import models as m

LABELS = {"name":"Nombre", "phone":"Teléfono", "email":"Correo", "kind":"Tipo", "notes":"Notas", "customer":"Cliente", "plate":"Placas", "vin":"VIN / número de serie", "make":"Marca", "model":"Modelo", "year":"Año", "odometer":"Kilometraje", "vehicle":"Vehículo", "scheduled_at":"Fecha y hora", "reason":"Motivo", "status":"Estado", "complaint":"Solicitud del cliente", "assigned_to":"Responsable", "promised_at":"Entrega prometida", "area":"Punto de inspección", "result":"Resultado", "photo":"Fotografía", "sku":"SKU / código", "unit":"Unidad", "cost":"Costo unitario", "sale_price":"Precio de venta", "reorder_point":"Punto de reposición", "supplier":"Proveedor", "number":"Folio", "expected_at":"Recepción prevista", "part":"Refacción", "quantity":"Cantidad", "unit_cost":"Costo unitario", "description":"Descripción", "start_date":"Inicio", "end_date":"Fin", "monthly_fee":"Cuota mensual", "sla_hours":"Compromiso de horas", "due_date":"Fecha de vencimiento", "due_odometer":"Kilometraje de mantenimiento", "work_order":"Orden relacionada", "origin":"Origen", "destination":"Destino", "operator_name":"Operador", "safety_reference":"Referencia de autorización humana", "minutes":"Minutos trabajados", "unit_price":"Precio unitario", "tax_rate":"Tasa de impuesto (0 a 1)", "approval_name":"Nombre de quien autoriza", "approval_reference":"Referencia de autorización", "amount":"Importe", "method":"Método", "reference":"Referencia", "due_at":"Vencimiento", "title":"Título", "outcome":"Resultado y evidencia"}

def model_form(model, fields, data=None, files=None, instance=None, initial=None):
    factory = forms.modelform_factory(model, fields=fields, labels={f:LABELS.get(f,f.replace('_',' ').capitalize()) for f in fields})
    form = factory(data=data, files=files, instance=instance, initial=initial)
    for name, field in form.fields.items():
        if isinstance(field, forms.DateTimeField):
            field.widget = forms.DateTimeInput(attrs={"type":"datetime-local"}, format="%Y-%m-%dT%H:%M")
            field.input_formats = ["%Y-%m-%dT%H:%M", "%Y-%m-%dT%H:%M:%S"]
        elif isinstance(field, forms.DateField):
            field.widget = forms.DateInput(attrs={"type":"date"}, format="%Y-%m-%d")
        elif isinstance(field.widget, forms.Textarea):
            field.widget.attrs["rows"] = 3
    return form

class SetupForm(UserCreationForm):
    first_name = forms.CharField(label="Tu nombre", max_length=150)
    class Meta:
        model = User
        fields = ["username", "first_name", "password1", "password2"]

class TeamForm(UserCreationForm):
    first_name = forms.CharField(label="Nombre", max_length=150)
    role = forms.ChoiceField(label="Rol", choices=list(ROLES.items()))
    class Meta:
        model = User
        fields = ["username", "first_name", "role", "password1", "password2"]

class MoneyLineForm(forms.Form):
    description = forms.CharField(label="Trabajo o refacción", max_length=240)
    kind = forms.ChoiceField(label="Tipo", choices=[("labor","Mano de obra"),("part","Refacción"),("service","Servicio externo")])
    quantity = forms.DecimalField(label="Cantidad", min_value=0.01, max_digits=10, decimal_places=2, initial=1)
    unit_price = forms.DecimalField(label="Precio unitario", min_value=0, max_digits=12, decimal_places=2)
    unit_cost = forms.DecimalField(label="Costo unitario conocido", min_value=0, max_digits=12, decimal_places=2, required=False, help_text="Vacío significa costo desconocido, no costo cero.")
    part = forms.ModelChoiceField(label="Refacción del catálogo", queryset=m.Part.objects.all(), required=False)

class PaymentForm(forms.Form):
    amount = forms.DecimalField(label="Importe recibido", min_value=0.01, max_digits=12, decimal_places=2)
    method = forms.ChoiceField(label="Método", choices=[("cash","Efectivo"),("transfer","Transferencia"),("card","Tarjeta"),("other","Otro")])
    reference = forms.CharField(label="Referencia / recibo", max_length=200)
    idempotency_key = forms.CharField(widget=forms.HiddenInput, max_length=100)

class InspectionForm(forms.ModelForm):
    class Meta:
        model = m.Inspection
        fields = ["area", "result", "notes", "photo"]
        labels = LABELS
        widgets = {"notes":forms.Textarea(attrs={"rows":3})}
    def clean_photo(self):
        photo = self.cleaned_data.get("photo")
        if photo:
            if photo.size > 5 * 1024 * 1024:
                raise forms.ValidationError("La fotografía debe pesar como máximo 5 MB.")
            if getattr(photo, "image", None) and (photo.image.width * photo.image.height > 20_000_000 or photo.image.format not in {"JPEG", "PNG", "WEBP"}):
                raise forms.ValidationError("Usa una foto JPEG, PNG o WebP de hasta 20 megapíxeles.")
        return photo


class TeamEditForm(forms.Form):
    first_name = forms.CharField(label="Nombre", max_length=150)
    role = forms.ChoiceField(label="Rol", choices=list(ROLES.items()))
    is_active = forms.BooleanField(label="Cuenta activa", required=False)
    password1 = forms.CharField(label="Nueva contraseña (opcional)", widget=forms.PasswordInput, required=False)
    password2 = forms.CharField(label="Repite la nueva contraseña", widget=forms.PasswordInput, required=False)

    def __init__(self, *args, member, **kwargs):
        self.member = member
        super().__init__(*args, **kwargs)
        if member.is_superuser:
            self.fields["role"].disabled = True
            self.initial["role"] = "manager"

    def clean(self):
        from django.contrib.auth.password_validation import validate_password
        values = super().clean()
        if values.get("password1") != values.get("password2"):
            raise forms.ValidationError("Las contraseñas no coinciden.")
        if values.get("password1"):
            validate_password(values["password1"], self.member)
        return values
