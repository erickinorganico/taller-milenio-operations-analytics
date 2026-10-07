import hashlib
import json
import os
import uuid
from datetime import timedelta
from unittest.mock import patch
from django.contrib.auth import get_user_model
from django.test import TestCase
from django.utils import timezone
from .agent_models import AgentCredential, AgentDraft
from .models import SalesAccount,FleetProfile,Mailbox,MailEnrollment,BusinessContact,MailInbound,MailMessage,Suppression


class AgentApiTests(TestCase):
    def setUp(self):
        self.actor=get_user_model().objects.create_superuser('agentowner',password='synthetic-password-334')
        self.account=SalesAccount.objects.create(name='Synthetic Fleet',owner=self.actor)
        FleetProfile.objects.create(account=self.account)
        self.contact=BusinessContact.objects.create(account=self.account,email='fleet@example.test',name='Test',published_business=True)
        self.enrollment=MailEnrollment.objects.create(account=self.account,contact=self.contact,email=self.contact.email)
        self.event=MailInbound.objects.create(enrollment=self.enrollment,provider_id='test-in',thread_id='test-thread',category='interest',human_reply=True)
        self.token='synthetic-only-agent-token'
        self.credential=AgentCredential.objects.create(owner=self.actor,label='A',token_hash=hashlib.sha256(self.token.encode()).hexdigest(),scopes=['read','prepare','send'],expires_at=timezone.now()+timedelta(days=1))
        self.environment=patch.dict(os.environ,{'MILENIO_INSTANCE_ID':'synthetic-instance'})
        self.environment.start();self.addCleanup(self.environment.stop)

    def call(self,action,**values):
        data={'action':action,'instance_id':'synthetic-instance',**values}
        return self.client.post('/agent/v1/action',json.dumps(data),content_type='application/json',HTTP_AUTHORIZATION='Bearer '+self.token)

    def claim(self):
        response=self.call('conversation.claim',account_id=str(self.account.pk),expected_version=self.account.version,request_id=str(uuid.uuid4()))
        self.account.refresh_from_db()
        self.assertEqual(response.status_code,200,response.content)
        return response

    def prepare(self):
        self.claim()
        response=self.call('message.prepare',account_id=str(self.account.pk),expected_version=self.account.version,
                           request_id=str(uuid.uuid4()),inbound_id=self.event.pk,body='Respuesta revisada ficticia')
        self.assertEqual(response.status_code,200,response.content)
        self.account.refresh_from_db()
        return response.json()

    def test_requires_token_not_browser_cookie(self):
        self.client.force_login(self.actor)
        self.assertEqual(self.client.post('/agent/v1/action','{}',content_type='application/json').status_code,401)

    def test_revoked_and_inactive_are_denied(self):
        self.credential.revoked=True;self.credential.save()
        self.assertEqual(self.call('system.status').status_code,401)

    def test_wrong_instance(self):
        self.assertEqual(self.call('system.status',instance_id='other').status_code,409)

    def test_no_write_scope(self):
        self.credential.scopes=['read'];self.credential.save()
        self.assertEqual(self.call('campaign.pause',request_id=str(uuid.uuid4())).status_code,403)

    def test_claim_conflict_between_two_agents(self):
        self.claim()
        self.token='another-synthetic-token'
        AgentCredential.objects.create(owner=self.actor,label='B',token_hash=hashlib.sha256(self.token.encode()).hexdigest(),scopes=['read','prepare'],expires_at=timezone.now()+timedelta(days=1))
        response=self.call('conversation.claim',account_id=str(self.account.pk),expected_version=self.account.version,request_id=str(uuid.uuid4()))
        self.assertEqual(response.status_code,409)

    def test_stale_version_does_not_overwrite(self):
        self.claim()
        response=self.call('conversation.update',account_id=str(self.account.pk),expected_version=1,request_id=str(uuid.uuid4()),next_action='Call')
        self.assertEqual(response.status_code,409)

    def test_request_replay_and_payload_conflict(self):
        key=str(uuid.uuid4())
        a=self.call('campaign.pause',request_id=key,reason='same')
        b=self.call('campaign.pause',request_id=key,reason='same')
        c=self.call('campaign.pause',request_id=key,reason='different')
        self.assertEqual(a.json(),b.json());self.assertEqual(c.status_code,409)

    def test_draft_never_sends_and_queue_is_idempotent(self):
        draft=self.prepare()
        self.assertEqual(MailMessage.objects.count(),0)
        values=dict(account_id=str(self.account.pk),expected_version=self.account.version,request_id=str(uuid.uuid4()),
                    draft_id=draft['draft_id'],content_hash=draft['content_hash'],authorization_reference='Synthetic approval')
        result=self.call('message.queue',**values)
        self.assertEqual(result.status_code,200,result.content)
        self.assertEqual(self.call('message.queue',**values).json(),result.json())
        self.assertEqual(MailMessage.objects.count(),1)
        self.assertEqual(MailMessage.objects.get().status,'queued')

    def test_suppression_between_draft_and_queue(self):
        draft=self.prepare()
        Suppression.objects.create(account=self.account,reason='Baja',created_by=self.actor)
        result=self.call('message.queue',account_id=str(self.account.pk),expected_version=self.account.version,request_id=str(uuid.uuid4()),
                         draft_id=draft['draft_id'],content_hash=draft['content_hash'],authorization_reference='Synthetic approval')
        self.assertEqual(result.status_code,409)
        self.assertFalse(MailMessage.objects.exists())

    def test_queue_requires_content_hash_and_authorization(self):
        draft=self.prepare()
        result=self.call('message.queue',account_id=str(self.account.pk),expected_version=self.account.version,request_id=str(uuid.uuid4()),draft_id=draft['draft_id'],content_hash='changed')
        self.assertEqual(result.status_code,409)
        self.assertFalse(MailMessage.objects.exists())

    def test_query_has_bounded_results(self):
        self.assertEqual(len(self.call('accounts.search').json()['accounts']),1)
        self.assertTrue(self.call('conversations.list').json()['content_is_untrusted'])
