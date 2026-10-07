import uuid
from django.conf import settings
from django.db import models
from django.utils import timezone


class AgentCredential(models.Model):
    id=models.UUIDField(primary_key=True,default=uuid.uuid4,editable=False)
    owner=models.ForeignKey(settings.AUTH_USER_MODEL,on_delete=models.PROTECT)
    label=models.CharField(max_length=100)
    token_hash=models.CharField(max_length=64,unique=True)
    scopes=models.JSONField(default=list)
    expires_at=models.DateTimeField()
    revoked=models.BooleanField(default=False)


class AgentRequest(models.Model):
    credential=models.ForeignKey(AgentCredential,on_delete=models.PROTECT)
    request_id=models.UUIDField()
    payload_hash=models.CharField(max_length=64)
    result=models.JSONField()
    created_at=models.DateTimeField(default=timezone.now)
    class Meta:
        constraints=[models.UniqueConstraint(fields=['credential','request_id'],name='agent_request_unique')]


class ConversationClaim(models.Model):
    account=models.OneToOneField('commercial.SalesAccount',primary_key=True,on_delete=models.PROTECT)
    credential=models.ForeignKey(AgentCredential,on_delete=models.PROTECT)
    expires_at=models.DateTimeField()


class AgentDraft(models.Model):
    id=models.UUIDField(primary_key=True,default=uuid.uuid4,editable=False)
    account=models.ForeignKey('commercial.SalesAccount',on_delete=models.PROTECT)
    inbound=models.ForeignKey('commercial.MailInbound',on_delete=models.PROTECT)
    credential=models.ForeignKey(AgentCredential,on_delete=models.PROTECT)
    body=models.TextField()
    content_hash=models.CharField(max_length=64)
    message=models.OneToOneField('commercial.MailMessage',null=True,on_delete=models.PROTECT)
    created_at=models.DateTimeField(default=timezone.now)
