from datetime import timedelta
from decimal import Decimal
import os
import json
from pathlib import Path
from types import SimpleNamespace
from unittest import mock

from django.contrib.auth.models import Group, User
from django.core.exceptions import PermissionDenied, ValidationError
from django.test import TestCase, override_settings
from django.utils import timezone

from workshop import intelligence
from workshop.models import (
    ActionTask, AuditEvent, Customer, FleetContract, Invoice, MaintenancePlan,
    Part, Payment, Proposal, Quote, QuoteLine, TimeEntry, TowService, Vehicle,
    WorkOrder,
)


class IntelligenceTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.manager = User.objects.create_user("manager", password="test-only")
        cls.manager.groups.add(Group.objects.create(name="manager"))
        cls.viewer = User.objects.create_user("viewer", password="test-only")
        cls.viewer.groups.add(Group.objects.create(name="viewer"))
        cls.customer = Customer.objects.create(name="Cliente de prueba")
        cls.vehicle = Vehicle.objects.create(customer=cls.customer, plate="TEST-01", make="Marca", model="Modelo")

    def order(self, *, status="in_progress", promised_at=None, number="WO-001"):
        return WorkOrder.objects.create(vehicle=self.vehicle, number=number, status=status,
                                        complaint="Revisión de prueba", promised_at=promised_at)

    def test_empty_populations_are_unknown_and_catalog_is_stable(self):
        dashboard = intelligence.build_dashboard()
        metrics = {item["metric_id"]: item for item in dashboard["metrics"]}
        self.assertEqual(len(intelligence.build_metric_catalog()), 18)
        for metric_id in ("OPS-WIP", "OPS-LATE", "FIN-INVOICED", "FIN-PAYMENTS", "FIN-OPEN-BALANCE",
                          "SALES-QUOTE-APPROVAL", "FIN-DIRECT-MARGIN", "DATA-LAST-EVENT", "INV-LOW-STOCK",
                          "INV-STOCK-VALUE-COST", "OPS-HOURS-LOGGED", "MAINT-OVERDUE-DATE",
                          "MAINT-OVERDUE-ODOMETER", "FLEET-EXPIRING-30D", "TOW-OPEN",
                          "TOW-MEDIAN-ARRIVAL-MIN", "TOW-MEDIAN-COMPLETE-MIN"):
            self.assertEqual(metrics[metric_id]["status"], "unknown", metric_id)
            self.assertIsNone(metrics[metric_id]["value"], metric_id)

    def test_metrics_separate_invoice_amount_from_payments_and_balance(self):
        order = self.order(status="delivered")
        invoice = Invoice.objects.create(work_order=order, number="ADM-1", subtotal=Decimal("100.00"),
            tax=Decimal("16.00"), total=Decimal("116.00"), due_at=timezone.now() + timedelta(days=1))
        Payment.objects.create(invoice=invoice, amount=Decimal("40.00"), method="cash", reference="R1",
            idempotency_key="test-payment-1", created_by=self.manager)
        metrics = {item["metric_id"]: item for item in intelligence.build_dashboard()["metrics"]}
        self.assertEqual(metrics["FIN-INVOICED"]["value"], "116.00")
        self.assertEqual(metrics["FIN-PAYMENTS"]["value"], "40.00")
        self.assertEqual(metrics["FIN-OPEN-BALANCE"]["value"], "76.00")
        self.assertEqual(metrics["FIN-OPEN-BALANCE"]["coverage"]["with_positive_balance"], 1)

    def test_cycle_requires_audited_delivery_transition(self):
        order = self.order(status="delivered")
        order.created_at = timezone.now() - timedelta(hours=8)
        order.save(update_fields=["created_at"])
        metric = next(item for item in intelligence.build_dashboard()["metrics"] if item["metric_id"] == "OPS-DELIVERY-CYCLE")
        self.assertEqual(metric["status"], "unknown")
        AuditEvent.objects.create(actor=self.manager, entity_type="WorkOrder", entity_id=str(order.pk),
            action="status_changed", before={"status": "ready"}, after={"status": "delivered"},
            created_at=timezone.now())
        metric = next(item for item in intelligence.build_dashboard()["metrics"] if item["metric_id"] == "OPS-DELIVERY-CYCLE")
        self.assertEqual(metric["status"], "measured")
        self.assertGreaterEqual(metric["value"], 0)
        earlier = next(item for item in intelligence.build_dashboard(as_of=timezone.now() - timedelta(days=1))["metrics"]
                       if item["metric_id"] == "OPS-DELIVERY-CYCLE")
        self.assertEqual(earlier["status"], "unknown")

    def test_quote_approval_uses_latest_decision_and_returns_percentage(self):
        first = self.order(number="WO-Q1")
        second = self.order(number="WO-Q2")
        Quote.objects.create(work_order=first, version=1, status="approved", authorized_at=timezone.now())
        Quote.objects.create(work_order=first, version=2, status="rejected")
        Quote.objects.create(work_order=second, version=1, status="rejected")
        metric = next(item for item in intelligence.build_dashboard()["metrics"]
                      if item["metric_id"] == "SALES-QUOTE-APPROVAL")
        self.assertEqual(metric["value"], 0.0)
        self.assertEqual(metric["numerator_value"], 0)
        self.assertEqual(metric["denominator_value"], 2)

    def test_margin_excludes_unknown_line_cost_and_reports_coverage(self):
        order = self.order(status="delivered")
        invoice = Invoice.objects.create(work_order=order, number="ADM-2", subtotal=Decimal("100.00"),
            tax=Decimal("0.00"), total=Decimal("100.00"), due_at=timezone.now())
        quote = Quote.objects.create(work_order=order, version=1, status="approved", authorized_at=timezone.now())
        QuoteLine.objects.create(quote=quote, description="Labor", kind="labor", quantity=Decimal("1"),
                                 unit_price=Decimal("100.00"), unit_cost=Decimal("30.00"))
        metric = next(item for item in intelligence.build_dashboard()["metrics"] if item["metric_id"] == "FIN-DIRECT-MARGIN")
        self.assertEqual(metric["value"], "70.00")
        self.assertEqual(metric["coverage"]["invoices_with_complete_quote_cost"], 1)
        QuoteLine.objects.create(quote=quote, description="Costo sin dato", kind="service", quantity=Decimal("1"),
                                 unit_price=Decimal("0.00"), unit_cost=None)
        metric = next(item for item in intelligence.build_dashboard()["metrics"] if item["metric_id"] == "FIN-DIRECT-MARGIN")
        self.assertEqual(metric["status"], "unknown")
        self.assertEqual(metric["coverage"]["excluded_cost_unknown_or_missing_quote"], 1)

    def test_rules_persist_role_runs_without_claiming_model_execution(self):
        self.order(status="waiting_parts")
        runs = intelligence.run_agents(self.manager)
        self.assertEqual({run.agent for run in runs}, {"operations", "collections", "data_quality"})
        self.assertTrue(all(run.status == "completed" and run.model_invoked is False for run in runs))
        proposal = Proposal.objects.get(run__agent="operations", kind="waiting_parts")
        self.assertEqual(proposal.evidence[0]["fields"]["status"], "waiting_parts")
        self.assertEqual(proposal.fingerprint, intelligence._hash(proposal.evidence))

    def test_reviewer_revalidation_stales_mutated_evidence_without_task(self):
        order = self.order(status="waiting_parts")
        run = intelligence.run_agents(self.manager, agent="operations")[0]
        proposal = Proposal.objects.get(run=run)
        WorkOrder.objects.filter(pk=order.pk).update(status="in_progress", version=2)
        result = intelligence.review_proposal(proposal.pk, self.manager, "accept")
        self.assertEqual(result.status, "stale")
        self.assertFalse(ActionTask.objects.filter(proposal=proposal).exists())

    def test_new_payment_invalidates_collection_proposal_even_when_old_rows_are_unchanged(self):
        order = self.order(status="delivered")
        invoice = Invoice.objects.create(work_order=order, number="ADM-COLLECT", subtotal=Decimal("100.00"),
            tax=Decimal("0.00"), total=Decimal("100.00"), due_at=timezone.now() - timedelta(days=2))
        run = intelligence.run_agents(self.manager, agent="collections")[0]
        proposal = Proposal.objects.get(run=run)
        self.assertTrue(any(reference["model"] == "PaymentSet" for reference in proposal.evidence))
        Payment.objects.create(invoice=invoice, amount=Decimal("100.00"), method="cash", reference="SETTLED",
            idempotency_key="test-collection-cleared", created_by=self.manager)
        result = intelligence.review_proposal(proposal.pk, self.manager, "accept")
        self.assertEqual(result.status, "stale")
        self.assertFalse(ActionTask.objects.filter(proposal=proposal).exists())

    def test_repeated_rules_run_does_not_duplicate_pending_or_active_task(self):
        self.order(status="waiting_parts")
        first_run = intelligence.run_agents(self.manager, agent="operations")[0]
        proposal = Proposal.objects.get(run=first_run, kind="waiting_parts")
        second_run = intelligence.run_agents(self.manager, agent="operations")[0]
        self.assertEqual(second_run.output["new_proposal_count"], 0)
        self.assertEqual(Proposal.objects.filter(run__agent="operations", kind="waiting_parts", status="pending").count(), 1)
        intelligence.review_proposal(proposal.pk, self.manager, "accept")
        third_run = intelligence.run_agents(self.manager, agent="operations")[0]
        self.assertEqual(third_run.output["new_proposal_count"], 0)
        self.assertEqual(ActionTask.objects.filter(proposal=proposal, status="open").count(), 1)

    def test_inventory_labor_maintenance_and_contract_metrics_use_known_coverage(self):
        order = self.order()
        Part.objects.create(sku="P-VALUED", name="Pieza con costo", stock=4, reserved=2,
                            reorder_point=2, cost=Decimal("5.00"))
        Part.objects.create(sku="P-UNKNOWN", name="Pieza sin costo", stock=1, reserved=0,
                            reorder_point=0, cost=Decimal("0.00"))
        TimeEntry.objects.create(work_order=order, technician=self.manager, minutes=90)
        plan_date = MaintenancePlan.objects.create(vehicle=self.vehicle, description="Servicio por fecha",
                                                   due_date=timezone.localdate() - timedelta(days=1))
        plan_km = MaintenancePlan.objects.create(vehicle=self.vehicle, description="Servicio por odómetro",
                                                 due_odometer=50000)
        fleet_customer = Customer.objects.create(name="Flotilla de prueba", kind="fleet")
        FleetContract.objects.create(customer=fleet_customer, name="Contrato próximo", start_date=timezone.localdate(),
                                     end_date=timezone.localdate() + timedelta(days=10), status="active")
        metrics = {item["metric_id"]: item for item in intelligence.build_dashboard()["metrics"]}
        self.assertEqual(metrics["INV-LOW-STOCK"]["value"], 1)
        self.assertEqual(metrics["INV-STOCK-VALUE-COST"]["value"], "20.00")
        self.assertFalse(metrics["INV-STOCK-VALUE-COST"]["coverage"]["complete_stock_valuation"])
        self.assertEqual(metrics["OPS-HOURS-LOGGED"]["value"], 1.5)
        self.assertEqual(metrics["MAINT-OVERDUE-DATE"]["value"], 1)
        self.assertEqual(metrics["MAINT-OVERDUE-ODOMETER"]["status"], "unknown")
        self.assertEqual(metrics["MAINT-OVERDUE-ODOMETER"]["coverage"]["missing_current_odometer"], 1)
        self.assertEqual(metrics["FLEET-EXPIRING-30D"]["value"], 1)
        findings = intelligence._rule_findings("data_quality", timezone.now())
        self.assertTrue(any(row["kind"] == "maintenance_missing_odometer" and row["entity_id"] == str(plan_km.pk) for row in findings))
        ops_findings = intelligence._rule_findings("operations", timezone.now())
        self.assertTrue(any(row["kind"] == "low_stock" and row["entity_type"] == "Part" for row in ops_findings))
        self.assertTrue(any(row["kind"] == "maintenance_overdue" and row["entity_id"] == str(plan_date.pk) for row in ops_findings))

    def test_tow_metrics_use_only_known_nonnegative_timestamps(self):
        now = timezone.now()
        TowService.objects.create(customer=self.customer, origin="A", destination="B", status="completed",
                                  requested_at=now - timedelta(hours=2), arrived_at=now - timedelta(minutes=90),
                                  completed_at=now - timedelta(minutes=30))
        TowService.objects.create(customer=self.customer, origin="C", destination="D", status="arrived",
                                  requested_at=now, arrived_at=now - timedelta(minutes=1))
        TowService.objects.create(customer=self.customer, origin="E", destination="F", status="requested",
                                  requested_at=now)
        metrics = {item["metric_id"]: item for item in intelligence.build_dashboard()["metrics"]}
        self.assertEqual(metrics["TOW-OPEN"]["value"], 2)
        self.assertEqual(metrics["TOW-MEDIAN-ARRIVAL-MIN"]["value"], 30.0)
        self.assertEqual(metrics["TOW-MEDIAN-ARRIVAL-MIN"]["coverage"]["invalid_negative_intervals"], 1)
        self.assertEqual(metrics["TOW-MEDIAN-COMPLETE-MIN"]["value"], 90.0)

    def test_review_requires_reviewer_role_and_acceptance_is_idempotent(self):
        self.order(status="waiting_parts")
        run = intelligence.run_agents(self.manager, agent="operations")[0]
        proposal = Proposal.objects.get(run=run)
        with self.assertRaises(PermissionDenied):
            intelligence.review_proposal(proposal.pk, self.viewer, "accept")
        accepted = intelligence.review_proposal(proposal.pk, self.manager, "accept")
        repeated = intelligence.review_proposal(proposal.pk, self.manager, "accept")
        self.assertEqual(accepted.status, "accepted")
        self.assertEqual(repeated.pk, accepted.pk)
        self.assertEqual(ActionTask.objects.filter(proposal=proposal).count(), 1)

    def test_completed_task_records_outcome_and_rule_recheck(self):
        order = self.order(status="waiting_parts")
        run = intelligence.run_agents(self.manager, agent="operations")[0]
        proposal = Proposal.objects.get(run=run)
        intelligence.review_proposal(proposal.pk, self.manager, "accept")
        task = ActionTask.objects.get(proposal=proposal)
        with self.assertRaises(ValidationError):
            intelligence.complete_action_task(task.pk, self.manager, " ")
        WorkOrder.objects.filter(pk=order.pk).update(status="in_progress")
        task = intelligence.complete_action_task(task.pk, self.manager, "Refacción recibida; trabajo reanudado.")
        event = AuditEvent.objects.get(entity_type="ActionTask", entity_id=str(task.pk), action="completed")
        self.assertEqual(task.status, "completed")
        self.assertEqual(event.after["followup_evaluation"]["status"], "not_detected")

    def test_assigned_technician_can_close_only_their_task(self):
        technician = User.objects.create_user("technician", password="test-only")
        technician_group, _ = Group.objects.get_or_create(name="technician")
        technician.groups.add(technician_group)
        other = User.objects.create_user("other-tech", password="test-only")
        other.groups.add(technician_group)
        self.order(status="waiting_parts")
        run = intelligence.run_agents(self.manager, agent="operations")[0]
        proposal = Proposal.objects.get(run=run)
        intelligence.review_proposal(proposal.pk, self.manager, "accept")
        task = ActionTask.objects.get(proposal=proposal)
        task.assigned_to = self.viewer
        task.save(update_fields=["assigned_to"])
        with self.assertRaises(PermissionDenied):
            intelligence.complete_action_task(task.pk, self.viewer, "Consulta no debe poder escribir")
        task.refresh_from_db()
        self.assertEqual(task.status, "open")
        self.assertEqual(task.outcome, "")
        task.assigned_to = technician
        task.save(update_fields=["assigned_to"])
        with self.assertRaises(PermissionDenied):
            intelligence.complete_action_task(task.pk, other, "Hecho por otra persona")
        completed = intelligence.complete_action_task(task.pk, technician, "Refacción recibida")
        self.assertEqual(completed.status, "completed")

    @override_settings(MILENIO_CODEX_ENABLED=True)
    def test_native_failure_is_visible_and_mock_never_counts_as_model(self):
        self.order(status="waiting_parts")
        with mock.patch.object(intelligence, "_resolve_codex_binary", return_value="codex-test"):
            failed = intelligence.run_native_agent(self.manager, "operations", native_runner=lambda **_: (_ for _ in ()).throw(TimeoutError("timeout")))
        self.assertEqual(failed.status, "failed")
        self.assertFalse(failed.model_invoked)
        finding = intelligence._rule_findings("operations", timezone.now())[0]
        native_call = {}
        def valid_mock(**kwargs):
            native_call.update(kwargs)
            return {"summary": "Revisión", "proposals": [{
                "kind": "waiting_parts", "title": "Revisar refacción", "body": "Verificar el estatus interno.",
                "entity_type": "WorkOrder", "entity_id": finding["entity_id"], "evidence_indices": [0],
            }]}
        with mock.patch.object(intelligence, "_resolve_codex_binary", return_value="codex-test"):
            completed = intelligence.run_native_agent(self.manager, "operations", base_findings=[finding], native_runner=valid_mock)
        self.assertEqual(completed.status, "completed", completed.error)
        self.assertFalse(completed.model_invoked)
        self.assertEqual(completed.proposals.count(), 1)
        command = native_call["command"]
        self.assertIn("--skip-git-repo-check", command)
        self.assertEqual(command[command.index("--sandbox") + 1], "read-only")
        self.assertEqual(command[command.index("-a") + 1], "never")
        self.assertIn("--ignore-user-config", command)

    @override_settings(MILENIO_CODEX_ENABLED=True)
    def test_adversarial_native_output_cannot_link_other_entity(self):
        self.order(status="waiting_parts", number="WO-SECURE")
        finding = intelligence._rule_findings("operations", timezone.now())[0]
        malformed = lambda **_: {"summary": "Revisión", "proposals": [{
            "kind": "waiting_parts", "title": "Propuesta", "body": "Texto.",
            "entity_type": "WorkOrder", "entity_id": "99999", "evidence_indices": [0],
        }]}
        with mock.patch.object(intelligence, "_resolve_codex_binary", return_value="codex-test"):
            run = intelligence.run_native_agent(self.manager, "operations", base_findings=[finding], native_runner=malformed)
        self.assertEqual(run.status, "failed")
        self.assertFalse(run.model_invoked)
        self.assertEqual(run.proposals.count(), 0)

    def test_native_configuration_blocks_shell_shims_and_paid_api_keys_are_removed(self):
        with mock.patch.dict(os.environ, {"MILENIO_CODEX_BIN": "codex.cmd", "OPENAI_API_KEY": "test-secret",
                                          "CODEX_API_KEY": "test-secret", "AZURE_OPENAI_API_KEY": "test-secret"}):
            with self.assertRaises(ValidationError):
                intelligence._resolve_codex_binary()
            native_env = intelligence._native_subprocess_env()
        self.assertNotIn("OPENAI_API_KEY", native_env)
        self.assertNotIn("CODEX_API_KEY", native_env)
        self.assertNotIn("AZURE_OPENAI_API_KEY", native_env)

    @override_settings(MILENIO_CODEX_ENABLED=True)
    def test_completed_cli_with_rejected_output_keeps_receipt_without_proposals(self):
        self.order(status="waiting_parts")
        finding = intelligence._rule_findings("operations", timezone.now())[0]
        def completed_invalid(command, prompt):
            output = Path(command[command.index("--output-last-message") + 1])
            output.write_text(json.dumps({"summary": "Salida rechazada", "proposals": [{
                "kind": "waiting_parts", "title": "Revisar", "body": "Consultar evidencia.",
                "entity_type": "WorkOrder", "entity_id": "", "evidence_indices": [0],
            }]}), encoding="utf-8")
            return SimpleNamespace(returncode=0, stdout='{"type":"turn.completed"}\n')
        with mock.patch.object(intelligence, "_resolve_codex_binary", return_value="codex-test"), \
             mock.patch.object(intelligence, "_run_native_cli", side_effect=completed_invalid):
            run = intelligence.run_native_agent(self.manager, "operations", base_findings=[finding])
        self.assertEqual(run.status, "failed")
        self.assertTrue(run.model_invoked)  # Fixture tests receipt handling, not actual inference.
        self.assertTrue(run.output["native_receipt"]["completion_observed"])
        self.assertFalse(run.output["output_accepted"])
        self.assertNotIn("proposals", run.output)
        self.assertEqual(run.proposals.count(), 0)
        self.assertIn("entity_id", run.error)

    def test_native_subprocess_uses_utf8_and_never_a_shell(self):
        result = object()
        with mock.patch.object(intelligence.subprocess, "run", return_value=result) as subprocess_run:
            returned = intelligence._run_native_cli(["codex-test", "exec"], "Prueba UTF-8: refacción")
        self.assertIs(returned, result)
        kwargs = subprocess_run.call_args.kwargs
        self.assertEqual(kwargs["encoding"], "utf-8")
        self.assertTrue(kwargs["text"])
        self.assertFalse(kwargs["shell"])
        self.assertEqual(kwargs["input"], "Prueba UTF-8: refacción")
