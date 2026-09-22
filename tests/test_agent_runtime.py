import hashlib
import json
import sqlite3
import tempfile
import unittest
from pathlib import Path

from milenio.agent_runtime import (
    _native_command,
    _readonly_connection,
    complete_agent_run,
    inspect_scoped_cases,
    list_available_agents,
    prepare_agent_run,
    query_metrics,
)
from milenio.fixtures import make_fixture
from milenio.warehouse import build_warehouse


def sha256(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def valid_native_result():
    return {
        "diagnosis": "The cited lead needs a human review.",
        "alternatives": ["Review its current context."],
        "manual_next_steps": ["A human reviewer verifies the record."],
        "drafts": [{"kind": "followup", "text": "Internal draft: review this lead.", "requires_human_review": True}],
        "missing_information": ["No live context is available."],
        "sensitivity": {"level": "medium", "reason": "The record can contain contact data."},
        "evidence": [{"entity_type": "leads", "entity_id": "L-001", "field": "status", "value": "new", "version": 1}],
        "workplan": ["Verify the current record."],
    }


def valid_native_plan():
    return {
        "evidence_requests": [{"entity_type": "leads", "entity_id": "L-001", "field": "status"}],
        "metric_ids": ["open_leads"],
    }


class AgentRuntimeTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary.name)
        self.warehouse = self.root / "warehouse.sqlite"
        build_warehouse(self.warehouse, make_fixture())

    def tearDown(self):
        self.temporary.cleanup()

    def test_nine_profiles_are_separately_configured(self):
        profiles = list_available_agents()
        self.assertEqual(9, len(profiles))
        self.assertEqual(9, len({item["id"] for item in profiles}))
        for item in profiles:
            self.assertEqual(["inspect_scoped_cases", "read_evidence", "query_metrics"], item["allowed_read_tools"])
            self.assertTrue(item["persona"] and item["objective"] and item["criteria"])

    def test_rules_run_is_complete_evidence_bound_and_does_not_mutate_source(self):
        before = sha256(self.warehouse)
        output = self.root / "rules-run"
        run = prepare_agent_run(self.warehouse, output, "operations_controller")
        self.assertEqual("completed", run["status"])
        self.assertEqual(before, sha256(self.warehouse))
        for name in ("input_packet.json", "prompt.md", "tool_trace.jsonl", "result.json", "run.json"):
            self.assertTrue((output / name).is_file(), name)
        result = json.loads((output / "result.json").read_text(encoding="utf-8"))
        self.assertFalse(result["model_invoked"])
        self.assertIn("no LLM invoked", result["mode_label"])
        self.assertEqual("status", result["result"]["evidence"][0]["field"])

    def test_read_connection_is_query_only(self):
        connection = _readonly_connection(self.warehouse)
        with self.assertRaises(sqlite3.OperationalError):
            connection.execute("UPDATE leads SET status='won' WHERE id='L-001'")
        connection.close()

    def test_native_fake_runner_is_a_test_interface_not_evidence_of_llm(self):
        output = self.root / "native-run"

        def fake_runner(**kwargs):
            self.assertIn("--ignore-user-config", kwargs["command"])
            self.assertIn("--model", kwargs["command"])
            response = valid_native_plan() if kwargs["stage"] == "plan" else valid_native_result()
            return {"response": response, "events": [{"provider_event_type": "completed", "model": "fake-test-model", "usage": {"output_tokens": 1}}]}

        run = prepare_agent_run(self.warehouse, output, "intake_admin", backend="native_codex", native_runner=fake_runner)
        self.assertEqual("completed", run["status"])
        result = json.loads((output / "result.json").read_text(encoding="utf-8"))
        self.assertFalse(result["model_invoked"])
        self.assertEqual("externally_supplied_unverified", result["execution_evidence"])
        self.assertEqual("native_codex", result["backend"])
        trace = (output / "tool_trace.jsonl").read_text(encoding="utf-8")
        self.assertIn("fake-test-model", trace)
        self.assertNotIn("Borrador interno", trace)
        self.assertTrue((output / "plan.json").is_file())
        self.assertTrue((output / "plan_receipt.json").is_file())
        self.assertTrue((output / "final_receipt.json").is_file())
        self.assertIn('"mode":"native-selected"', trace)

    def test_native_rejects_invented_or_stale_evidence(self):
        output = self.root / "bad-native-run"
        bad = valid_native_result()
        bad["evidence"][0]["version"] = 999
        run = prepare_agent_run(self.warehouse, output, "intake_admin", backend="native_codex", native_runner=lambda **kwargs: valid_native_plan() if kwargs["stage"] == "plan" else bad)
        self.assertEqual("blocked", run["status"])
        self.assertFalse((output / "result.json").exists())
        self.assertIn("stale or invented evidence", run["blocked_reason"])

    def test_native_rejects_invalid_response_shape(self):
        output = self.root / "schema-native-run"
        malformed = valid_native_result()
        del malformed["workplan"]
        run = prepare_agent_run(self.warehouse, output, "intake_admin", backend="native_codex", native_runner=lambda **kwargs: valid_native_plan() if kwargs["stage"] == "plan" else malformed)
        self.assertEqual("blocked", run["status"])
        self.assertIn("result contract", run["blocked_reason"])

    def test_completion_rejects_a_source_changed_after_prepare(self):
        output = self.root / "stale-source-run"
        malformed = valid_native_result()
        del malformed["workplan"]
        prepare_agent_run(self.warehouse, output, "intake_admin", backend="native_codex", native_runner=lambda **kwargs: valid_native_plan() if kwargs["stage"] == "plan" else malformed)
        connection = sqlite3.connect(self.warehouse)
        connection.execute("UPDATE leads SET status='won' WHERE id='L-001'")
        connection.commit()
        connection.close()
        with self.assertRaisesRegex(ValueError, "warehouse changed"):
            complete_agent_run(output, valid_native_result())

    def test_native_command_is_explicit_local_subscription_cli(self):
        command = _native_command(Path("schema.json"), Path("last.json"), Path("."))
        self.assertEqual("codex", command[0])
        self.assertIn("--ignore-user-config", command)
        self.assertIn("--ephemeral", command)
        self.assertIn("read-only", command)
        self.assertNotIn("priority", " ".join(command))
        for feature in ("shell_tool", "apps", "browser_use", "computer_use", "multi_agent", "plugins"):
            self.assertIn(feature, command)

    def test_invalid_native_plan_blocks_before_the_final_call(self):
        output = self.root / "invalid-plan"
        calls = []

        def fake_runner(**kwargs):
            calls.append(kwargs["stage"])
            return {"evidence_requests": [{"entity_type": "customers", "entity_id": "C-999", "field": "consent"}], "metric_ids": ["open_leads"]}

        run = prepare_agent_run(self.warehouse, output, "intake_admin", backend="native_codex", native_runner=fake_runner)
        self.assertEqual("blocked", run["status"])
        self.assertEqual(["plan"], calls)
        self.assertTrue((output / "plan.json").is_file())
        self.assertIn("outside visible scoped cases", run["blocked_reason"])

    def test_metrics_exclude_active_contracts_outside_the_effective_window(self):
        connection = sqlite3.connect(self.warehouse)
        connection.execute("UPDATE contracts SET starts_at='2027-01-01T00:00:00Z' WHERE id='CT-001'")
        connection.commit()
        connection.close()
        connection = _readonly_connection(self.warehouse)
        profile = next(item for item in list_available_agents() if item["id"] == "fleet_sla_watcher")
        self.assertEqual(0, query_metrics(connection, profile, ["active_contracts"])["active_contracts"])
        connection.close()

    def test_local_validation_rejects_more_alternatives_than_schema_allows(self):
        output = self.root / "too-many-alternatives"
        invalid = valid_native_result()
        invalid["alternatives"] = ["Revisar"] * 7
        run = prepare_agent_run(self.warehouse, output, "intake_admin", backend="native_codex", native_runner=lambda **kwargs: valid_native_plan() if kwargs["stage"] == "plan" else invalid)
        self.assertEqual("blocked", run["status"])
        self.assertIn("invalid alternatives", run["blocked_reason"])

    def test_mocked_prohibited_provider_tool_blocks_before_final(self):
        output = self.root / "prohibited-provider-tool"
        calls = []

        def fake_runner(**kwargs):
            calls.append(kwargs["stage"])
            return {"response": valid_native_plan(), "events": [{"provider_item_type": "command_execution"}]}

        run = prepare_agent_run(self.warehouse, output, "intake_admin", backend="native_codex", native_runner=fake_runner)
        self.assertEqual("blocked", run["status"])
        self.assertEqual(["plan"], calls)
        self.assertIn("prohibited tool", run["blocked_reason"])

    def test_collections_cases_and_aggregate_keep_payment_ownership(self):
        profile = next(item for item in list_available_agents() if item["id"] == "collections_assistant")
        connection = _readonly_connection(self.warehouse)
        cases = inspect_scoped_cases(connection, profile)
        invoice_ids = {case["entity_id"] for case in cases if case["entity_type"] == "invoices"}
        payment_cases = [case for case in cases if case["entity_type"] == "payments"]
        self.assertTrue(invoice_ids)
        self.assertTrue(payment_cases)
        self.assertTrue(all(case["record"]["invoice_id"] in invoice_ids for case in payment_cases))
        metrics = query_metrics(connection, profile, ["unpaid_invoices", "invoice_payment_summary"], invoice_ids=sorted(invoice_ids))
        self.assertEqual(3, metrics["unpaid_invoices"])
        summary = {row["invoice_id"]: row for row in metrics["invoice_payment_summary"]}
        self.assertTrue(set(summary).issubset(invoice_ids))
        self.assertEqual((100000, 85000, 1), (summary["INV-001"]["paid_cents"], summary["INV-001"]["balance_cents"], summary["INV-001"]["payment_count"]))
        self.assertEqual((85000, 0, 1), (summary["INV-003"]["paid_cents"], summary["INV-003"]["balance_cents"], summary["INV-003"]["payment_count"]))
        connection.close()

    def test_fleet_sla_cases_stay_related_to_active_contract(self):
        profile = next(item for item in list_available_agents() if item["id"] == "fleet_sla_watcher")
        connection = _readonly_connection(self.warehouse)
        cases = inspect_scoped_cases(connection, profile)
        contract_ids = {case["entity_id"] for case in cases if case["entity_type"] == "contracts"}
        related_work = [case for case in cases if case["entity_type"] == "work_orders"]
        self.assertTrue(contract_ids and related_work)
        self.assertTrue(all(case["record"]["contract_id"] in contract_ids for case in related_work))
        connection.close()

    def test_maintenance_cases_prefer_earliest_due_record_and_prompt_has_fixed_cutoff(self):
        profile = next(item for item in list_available_agents() if item["id"] == "maintenance_planner")
        connection = _readonly_connection(self.warehouse)
        cases = inspect_scoped_cases(connection, profile)
        self.assertEqual("M-001", next(case["entity_id"] for case in cases if case["entity_type"] == "maintenance"))
        connection.close()
        output = self.root / "cutoff-rules"
        prepare_agent_run(self.warehouse, output, "operations_controller")
        self.assertIn("as_of=2026-09-21T18:00:00Z", (output / "prompt.md").read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
