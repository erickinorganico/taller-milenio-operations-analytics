"""Photo-to-quote reuse must preserve provenance and financial authorization boundaries."""
import time
from decimal import Decimal
from unittest.mock import patch

from django.contrib.auth.models import User, Group
from django.core.exceptions import ValidationError
from django.db import IntegrityError, connection, transaction
from django.test import Client, TestCase
from django.test.utils import CaptureQueriesContext
from django.utils import timezone

from workshop import models as m, photo_quotes as flow, services as s


class PhotoQuoteTests(TestCase):
    def setUp(self):
        self.manager = User.objects.create_superuser('photo-quote-manager')
        self.client.force_login(self.manager)
        customer = m.Customer.objects.create(name='Cliente ficticio')
        vehicle = m.Vehicle.objects.create(customer=customer,plate='PHOTO-Q1')
        self.order = m.WorkOrder.objects.create(vehicle=vehicle,number='PHOTO-Q1',status='inspection')
        self.document = m.DocumentCapture.objects.create(title='Hoja ficticia revisada',kind='service',
            photo='not-opened.jpg',fingerprint='photo-q1',status='applied',uploaded_by=self.manager,
            reviewed_by=self.manager,reviewed_at=timezone.now(),applied_by=self.manager,
            applied_at=timezone.now(),work_order=self.order)
        self.source = self.new_source()
        self.route = f'/orders/{self.order.pk}/quote-from-photo/'

    def new_source(self, **overrides):
        source = m.CapturedService.objects.create(work_order=self.order,
            fingerprint=str(m.CapturedService.objects.count()),description='Servicio leído de foto',
            **overrides)
        source.documents.add(self.document)
        return source

    def row(self, source=None, **overrides):
        return {'source_id':(source or self.source).pk,'description':'Servicio revisado para cotizar',
            'kind':'service','quantity':Decimal('2'),'unit_price':Decimal('123.45'),
            'unit_cost':None,'part_sku':'',**overrides}

    def plan(self):
        self.order.refresh_from_db()
        return flow.prepare(self.order,self.manager)

    def apply(self, plan=None, rows=None):
        return flow.apply(order=self.order,actor=self.manager,receipt=(plan or self.plan())['receipt'],
            rows=rows or [self.row()],tax_rate=Decimal('0.08'))

    def post_data(self, page, **overrides):
        row = self.row()
        return {'receipt':page.context['header_form']['receipt'].value(),'tax_rate':'0.08','checked':'on',
            'services-TOTAL_FORMS':'1','services-INITIAL_FORMS':'1','services-MIN_NUM_FORMS':'0',
            'services-MAX_NUM_FORMS':'50','services-0-selected':'on',
            **{'services-0-'+k:'' if v is None else str(v) for k,v in row.items()},**overrides}

    def test_read_only_preparation_keeps_unknowns_blank_and_requires_review(self):
        page = self.client.get(self.route)
        self.assertContains(page,'De la foto al presupuesto')
        form = page.context['rows'].forms[0]
        self.assertIsNone(form['quantity'].value())
        self.assertIsNone(form['unit_price'].value())
        self.assertIsNone(form['unit_cost'].value())
        self.assertEqual(form['kind'].value(),'')
        self.assertFalse(m.Quote.objects.exists())
        self.assertFalse(m.PhotoQuoteBatch.objects.exists())
        response = self.client.post(self.route,self.post_data(page,checked=''))
        self.assertEqual(response.status_code,400)
        self.assertFalse(m.QuoteLine.objects.exists())

    def test_batch_creates_only_draft_lines_with_photo_link_and_unknown_cost(self):
        quote = self.apply()
        line = quote.lines.get()
        self.assertEqual((quote.status,line.quantity,line.unit_price),('draft',Decimal('2'),Decimal('123.45')))
        self.assertIsNone(line.unit_cost)
        self.assertEqual(line.source_service,self.source)
        self.assertEqual(line.source_service.documents.get(),self.document)
        self.source.refresh_from_db(); self.order.refresh_from_db()
        self.assertIsNone(self.source.quantity)
        self.assertIsNone(self.source.unit_price)
        self.assertEqual(self.order.status,'inspection')
        self.assertFalse(m.Payment.objects.exists())
        self.assertFalse(m.Invoice.objects.exists())
        self.assertFalse(m.StockMovement.objects.exists())
        self.assertFalse(m.Reservation.objects.exists())
        self.assertEqual(m.AuditEvent.objects.filter(action='photo_sourced').get().after['document_ids'],[self.document.pk])
        self.assertContains(self.client.get(f'/orders/{self.order.pk}/'),'Desde foto:')
        self.assertContains(self.client.get(f'/orders/{self.order.pk}/'),'Servicio de foto agregado al presupuesto')

    def test_same_request_and_http_double_submit_do_not_duplicate(self):
        page = self.client.get(self.route)
        data = self.post_data(page)
        self.assertEqual(self.client.post(self.route,data).status_code,302)
        self.assertEqual(self.client.post(self.route,data).status_code,302)
        self.assertEqual(m.Quote.objects.count(),1)
        self.assertEqual(m.QuoteLine.objects.count(),1)
        self.assertEqual(m.PhotoQuoteBatch.objects.count(),1)
        self.assertEqual(m.AuditEvent.objects.filter(action='photo_sourced').count(),1)
        self.assertEqual(len(self.client.get(self.route).context['rows'].forms),0)

    def test_changed_replay_is_rejected_but_original_result_remains(self):
        plan = self.plan(); quote = self.apply(plan)
        self.assertEqual(self.apply(plan).pk,quote.pk)
        with self.assertRaisesRegex(ValidationError,'otros datos'):
            self.apply(plan,[self.row(unit_price=Decimal('500'))])
        self.assertEqual(quote.lines.get().unit_price,Decimal('123.45'))

    def test_existing_draft_preserves_manual_lines_and_source_can_be_used_in_new_version(self):
        draft = s.create_quote(actor=self.manager,work_order=self.order)
        manual = s.add_quote_line(actor=self.manager,quote=draft,description='Manual',kind='labor',quantity=1,unit_price=10)
        self.assertEqual(self.apply().pk,draft.pk)
        self.assertTrue(draft.lines.filter(pk=manual.pk).exists())
        self.assertEqual(draft.lines.count(),2)
        replacement = s.create_quote(actor=self.manager,work_order=self.order)
        self.assertEqual(self.apply().pk,replacement.pk)
        self.assertEqual(replacement.lines.get().source_service,self.source)
        self.assertEqual(draft.lines.count(),2)

    def test_database_constraint_blocks_a_second_line_for_same_source_and_quote(self):
        quote = self.apply()
        with self.assertRaises(IntegrityError), transaction.atomic():
            m.QuoteLine.objects.create(quote=quote,source_service=self.source,description='Duplicado',kind='service',quantity=1,unit_price=10)
        self.assertEqual(quote.lines.count(),1)

    def test_changed_source_document_or_order_rejects_stale_plan_without_writes(self):
        for target,fields in ((self.source,{'unit_price':Decimal('50')}),(self.document,{'version':2}),(self.order,{'version':2})):
            plan = self.plan()
            type(target).objects.filter(pk=target.pk).update(**fields)
            with self.assertRaises(ValidationError):
                self.apply(plan)
            self.assertFalse(m.Quote.objects.exists())
            self.assertFalse(m.PhotoQuoteBatch.objects.exists())

    def test_changed_manual_quote_line_rejects_stale_plan(self):
        quote = s.create_quote(actor=self.manager,work_order=self.order)
        plan = self.plan()
        s.add_quote_line(actor=self.manager,quote=quote,description='Otra edición',kind='labor',quantity=1,unit_price=10)
        with self.assertRaisesRegex(ValidationError,'cambió'):
            self.apply(plan)
        self.assertEqual(quote.lines.count(),1)

    def test_foreign_source_wrong_actor_bad_signature_and_expiration_are_rejected(self):
        plan = self.plan()
        another = m.WorkOrder.objects.create(vehicle=self.order.vehicle,number='OTHER-PHOTO',status='inspection')
        foreign = m.CapturedService.objects.create(work_order=another,fingerprint='other',description='Otro servicio')
        foreign.documents.add(self.document)
        with self.assertRaises(ValidationError):
            self.apply(plan,[self.row(foreign)])
        other_actor = User.objects.create_superuser('other-photo-owner')
        with self.assertRaisesRegex(ValidationError,'otra orden o persona'):
            flow.apply(order=self.order,actor=other_actor,receipt=plan['receipt'],rows=[self.row()],tax_rate=0)
        with self.assertRaises(ValidationError):
            self.apply({**plan,'receipt':plan['receipt']+'bad'})
        with patch('django.core.signing.time.time',return_value=time.time()+901), self.assertRaises(ValidationError):
            self.apply(plan)
        self.assertFalse(m.Quote.objects.exists())

    def test_missing_quantity_price_or_type_is_a_field_error_without_zero_defaults(self):
        page = self.client.get(self.route)
        for field in ('quantity','unit_price','kind'):
            response = self.client.post(self.route,self.post_data(page,**{'services-0-'+field:''}))
            self.assertEqual(response.status_code,400)
            self.assertIn(field,response.context['rows'].forms[0].errors)
        self.assertFalse(m.Quote.objects.exists())

    def test_no_selection_is_a_visible_form_error(self):
        page = self.client.get(self.route)
        response = self.client.post(self.route,self.post_data(page,**{'services-0-selected':''}))
        self.assertEqual(response.status_code,400)
        self.assertContains(response,'Selecciona al menos un servicio',status_code=400)
        self.assertFalse(m.Quote.objects.exists())

    def test_missing_part_rolls_back_entire_batch_and_valid_sku_does_not_reserve_stock(self):
        second = self.new_source()
        plan = self.plan()
        before_version = self.order.version
        with self.assertRaisesRegex(ValidationError,'SKU'):
            self.apply(plan,[self.row(),self.row(second,kind='part',part_sku='MISSING')])
        self.order.refresh_from_db()
        self.assertEqual(self.order.version,before_version)
        self.assertFalse(m.Quote.objects.exists())
        self.assertFalse(m.AuditEvent.objects.exists())
        part = m.Part.objects.create(sku='PART-1',name='Pieza de prueba',stock=5)
        quote = self.apply(rows=[self.row(kind='part',part_sku='part-1')])
        self.assertEqual(quote.lines.get().part,part)
        part.refresh_from_db()
        self.assertEqual((part.stock,part.reserved),(Decimal('5'),Decimal('0')))

    def test_sent_authorized_and_closed_orders_are_protected(self):
        quote = s.create_quote(actor=self.manager,work_order=self.order)
        for status in ('sent','approved'):
            m.Quote.objects.filter(pk=quote.pk).update(status=status)
            with self.assertRaises(ValidationError):
                self.plan()
        m.Quote.objects.filter(pk=quote.pk).update(status='draft')
        for status in ('intake','delivered','cancelled','in_progress'):
            m.WorkOrder.objects.filter(pk=self.order.pk).update(status=status)
            with self.assertRaises(ValidationError):
                self.plan()
        self.assertFalse(m.QuoteLine.objects.exists())

    def test_access_roles_and_csrf_are_enforced(self):
        for role in ('viewer','finance','technician'):
            user = User.objects.create_user('photo-'+role)
            user.groups.add(Group.objects.create(name=role))
            self.client.force_login(user)
            self.assertEqual(self.client.get(self.route).status_code,403)
            self.assertEqual(self.client.post(self.route,{}).status_code,403)
        advisor = User.objects.create_user('photo-advisor')
        advisor.groups.add(Group.objects.create(name='advisor'))
        self.client.force_login(advisor)
        self.assertEqual(self.client.get(self.route).status_code,200)
        browser = Client(enforce_csrf_checks=True); browser.force_login(advisor)
        self.assertEqual(browser.post(self.route,{}).status_code,403)
        self.client.logout()
        self.assertEqual(self.client.get(self.route).status_code,302)

    def test_source_rows_and_order_queries_do_not_grow_per_visible_row(self):
        with CaptureQueriesContext(connection) as small:
            self.assertEqual(self.client.get(self.route).status_code,200)
        for _ in range(24):
            self.new_source()
        with CaptureQueriesContext(connection) as large:
            self.assertEqual(self.client.get(self.route).status_code,200)
        self.assertEqual(len(small),len(large))
        self.assertLess(len(large),20)
        for _ in range(26):
            self.new_source()
        plan = self.plan()
        self.assertEqual(len(plan['sources']),50)
        self.assertTrue(plan['more'])
