"""Authenticated agent actions use the same business rules and unique mail queue."""
import hashlib
import json
import os
import uuid
from datetime import timedelta, date
from django.core.exceptions import ValidationError
from django.db import transaction
from django.http import JsonResponse
from django.utils import timezone
from django.views.decorators.csrf import csrf_exempt
from workshop.access import can
from .models import SalesAccount, Mailbox, MailInbound, MailMessage, BusinessContact
from .agent_models import AgentCredential, AgentRequest, ConversationClaim, AgentDraft
from .services import audit, locked, bump
from .rules import suppressed
from .mail_flow import pause_account, queue_message, enroll, SIGNATURE

SCOPES={'system.status':'read','accounts.search':'read','account.get':'read','conversations.list':'read',
        'conversation.claim':'prepare','message.prepare':'prepare','conversation.update':'prepare',
        'campaign.pause':'prepare','message.queue':'send','campaign.enroll':'send'}


def digest(value):
    return hashlib.sha256(value.encode()).hexdigest()


def account_data(account):
    return {'id':str(account.pk),'name':account.name,'version':account.version,'stage':account.stage,
            'next_action':account.next_action,'next_action_on':str(account.next_action_on or '')}


def read_action(action,data):
    if action=='system.status':
        from milenio_web.worker_health import status
        box=Mailbox.objects.filter(pk=1).first()
        return {**status(),'mail':{'connected':bool(box and box.connected),'enabled':bool(box and box.enabled),
            'last_sync':box.last_sync.isoformat() if box and box.last_sync else None,
            'queued':MailMessage.objects.filter(status='queued').count(),
            'unknown':MailMessage.objects.filter(status='unknown').count()}}
    if action=='accounts.search':
        offset=max(0,int(data.get('offset',0)))
        accounts=SalesAccount.objects.filter(name__icontains=str(data.get('query',''))[:100]).order_by('name','pk')[offset:offset+50]
        return {'accounts':[account_data(a) for a in accounts],'next_offset':offset+50}
    if action=='account.get':
        account=SalesAccount.objects.get(pk=data['account_id'])
        return {**account_data(account),'contacts':list(account.contacts.values('id','name','email','phone','published_business','deliverability')),
                'evidence':list(account.evidence.values('id','topic','excerpt','reviewed','source_url')),
                'recent_interactions':list(account.interactions.order_by('-occurred_at').values('kind','summary')[:50])}
    if action=='conversations.list':
        offset=max(0,int(data.get('offset',0)))
        events=MailInbound.objects.filter(needs_review=True).select_related('enrollment__account').order_by('pk')[offset:offset+50]
        return {'incoming':[{'id':e.pk,'account':account_data(e.enrollment.account),'sender':e.sender,
                  'subject':e.subject,'body':e.body,'category':e.category,'thread_id':e.thread_id} for e in events],
                'next_offset':offset+50,'content_is_untrusted':True}
    raise ValidationError('Acción desconocida.')


def mutate(action,data,credential):
    if action=='campaign.pause':
        Mailbox.objects.filter(pk=1).update(enabled=False)
        audit(None,credential.owner,'agent_mail_paused',credential=str(credential.pk),reason=str(data.get('reason',''))[:240])
        return {'status':'paused'}
    account=locked(data['account_id'],data['expected_version'])
    now=timezone.now()
    claim=ConversationClaim.objects.filter(account=account).first()
    if action=='conversation.claim':
        if claim and claim.expires_at>now and claim.credential_id!=credential.pk:
            raise ValidationError('Conversación reservada por otro agente.')
        ConversationClaim.objects.update_or_create(account=account,defaults={'credential':credential,'expires_at':now+timedelta(minutes=15)})
        bump(account)
        audit(account,credential.owner,'agent_claimed',credential=str(credential.pk))
        return {'status':'claimed','version':account.version,'expires_in_seconds':900}
    if not claim or claim.expires_at<=now or claim.credential_id!=credential.pk:
        raise ValidationError('Reserva la conversación antes de modificarla.')
    result={}
    if action=='conversation.update':
        account.next_action=str(data['next_action'])[:240]
        account.next_action_on=date.fromisoformat(data['next_action_on']) if data.get('next_action_on') else None
        if suppressed(account): raise ValidationError('Empresa en no contactar.')
        result={'status':'updated'}
    elif action=='message.prepare':
        event=MailInbound.objects.get(pk=data['inbound_id'],enrollment__account=account)
        body=str(data['body']).strip()
        if not body or len(body)>12000: raise ValidationError('Texto vacío o mayor de 12,000 caracteres.')
        draft=AgentDraft.objects.create(account=account,inbound=event,credential=credential,body=body,content_hash=digest(body))
        result={'status':'prepared','draft_id':str(draft.pk),'content_hash':draft.content_hash}
    elif action in ('message.queue','campaign.enroll'):
        reference=str(data.get('authorization_reference','')).strip()
        if not reference or len(reference)>500: raise ValidationError('Registra la autorización comercial vigente.')
        if action=='campaign.enroll':
            contact=BusinessContact.objects.get(pk=data['contact_id'],account=account)
            enrollment=enroll(contact,credential.owner)
            result={'status':'queued','enrollment_id':enrollment.pk}
        else:
            draft=AgentDraft.objects.get(pk=data['draft_id'],account=account,credential=credential)
            if draft.content_hash!=data.get('content_hash'): raise ValidationError('Contenido distinto del revisado.')
            event=draft.inbound
            if draft.message_id or MailMessage.objects.filter(inbound=event).exists():
                raise ValidationError('Este mensaje ya tiene una respuesta preparada para envío.')
            if suppressed(account) or not event.human_reply or event.category in ('negative','optout','bounce','automatic','unknown_sender'):
                raise ValidationError('La conversación no admite respuesta comercial.')
            pause_account(account.pk,'Respuesta preparada por agente autorizado',manual=True)
            message=queue_message(event.enrollment,'manual','Re: '+event.subject.removeprefix('Re: '),draft.body+SIGNATURE,
                                  inbound=event,thread_id=event.thread_id,reply_to_id=event.rfc_id)
            draft.message=message
            draft.save(update_fields=['message'])
            event.needs_review=False
            event.save(update_fields=['needs_review'])
            result={'status':'queued','message_id':str(message.pk)}
        audit(account,credential.owner,'agent_send_authorized',credential=str(credential.pk),reference=reference,**result)
    else: raise ValidationError('Acción desconocida.')
    bump(account)
    audit(account,credential.owner,'agent_action',credential=str(credential.pk),action_name=action,**result)
    return {**result,'version':account.version}


@csrf_exempt
def endpoint(request):
    # No session-cookie auth: every request must possess an individually revocable token.
    if request.method!='POST': return JsonResponse({'error':'POST required'},status=405)
    if len(request.body)>65536: return JsonResponse({'error':'payload_too_large'},status=413)
    token=request.headers.get('Authorization','').removeprefix('Bearer ')
    credential=AgentCredential.objects.filter(token_hash=digest(token),revoked=False,expires_at__gt=timezone.now()).select_related('owner').first()
    if not credential or not credential.owner.is_active or not can(credential.owner,'manage'):
        return JsonResponse({'error':'unauthorized'},status=401)
    try:
        data=json.loads(request.body)
        if not isinstance(data,dict): raise ValueError()
        expected=os.environ.get('MILENIO_INSTANCE_ID','')
        if not expected or data.get('instance_id')!=expected: return JsonResponse({'error':'wrong_instance'},status=409)
        action=data['action']
        if SCOPES.get(action) not in credential.scopes: return JsonResponse({'error':'forbidden'},status=403)
        if SCOPES[action]=='read': return JsonResponse(read_action(action,data))
        request_id=uuid.UUID(data['request_id'])
        payload_hash=digest(json.dumps(data,sort_keys=True,separators=(',',':')))
        with transaction.atomic():
            previous=AgentRequest.objects.filter(credential=credential,request_id=request_id).first()
            if previous:
                if previous.payload_hash!=payload_hash: return JsonResponse({'error':'request_id_conflict'},status=409)
                return JsonResponse(previous.result)
            result=mutate(action,data,credential)
            AgentRequest.objects.create(credential=credential,request_id=request_id,payload_hash=payload_hash,result=result)
            return JsonResponse(result)
    except (ValueError,KeyError,TypeError): return JsonResponse({'error':'invalid_payload'},status=400)
    except ValidationError as error: return JsonResponse({'error':'conflict','detail':error.messages},status=409)
    except (SalesAccount.DoesNotExist,MailInbound.DoesNotExist,AgentDraft.DoesNotExist,BusinessContact.DoesNotExist):
        return JsonResponse({'error':'not_found'},status=404)
