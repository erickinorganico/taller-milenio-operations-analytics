from decimal import Decimal

from django import forms
from django.contrib import messages
from django.core.exceptions import ValidationError
from django.db import IntegrityError, OperationalError
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_http_methods

from . import models as m, photo_quotes
from .access import require


class QuotePhotoRow(forms.Form):
    source_id = forms.IntegerField(widget=forms.HiddenInput)
    selected = forms.BooleanField(label='Agregar este servicio', required=False)
    description = forms.CharField(label='Concepto a cotizar', max_length=250, required=False)
    kind = forms.ChoiceField(label='Tipo', choices=[('','Selecciona el tipo'),*m.QuoteLine.Kind.choices], required=False)
    quantity = forms.DecimalField(label='Cantidad', max_digits=12, decimal_places=3, min_value=Decimal('0.001'), required=False)
    unit_price = forms.DecimalField(label='Precio unitario', max_digits=14, decimal_places=2, min_value=0, required=False)
    unit_cost = forms.DecimalField(label='Costo unitario (si se conoce)', max_digits=14, decimal_places=2, min_value=0, required=False)
    part_sku = forms.CharField(label='SKU de refacción', max_length=80, required=False,
        help_text='Para Refacción, utiliza un SKU que ya exista en Inventario.')

    def clean(self):
        data = super().clean()
        if data.get('selected'):
            for name in ('description','kind','quantity','unit_price'):
                if data.get(name) in (None, '') and name not in self.errors:
                    self.add_error(name,'Completa este dato para agregar el servicio.')
            if data.get('kind') == 'part' and not data.get('part_sku'):
                self.add_error('part_sku','Selecciona el SKU de una refacción existente.')
        return data


class QuotePhotoSetBase(forms.BaseFormSet):
    def clean(self):
        super().clean()
        if not any(self.errors) and not any(form.cleaned_data.get('selected') for form in self.forms):
            raise forms.ValidationError('Selecciona al menos un servicio para continuar.')


QuotePhotoSet = forms.formset_factory(QuotePhotoRow, formset=QuotePhotoSetBase,
    extra=0, max_num=50, validate_max=True, absolute_max=50)


class QuotePhotoHeader(forms.Form):
    receipt = forms.CharField(widget=forms.HiddenInput)
    tax_rate = forms.DecimalField(label='Tasa aplicable (0 a 1)', max_digits=6, decimal_places=4, min_value=0, max_value=1)
    checked = forms.BooleanField(label='Revisé los conceptos, cantidades y precios para este borrador')


@require('reception')
@require_http_methods(['GET','POST'])
def photo_quote(request, pk):
    order = get_object_or_404(m.WorkOrder.objects.select_related('vehicle__customer'), pk=pk)
    try:
        plan = photo_quotes.prepare(order,request.user)
    except ValidationError as error:
        messages.error(request,' · '.join(error.messages))
        return redirect(f'/orders/{pk}/#documents')
    initial = [{'source_id':source.pk, 'selected':False, 'description':source.description,
        'kind':source.kind if source.kind != 'unknown' else '', 'quantity':source.quantity,
        'unit_price':source.unit_price, 'unit_cost':source.unit_cost, 'part_sku':source.part_sku} for source in plan['sources']]
    header = QuotePhotoHeader(request.POST if request.method == 'POST' else None,
        initial={'receipt':plan['receipt'],'tax_rate':plan['quote'].tax_rate if plan['quote'] else 0})
    if plan['quote']:
        header.fields['tax_rate'].disabled = True
    rows = QuotePhotoSet(request.POST if request.method == 'POST' else None, initial=initial, prefix='services')
    status = 200
    if request.method == 'POST':
        header_ok, rows_ok = header.is_valid(), rows.is_valid()
        if header_ok and rows_ok:
            selected = [{k:v for k,v in form.cleaned_data.items() if k != 'selected'}
                        for form in rows if form.cleaned_data.get('selected')]
            try:
                quote = photo_quotes.apply(order=order,actor=request.user,receipt=header.cleaned_data['receipt'],
                    rows=selected,tax_rate=header.cleaned_data['tax_rate'])
            except ValidationError as error:
                header.add_error(None,error)
                status = 409
            except (IntegrityError,OperationalError):
                header.add_error(None,'Otra actualización impidió guardar. Vuelve a abrir la orden para revisar el presupuesto.')
                status = 409
            else:
                messages.success(request,f'Servicios guardados en el presupuesto v{quote.version} como borrador.')
                return redirect(f'/orders/{pk}/#quote')
        else:
            status = 400
    sources = {source.pk:source for source in plan['sources']}
    for form in rows:
        try:
            form.source = sources.get(int(form['source_id'].value()))
        except (TypeError,ValueError):
            form.source = None
    return render(request,'workshop/photo_quote.html',{'title':'Cotizar servicios de fotos','section':'Órdenes',
        'order':order,'header_form':header,'rows':rows,'quote':plan['quote'],'more':plan['more']},status=status)
