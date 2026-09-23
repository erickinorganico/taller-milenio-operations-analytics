from datetime import timedelta
from decimal import Decimal

from django.contrib.auth.models import Group, User
from django.test import Client, TestCase
from django.utils import timezone

from workshop import analytics, automation, models as m


class AnalyticsWebTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.manager = User.objects.create_user('ana_manager', password='test-only')
        cls.manager.groups.add(Group.objects.get_or_create(name='manager')[0])
        cls.viewer = User.objects.create_user('ana_viewer', password='test-only')
        cls.viewer.groups.add(Group.objects.get_or_create(name='viewer')[0])
        cls.tech = User.objects.create_user('ana_tech', password='test-only')
        cls.tech.groups.add(Group.objects.get_or_create(name='technician')[0])
        User.objects.create_superuser('ana_admin', password='test-only')
        customer = m.Customer.objects.create(name='Synthetic analytics customer')
        vehicle = m.Vehicle.objects.create(customer=customer, plate='ANA-TEST')
        order = m.WorkOrder.objects.create(vehicle=vehicle, number='ANA-1', complaint='Example', status='approved')
        quote = m.Quote.objects.create(work_order=order, version=1, status='approved', authorized_at=timezone.now())
        m.QuoteLine.objects.create(quote=quote, kind='service', description='=HYPERLINK("bad") <script>alert(1)</script>', quantity=1, unit_price=200)
        cls.cut = analytics.refresh_analytics(cls.manager)
        automation.initialize_defaults()

    def test_manager_landing_is_dashboard_and_daily_operation_remains(self):
        self.client.force_login(self.manager)
        response = self.client.get('/')
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Vista general')
        self.assertContains(response, 'Refacciones utilizadas')
        self.assertContains(response, 'Servicios más solicitados')
        self.assertContains(self.client.get('/today/'), 'Hoy en el taller')

    def test_technician_keeps_operation_and_cannot_access_analytics(self):
        self.client.force_login(self.tech)
        self.assertContains(self.client.get('/'), 'Hoy en el taller')
        for path in ['/analytics/', '/analytics/data/service_lines/', '/automations/']:
            self.assertEqual(self.client.get(path).status_code, 403, path)

    def test_viewer_can_read_but_cannot_queue_or_configure(self):
        self.client.force_login(self.viewer)
        self.assertEqual(self.client.get('/analytics/').status_code, 200)
        self.assertEqual(self.client.post('/automations/enqueue/').status_code, 403)
        self.assertEqual(self.client.post('/automations/configure/', {'interval_minutes': 5}).status_code, 403)
        self.assertEqual(m.AutomationJob.objects.count(), 0)

    def test_filters_reject_invalid_ranges_and_unknown_snapshots(self):
        self.client.force_login(self.manager)
        for params in [{'start':'invalid'}, {'start':'2026-04-20','end':'2026-04-01'}, {'segment':'sql'}]:
            self.assertEqual(self.client.get('/analytics/', params).status_code, 400)
        self.assertEqual(self.client.get('/analytics/', {'snapshot':'x'}).status_code, 404)
        self.assertEqual(self.client.get('/analytics/', {'snapshot':'99999'}).status_code, 404)
        self.assertEqual(self.client.get('/analytics/data/unknown/').status_code, 404)
        response = self.client.get('/analytics/', {'start':'2026-04-20', 'end':'2026-04-01', 'segment':'fleet', 'snapshot':self.cut.pk})
        self.assertEqual(response.context['d']['filters']['segment'], 'fleet')
        self.assertContains(response, 'value="2026-04-20"', status_code=400)
        self.assertContains(response, 'Revisa Desde y Hasta', status_code=400)
        self.assertContains(response, 'Filtros del dashboard', status_code=400)

    def test_six_marts_are_browsable_and_csv_is_formula_safe(self):
        self.client.force_login(self.manager)
        for mart in analytics.MARTS:
            response = self.client.get(f'/analytics/data/{mart}/', {'snapshot':self.cut.pk})
            self.assertEqual(response.status_code, 200, mart)
        html = self.client.get('/analytics/data/service_lines/').content.decode()
        self.assertNotIn('<script>alert(1)</script>', html)
        csv = self.client.get('/analytics/data/service_lines/', {'export':'csv'}).content.decode('utf-8-sig')
        self.assertIn("'=HYPERLINK", csv)
        self.assertIn('source_fingerprint', csv)
        self.assertIn(self.cut.source_fingerprint, csv)

    def test_queue_post_is_nonblocking_and_requires_csrf(self):
        self.client.force_login(self.manager)
        response = self.client.post('/automations/enqueue/', {'mode':'rules'})
        self.assertRedirects(response, '/automations/')
        job = m.AutomationJob.objects.get()
        self.assertEqual(job.status, 'pending')
        self.assertEqual(m.AgentRun.objects.count(), 0)
        csrf = Client(enforce_csrf_checks=True)
        csrf.force_login(self.manager)
        self.assertEqual(csrf.post('/automations/enqueue/', {'mode':'rules'}).status_code, 403)

    def test_empty_installation_has_no_get_mutations(self):
        m.AnalyticsRow.objects.all().delete()
        m.AnalyticsSnapshot.objects.all().delete()
        self.client.force_login(self.manager)
        self.assertContains(self.client.get('/analytics/'), 'Preparando el primer corte')
        self.assertEqual(m.AnalyticsSnapshot.objects.count(), 0)
        self.assertEqual(m.AutomationJob.objects.count(), 0)

    def test_all_dashboard_roles_see_coverage_and_cut_drift_is_visible(self):
        advisor = User.objects.create_user('ana_advisor', password='test-only')
        advisor.groups.add(Group.objects.get_or_create(name='advisor')[0])
        self.client.force_login(advisor)
        response = self.client.get('/analytics/')
        self.assertContains(response, 'órdenes con eventos suficientes')
        self.assertContains(response, 'Entregadas sin evento comprobable')
        self.assertNotContains(response, 'Exportar análisis JSON')
        self.assertEqual(self.client.get('/analytics/', {'export':'json'}).status_code, 403)
        job = automation.enqueue_manual(advisor)
        job.result = {'evidence_context': {'audit_cursor_advanced_after_snapshot': True,
                     'snapshot_audit_cursor': 3, 'post_agent_audit_cursor': 4}}
        job.save(update_fields=['result'])
        self.assertContains(self.client.get('/automations/'), 'Hubo cambios después del corte')

    def test_queued_cycle_links_snapshot_runs_proposals_and_human_followup(self):
        order = m.WorkOrder.objects.first()
        order.promised_at = timezone.now()-timedelta(days=1)
        order.save()
        automation.set_policy(self.manager, automatic_enabled=False)
        job = automation.enqueue_manual(self.manager)
        result = automation.run_once(worker_id='web-integration-test')
        job.refresh_from_db()
        self.assertEqual(job.status, 'completed', result)
        self.assertTrue(job.snapshot_id)
        self.assertEqual(len(job.agent_run_ids), 3)
        proposal = m.Proposal.objects.filter(run_id__in=job.agent_run_ids, entity_type='WorkOrder', entity_id=str(order.pk)).first()
        self.assertIsNotNone(proposal)
        self.client.force_login(self.manager)
        self.assertEqual(self.client.post(f'/proposals/{proposal.pk}/review/', {'decision':'accept'}).status_code, 302)
        self.assertEqual(m.ActionTask.objects.filter(proposal=proposal).count(), 1)
        self.assertContains(self.client.get('/automations/'), f'Corte #{job.snapshot_id}')

    def test_chart_and_quick_ranges_use_selected_snapshot_and_segment(self):
        from urllib.parse import urlparse, parse_qs
        self.client.force_login(self.manager)
        response = self.client.get('/analytics/', {'snapshot': self.cut.pk, 'segment': 'individual'})
        self.assertEqual(response.status_code, 200)
        context = response.context
        self.assertFalse(context['historical'])
        points = context['p']['chart']['points']
        self.assertEqual(sum(Decimal(p['invoiced_mxn']) for p in points), Decimal(context['d']['kpis']['invoiced']['value']))
        anchor = timezone.localdate(self.cut.recorded_at)
        for quick in context['quick_ranges']:
            query = parse_qs(urlparse(quick['url']).query)
            self.assertEqual(query['snapshot'], [str(self.cut.pk)])
            self.assertEqual(query['segment'], ['individual'])
            self.assertEqual(query['end'], [anchor.isoformat()])
            self.assertEqual(self.client.get('/analytics/' + quick['url']).status_code, 200)

    def test_dashboard_assets_are_served_with_strict_policy(self):
        self.client.force_login(self.manager)
        response = self.client.get('/analytics/')
        self.assertNotIn("'unsafe-inline'", response.headers.get('Content-Security-Policy', ''))
        for asset in ['shell.css', 'shell.js', 'analytics.js']:
            self.assertEqual(self.client.get('/static/workshop/' + asset).status_code, 200)
