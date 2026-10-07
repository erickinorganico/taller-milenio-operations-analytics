from django.contrib import messages
from django import forms
from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_http_methods
from workshop.access import require
from .models import Mailbox, MailEnrollment, MailMessage, MailInbound, BusinessContact
from .mail_flow import enroll, pause_account, queue_message, SIGNATURE
from .rules import suppressed
from .services import audit


class MailSettingsForm(forms.Form):
    site_url = forms.URLField(required=False, label='Sitio público (opcional)')
    video_url = forms.URLField(required=False, label='Video público (opcional)')
    public_assets_confirmed = forms.BooleanField(required=False, label='Comprobé que los enlaces abren sin iniciar sesión')
    holidays = forms.CharField(required=False, label='Fechas sin envíos: AAAA-MM-DD, separadas por comas')

    def clean_holidays(self):
        from datetime import date
        try:
            return sorted(set(date.fromisoformat(x.strip()).isoformat() for x in self.cleaned_data['holidays'].split(',') if x.strip()))
        except ValueError:
            raise forms.ValidationError('Usa fechas válidas con formato AAAA-MM-DD.')

    def clean(self):
        result = super().clean()
        for name in ('site_url', 'video_url'):
            if result.get(name) and not result[name].startswith('https://'):
                self.add_error(name, 'Usa un enlace HTTPS público.')
        return result


@require('manage')
@require_http_methods(['GET', 'POST'])
def dashboard(request):
    box, _ = Mailbox.objects.get_or_create(pk=1)
    if request.method == 'POST':
        try:
            with transaction.atomic():
                action = request.POST.get('action')
                if action == 'enroll':
                    enroll(get_object_or_404(BusinessContact, pk=request.POST.get('contact')), request.user)
                    messages.success(request, 'Empresa incorporada. El primer correo ya está en la cola.')
                elif action == 'catalog':
                    from .catalog_import import import_catalog
                    source = settings.DATA_DIR / 'imports/catalog.json'
                    if not source.is_file():
                        source = settings.BASE_DIR.parent / 'outputs/ampliacion-prospeccion-20261003T220600Z/datos-revisados.json'
                    if not source.is_file():
                        raise ValidationError('No se encuentra el catálogo vigente junto al proyecto.')
                    result = import_catalog(source, request.user)
                    messages.success(request, 'Catálogo disponible en el CRM: ' + str(result))
                elif action == 'toggle':
                    box = Mailbox.objects.select_for_update().get(pk=1)
                    if not box.enabled and (not box.connected or not box.owner_id):
                        raise ValidationError('Conecta Gmail antes de activar el flujo.')
                    box.enabled = not box.enabled
                    box.save()
                    audit(None, request.user, 'mail_toggle', enabled=box.enabled)
                elif action == 'auto':
                    box.auto_reply = not box.auto_reply; box.save(update_fields=['auto_reply'])
                    audit(None, request.user, 'mail_auto_toggle', enabled=box.auto_reply)
                elif action == 'settings':
                    form = MailSettingsForm(request.POST)
                    if not form.is_valid():
                        raise ValidationError(' '.join(str(e) for values in form.errors.values() for e in values))
                    for name, value in form.cleaned_data.items():
                        setattr(box, name, value)
                    box.save(update_fields=list(form.cleaned_data))
                    audit(None, request.user, 'mail_settings_updated', **form.cleaned_data)
                    messages.success(request, 'Configuración guardada. Los enlaces se incluyen en mensajes preparados a partir de ahora.')
                elif action == 'pause':
                    e = get_object_or_404(MailEnrollment, pk=request.POST.get('enrollment'))
                    pause_account(e.account_id, 'Pausa manual de Gerencia', manual=True)
                    audit(e.account, request.user, 'mail_paused')
                elif action == 'cancel':
                    m = get_object_or_404(MailMessage, pk=request.POST.get('message'))
                    MailMessage.objects.filter(pk=m.pk, status='queued').update(status='cancelled', error='Cancelado por Gerencia')
                    pause_account(m.enrollment.account_id, 'Mensaje cancelado por Gerencia', manual=True)
                    audit(m.enrollment.account, request.user, 'mail_cancelled', message=str(m.pk))
                else:
                    raise ValidationError('Acción no reconocida.')
        except (ValidationError, IntegrityError) as exc:
            messages.error(request, '; '.join(exc.messages) if isinstance(exc, ValidationError) else 'Registro duplicado; no se creó otro envío.')
        return redirect('commercial:mail')
    contacts = BusinessContact.objects.filter(published_business=True, account__identity_confirmed=True, account__is_demo=False,
        account__mail_enrollment__isnull=True, account__stage__in=['research', 'ready']).exclude(email='').exclude(deliverability='bounced').select_related('account')
    return render(request, 'commercial/mail.html', {
        'box': box, 'contacts': contacts, 'enrollments': MailEnrollment.objects.select_related('account'),
        'outbox': MailMessage.objects.select_related('enrollment__account').order_by('-created_at')[:100],
        'inbox': MailInbound.objects.select_related('enrollment__account').order_by('-received_at')[:100],
        'sent': MailMessage.objects.filter(status='sent').count(),
        'replies': MailInbound.objects.filter(human_reply=True).exclude(category__in=['optout','negative']).count(),
        'pending': MailMessage.objects.filter(status='queued').count(),
        'review': MailInbound.objects.filter(needs_review=True).count(),
        'unknown': MailMessage.objects.filter(status='unknown').count(),
        'settings_form': MailSettingsForm(initial={'site_url': box.site_url, 'video_url': box.video_url,
            'public_assets_confirmed': box.public_assets_confirmed, 'holidays': ', '.join(box.holidays)}),
    })


@require('manage')
@require_http_methods(['GET', 'POST'])
def incoming(request, pk):
    event = get_object_or_404(MailInbound.objects.select_related('enrollment__account'), pk=pk)
    if request.method == 'POST':
        try:
            with transaction.atomic():
                event = MailInbound.objects.select_for_update().get(pk=pk)
                if request.POST.get('action') == 'resolve':
                    event.needs_review = False; event.save(update_fields=['needs_review'])
                    audit(event.enrollment.account, request.user, 'mail_inbound_reviewed', inbound=event.pk)
                elif request.POST.get('action') == 'reply':
                    body = request.POST.get('body', '').strip()
                    if not body or len(body) > 12000:
                        raise ValidationError('Escribe una respuesta de hasta 12,000 caracteres.')
                    if suppressed(event.enrollment.account) or not event.human_reply or event.category in ('negative', 'optout'):
                        raise ValidationError('Este mensaje no admite respuesta desde el flujo comercial.')
                    if MailMessage.objects.filter(inbound=event).exists():
                        raise ValidationError('Ya existe una respuesta para este mensaje. Consulta su estado en la cola.')
                    pause_account(event.enrollment.account_id, 'Respuesta revisada por Gerencia', manual=True)
                    queue_message(event.enrollment, 'manual', 'Re: ' + event.subject.removeprefix('Re: '), body + SIGNATURE,
                                  inbound=event, thread_id=event.thread_id, reply_to_id=event.rfc_id)
                    event.needs_review = False; event.save(update_fields=['needs_review'])
                    audit(event.enrollment.account, request.user, 'mail_manual_queued', inbound=event.pk)
                else:
                    raise ValidationError('Acción no reconocida.')
        except ValidationError as exc:
            messages.error(request, '; '.join(exc.messages))
        return redirect('commercial:mail-incoming', pk=pk)
    return render(request, 'commercial/mail_incoming.html', {'event': event})
