"""Validated GET filters; dates include the whole day in the workshop timezone."""
from datetime import datetime, time, timedelta

from django import forms
from django.utils import timezone


class DateRangeForm(forms.Form):
    start = forms.DateField(label="Desde", required=False, widget=forms.DateInput(attrs={"type": "date"}))
    end = forms.DateField(label="Hasta", required=False, widget=forms.DateInput(attrs={"type": "date"}))

    def clean(self):
        values = super().clean()
        if values.get("start") and values.get("end") and values["start"] > values["end"]:
            raise forms.ValidationError("La fecha desde debe ser anterior o igual a la fecha hasta.")
        # Leave room for the exclusive next-day boundary.
        if values.get("end") and values["end"].year == 9999:
            self.add_error("end", "Usa una fecha anterior al año 9999.")
        return values


def filter_dates(queryset, values, field="created_at"):
    zone = timezone.get_current_timezone()
    for key, lookup in (("start", "gte"), ("end", "lt")):
        value = values.get(key)
        if value:
            if key == "end":
                value += timedelta(days=1)
            boundary = timezone.make_aware(datetime.combine(value, time.min), zone)
            queryset = queryset.filter(**{f"{field}__{lookup}": boundary})
    return queryset
