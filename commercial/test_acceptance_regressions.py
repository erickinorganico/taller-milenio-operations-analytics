"""Regresiones de los contratos locales: S1 104/109/110/116/122/130."""
import csv
import io
from datetime import timedelta
from decimal import Decimal
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.test import TestCase, TransactionTestCase
from django.utils import timezone
from . import services as s
from .models import AuditEvent, Evidence, SalesAccount, SalesOpportunity
from workshop.models import Customer, Vehicle, WorkOrder


class AcceptanceRegressions(TestCase):
    def setUp(self):
        self.actor = get_user_model().objects.create_superuser('synthetic-regression', password='synthetic-only')
        self.account = s.create_account({'name':'Empresa ficticia','website':'https://ficticia.example','is_demo':True,'next_action':'Confirmar siguiente paso','next_action_on':timezone.localdate()}, self.actor)

    def current(self):
        return SalesAccount.objects.select_related('fleet').get(pk=self.account.pk)

    def evidence(self, topic, reviewed=True):
        a=self.current()
        return s.add_record(a.pk,a.version,'evidence',{'topic':topic,'source_note':'Confirmación ficticia: referencia verificable','excerpt':'Hecho de prueba; no describe operación real','reviewed':reviewed},self.actor)

    def ready(self):
        self.evidence('identity')
        vehicle=self.evidence('vehicles')
        need=self.evidence('need')
        a=self.current()
        s.update_account(a.pk,a.version,{'identity_confirmed':True},self.actor)
        a=self.current()
        s.add_record(a.pk,a.version,'contact',{'name':'Área de prueba','email':'area@ficticia.example','source_note':'Fixture','published_business':True},self.actor)
        a=self.current()
        s.update_fleet(a.pk,a.version,{'fuel':'gasoline','vehicle_type':'light','total_units':3,'compatible_units':3,'vehicle_evidence':vehicle,'need_confirmed':True,'need_evidence':need},self.actor)

    def opportunity(self):
        a=self.current()
        return s.add_record(a.pk,a.version,'opportunity',{'title':'Necesidad ficticia','service':'mechanics'},self.actor)

    def proposal(self, opportunity):
        a=self.current()
        return s.create_proposal(a.pk,a.version,{'opportunity':opportunity,'scope':'Alcance sintético','terms':'Condiciones sintéticas','amount':Decimal('100'),'valid_until':timezone.localdate()+timedelta(days=1)},self.actor)

    def accept(self,p,reference='Aceptación ficticia de esta revisión'):
        a=self.current()
        return s.accept_proposal(a.pk,a.version,p.pk,reference,self.actor)

    def accepted(self):
        self.ready(); op=self.opportunity(); proposal=self.proposal(op); self.accept(proposal)
        return op,proposal

    def handoff(self):
        a=self.current()
        return s.handoff(a.pk,a.version,self.actor)

    def order(self,customer,number='SYNTH-1'):
        v=Vehicle.objects.create(customer=customer,make='Ficticia',model='Prueba')
        return WorkOrder.objects.create(vehicle=v,number=number,complaint='Fixture',status='intake')

    def link(self,op,order):
        a=self.current()
        s.link_service(a.pk,a.version,op,order,None,self.actor)

    def csv(self,rows):
        out=io.StringIO(); w=csv.writer(out);w.writerow(s.CSV_BRANCH_FIELDS);w.writerows(rows)
        return out.getvalue().encode()

    def test_A10_shared_domain_and_same_name_allow_distinct_branches(self):
        b=s.create_account({'name':self.account.name,'branch':'Otay','website':self.account.website},self.actor)
        self.assertNotEqual(b.pk,self.account.pk)
        self.assertEqual(b.domain,self.account.domain)
        self.assertIn('Otay',str(b))

    def test_A10_same_identity_requires_review_instead_of_duplicate(self):
        with self.assertRaises(ValidationError):
            s.create_account({'name':self.account.name,'website':self.account.website},self.actor)

    def test_A10_csv_keeps_shared_domain_branches_and_replays(self):
        raw=self.csv([['','Grupo ficticio','https://grupo.example','Tijuana','','manual','','','Centro'],['','Grupo ficticio','https://grupo.example','Tijuana','','manual','','','Otay']])
        self.assertEqual(s.import_candidates(raw,self.actor)['created'],2)
        self.assertTrue(s.import_candidates(raw,self.actor)['repeated'])
        self.assertEqual(SalesAccount.objects.filter(domain='grupo.example').count(),2)

    def test_A10_ambiguous_csv_preserves_review_receipt(self):
        raw=self.csv([['',self.account.name,self.account.website,'Tijuana','','manual','','Otra fuente','']])
        result=s.import_candidates(raw,self.actor)
        self.assertEqual(result['created'],0)
        self.assertEqual(len(result['review_rows']),1)
        self.assertEqual(result['review_rows'][0]['candidate']['notes'],'Otra fuente')

    def test_A17_opportunity_without_need_is_rejected(self):
        with self.assertRaises(ValidationError):self.opportunity()

    def test_A17_need_checkbox_without_evidence_is_rejected(self):
        fleet=self.current().fleet;fleet.need_confirmed=True;fleet.save()
        with self.assertRaises(ValidationError):self.opportunity()

    def test_A17_need_without_next_step_date_is_rejected(self):
        self.ready();a=self.current()
        s.update_account(a.pk,a.version,{'next_action_on':None},self.actor)
        with self.assertRaises(ValidationError):self.opportunity()

    def test_A17_valid_need_and_agreed_step_are_audited(self):
        self.ready();op=self.opportunity()
        event=AuditEvent.objects.filter(action='opportunity_added').latest('pk')
        self.assertIsNone(op.amount)
        self.assertEqual(event.details['need_evidence'],self.current().fleet.need_evidence_id)
        self.assertEqual(event.details['agreed_next_step'],'Confirmar siguiente paso')
        self.assertEqual(event.details['owner'],self.actor.pk)

    def test_A12_acceptance_is_won_without_order_or_payment(self):
        op,p=self.accepted();op.refresh_from_db()
        self.assertEqual(op.status,'won')
        self.assertIsNone(op.work_order_id)
        self.assertEqual(Customer.objects.count(),0)

    def test_A12_empty_acceptance_reference_is_rejected(self):
        self.ready();op=self.opportunity();p=self.proposal(op)
        with self.assertRaises(ValidationError):self.accept(p,' ')
        op.refresh_from_db();self.assertEqual(op.status,'pending_acceptance')

    def test_A24_new_revision_is_pending_and_keeps_old_acceptance(self):
        op,old=self.accepted();new=self.proposal(op);op.refresh_from_db();old.refresh_from_db()
        self.assertEqual(op.status,'pending_acceptance')
        self.assertIsNotNone(old.accepted_at)
        self.assertIsNone(new.accepted_at)
        with self.assertRaises(ValidationError):self.handoff()
        self.assertEqual(Customer.objects.count(),0)

    def test_A24_old_accepted_revision_cannot_be_reaccepted_as_current(self):
        op,old=self.accepted();self.proposal(op)
        with self.assertRaises(ValidationError):self.accept(old)

    def test_A24_unaccepted_revision_blocks_new_service_link(self):
        op,p=self.accepted();customer=self.handoff();order=self.order(customer);self.proposal(op)
        with self.assertRaises(ValidationError):self.link(op,order)
        op.refresh_from_db();self.assertIsNone(op.work_order_id)

    def test_A24_accepted_revision_records_exact_service_source(self):
        op,old=self.accepted();new=self.proposal(op);self.accept(new)
        customer=self.handoff();order=self.order(customer);self.link(op,order);op.refresh_from_db()
        self.assertEqual(op.service_proposal_id,new.pk)
        event=AuditEvent.objects.filter(action='service_linked').latest('pk')
        self.assertEqual(event.details['revision'],2)
        self.assertEqual(event.details['proposal'],new.pk)
        self.assertEqual(order.status,'intake')

    def test_A24_new_revision_does_not_rewrite_prior_service_source(self):
        op,old=self.accepted();customer=self.handoff();order=self.order(customer);self.link(op,order)
        self.proposal(op);op.refresh_from_db()
        self.assertEqual(op.service_proposal_id,old.pk)
        self.assertEqual(op.work_order_id,order.pk)
        self.assertEqual(op.status,'pending_acceptance')

    def test_A26_first_intake_order_leaves_recurrence_pending(self):
        op,p=self.accepted();customer=self.handoff();self.link(op,self.order(customer));a=self.current()
        with self.assertRaises(ValidationError):s.change_stage(a.pk,a.version,'active',self.actor)
        s.change_stage(a.pk,a.version,'recurrence_pending',self.actor)
        self.assertEqual(self.current().recurrence_basis,'pending')

    def test_A26_two_orders_do_not_infer_recurrence_without_confirmation(self):
        op,p=self.accepted();customer=self.handoff();self.order(customer,'SYNTH-A');self.order(customer,'SYNTH-B');a=self.current()
        with self.assertRaises(ValidationError):s.change_stage(a.pk,a.version,'active',self.actor)

    def test_A26_second_order_and_current_plan_remain_distinct(self):
        self.accepted()
        for basis in ('second_order','current_plan'):
            with self.subTest(basis=basis):
                evidence=self.evidence('recurrence');a=self.current()
                s.update_account(a.pk,a.version,{'recurrence_basis':basis,'recurrence_evidence':evidence},self.actor)
                a=self.current();s.change_stage(a.pk,a.version,'active',self.actor)
                self.assertEqual(self.current().recurrence_basis,basis)
                self.assertEqual(self.current().recurrence_evidence_id,evidence.pk)

    def test_A26_unreviewed_or_cross_account_recurrence_rejected(self):
        self.accepted();evidence=self.evidence('recurrence',False);a=self.current()
        with self.assertRaises(ValidationError):s.update_account(a.pk,a.version,{'recurrence_basis':'current_plan','recurrence_evidence':evidence},self.actor)
        other=s.create_account({'name':'Otra empresa'},self.actor)
        foreign=Evidence.objects.create(account=other,topic='recurrence',source_note='Fixture',excerpt='Fixture',reviewed=True,created_by=self.actor)
        with self.assertRaises(ValidationError):s.update_account(a.pk,a.version,{'recurrence_basis':'second_order','recurrence_evidence':foreign},self.actor)

    def test_A26_return_to_pending_removes_unsupported_active_stage(self):
        self.accepted();evidence=self.evidence('recurrence');a=self.current()
        s.update_account(a.pk,a.version,{'recurrence_basis':'current_plan','recurrence_evidence':evidence},self.actor)
        a=self.current();s.change_stage(a.pk,a.version,'active',self.actor)
        a=self.current();s.update_account(a.pk,a.version,{'recurrence_basis':'pending','recurrence_evidence':None},self.actor)
        self.assertEqual(self.current().stage,'recurrence_pending')

    def test_A26_new_account_cannot_claim_confirmed_recurrence(self):
        with self.assertRaises(ValidationError):
            s.create_account({'name':'Otra cuenta ficticia','recurrence_basis':'current_plan'},self.actor)

    def test_origin_contact_correction_survives_rebase(self):
        self.ready();a=self.current();contact=a.contacts.get()
        updated=s.add_record(a.pk,a.version,'contact',{'existing_contact':contact,'name':'Área corregida','email':contact.email,'source_note':'Corrección ficticia','published_business':True},self.actor)
        self.assertEqual(updated.pk,contact.pk)
        self.assertEqual(a.contacts.count(),1)
        self.assertEqual(updated.name,'Área corregida')

    def test_origin_current_compatibility_guard_survives_rebase(self):
        op,p=self.accepted();customer=self.handoff();order=self.order(customer);a=self.current()
        s.update_fleet(a.pk,a.version,{'fuel':'diesel','compatible_units':0},self.actor)
        with self.assertRaises(ValidationError):self.link(op,order)


class ExistingDataMigrationTests(TransactionTestCase):
    def test_existing_acceptances_preserved_and_unsupported_labels_pending(self):
        from django.db import connection
        from django.db.migrations.executor import MigrationExecutor
        executor=MigrationExecutor(connection)
        previous=[('commercial','0001_initial')]
        current=[('commercial','0002_acceptance_branch_recurrence')]
        executor.migrate(previous)
        try:
            old=executor.loader.project_state(previous).apps
            User=old.get_model('auth','User')
            Account=old.get_model('commercial','SalesAccount')
            Opportunity=old.get_model('commercial','SalesOpportunity')
            Proposal=old.get_model('commercial','SalesProposal')
            actor=User.objects.create(username='migration-synthetic')
            account=Account.objects.create(name='Cuenta ficticia anterior',owner_id=actor.pk,stage='active')
            revised=Opportunity.objects.create(account_id=account.pk,title='Aceptación sustituida',service='mechanics',status='won')
            first=Proposal.objects.create(opportunity_id=revised.pk,revision=1,scope='Fixture',terms='Fixture',amount='100',valid_until=timezone.localdate(),accepted_at=timezone.now(),acceptance_reference='Referencia histórica',created_by_id=actor.pk)
            Proposal.objects.create(opportunity_id=revised.pk,revision=2,scope='Cambio',terms='Fixture',amount='200',valid_until=timezone.localdate(),created_by_id=actor.pk)
            accepted=Opportunity.objects.create(account_id=account.pk,title='Aceptada sin orden',service='mechanics',status='open')
            Proposal.objects.create(opportunity_id=accepted.pk,revision=1,scope='Fixture',terms='Fixture',amount='100',valid_until=timezone.localdate(),accepted_at=timezone.now(),acceptance_reference='Referencia vigente',created_by_id=actor.pk)
            lost=Opportunity.objects.create(account_id=account.pk,title='Perdida',service='mechanics',status='lost')
            executor=MigrationExecutor(connection);executor.migrate(current)
            from .models import SalesProposal
            self.assertEqual(SalesAccount.objects.get(pk=account.pk).stage,'recurrence_pending')
            self.assertEqual(SalesOpportunity.objects.get(pk=revised.pk).status,'pending_acceptance')
            self.assertEqual(SalesOpportunity.objects.get(pk=accepted.pk).status,'won')
            self.assertEqual(SalesOpportunity.objects.get(pk=lost.pk).status,'lost')
            self.assertEqual(SalesProposal.objects.get(pk=first.pk).acceptance_reference,'Referencia histórica')
            self.assertIsNone(SalesOpportunity.objects.get(pk=revised.pk).service_proposal_id)
        finally:
            MigrationExecutor(connection).migrate(current)
