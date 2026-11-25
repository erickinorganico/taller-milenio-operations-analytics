"""Order filters respect the caller's existing order visibility."""
from urllib.parse import urlencode

from django import forms
from django.contrib.auth.models import User

from .list_filters import DateRangeForm, filter_dates
from .models import WorkOrder


class OrderFilterForm(DateRangeForm):
    q = forms.CharField(label="Buscar orden", required=False, max_length=200,
        widget=forms.TextInput(attrs={"type": "search", "placeholder": "Orden, cliente o placa"}))
    status = forms.ChoiceField(label="Etapa", required=False, choices=[("", "Todas")] + WorkOrder.Status.choices)
    owner = forms.ChoiceField(label="Responsable", required=False)
    attention = forms.ChoiceField(label="Atención", required=False, choices=[("", "Todas"),
        ("unassigned", "Abiertas sin responsable"), ("undated", "Abiertas sin fecha prometida"), ("late", "Abiertas atrasadas")])
    mine = forms.BooleanField(label="Solo mis órdenes", required=False)
    date_field = forms.ChoiceField(label="Filtrar fechas de", required=False,
        choices=[("", "Recepción"), ("promised", "Entrega prometida")])

    def __init__(self, data, *, visible_orders):
        super().__init__(data, auto_id="filter_%s")
        users = User.objects.filter(pk__in=visible_orders.values("assigned_to_id")).order_by("first_name", "username")
        self.fields["owner"].choices = [("", "Cualquier responsable"), ("unassigned", "Sin asignar")] + [
            (str(user.pk), user.get_full_name() or user.username) for user in users]
        self.order_fields(["q", "status", "owner", "attention", "mine", "date_field", "start", "end"])


def order_filter_context(form):
    values = form.cleaned_data if form.is_valid() else {}
    filters = {key: "1" if key == "mine" else value.isoformat() if key in {"start", "end"} else value
               for key, value in values.items() if value}
    return {"list_filter_form": form, "filter_query": urlencode({key: value for key, value in filters.items() if key != "q"}),
            "query": values.get("q", ""), "filtered": bool(filters), "clear_url": "/orders/"}


def dates_for_orders(queryset, values):
    return filter_dates(queryset, values, "promised_at" if values.get("date_field") == "promised" else "created_at")
