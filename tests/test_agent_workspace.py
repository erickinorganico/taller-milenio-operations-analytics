import hashlib
import json
import sqlite3
import tempfile
import unittest
from pathlib import Path

from milenio.agent_workspace import build_agent_workspace
from milenio.agent_runtime import AgentRuntimeError, list_available_agents, query_metrics, _readonly_connection
from milenio.fixtures import make_fixture
from milenio.metric_registry import build_metric_registry
from milenio.client_actions import write_action_workbook
from milenio.warehouse import build_warehouse


class AgentWorkspaceTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary.name)
        self.database = self.root / "warehouse.sqlite"
        build_warehouse(self.database, make_fixture())
        self.runs = self.root / "current"
        self.history = self.root / "history"
        self.metric_registry = {
            "as_of": "2026-09-21T18:00:00Z",
            "synthetic": True,
            "metrics": [{"metric_id": metric_id, "value": None, "status": "unknown", "reason": "fixture"}
                        for metric_id in self._allowed_metric_ids()],
        }

    def tearDown(self):
        self.temporary.cleanup()

    @staticmethod
    def _allowed_metric_ids():
        spec = Path(__file__).resolve().parents[1] / "specs" / "agent_operating_contract.json"
        payload = json.loads(spec.read_text(encoding="utf-8"))
        return sorted({metric_id for role in payload["roles"] for metric_id in role["metric_ids"]})

    def _write_run(self, root, *, source_hash=None, agent_id="intake_admin"):
        run_dir = root / agent_id
        run_dir.mkdir(parents=True)
        source_hash = source_hash or hashlib.sha256(self.database.read_bytes()).hexdigest()
        connection = sqlite3.connect(self.database)
        status, version = connection.execute("SELECT status,version FROM leads WHERE id='L-001'").fetchone()
        connection.close()
        reference = {"entity_type": "leads", "entity_id": "L-001", "field": "status", "value": status, "version": version}
        case = {"entity_type": "leads", "entity_id": "L-001", "version": version,
                "record": {"id": "L-001", "version": version, "status": status}}
        (run_dir / "run.json").write_text(json.dumps({
            "agent_id": agent_id, "backend": "rules", "status": "completed",
            "warehouse_sha256": source_hash, "source_hash_verified": True,
            "external_execution": False,
        }), encoding="utf-8")
        (run_dir / "input_packet.json").write_text(json.dumps({
            "warehouse_sha256": source_hash, "as_of": "2026-09-21T18:00:00Z", "synthetic": True,
            "tool_context": {"cases": [case], "evidence": [reference], "metrics": {}},
        }), encoding="utf-8")
        (run_dir / "tool_trace.jsonl").write_text('{"tool":"query_metrics","status":"ok"}\n', encoding="utf-8")
        (run_dir / "plan.json").write_text(json.dumps({"metric_ids": ["M-B2C-LEADS"]}), encoding="utf-8")
        (run_dir / "result.json").write_text(json.dumps({
            "status": "completed", "backend": "rules", "model_invoked": False,
            "mode_label": "offline deterministic baseline; no LLM invoked", "external_execution": False,
            "result": {
                "diagnosis": "La línea base señala este registro para revisión humana.",
                "evidence": [reference], "manual_next_steps": ["Confirmar el estado con la fuente."],
                "drafts": [{"kind": "followup", "text": "Borrador interno", "requires_human_review": True}],
                "missing_information": ["Falta contexto del negocio."],
            },
        }), encoding="utf-8")
        return run_dir

    def test_current_hash_run_yields_client_action_and_pending_proposal(self):
        run_dir = self._write_run(self.runs)
        workspace = build_agent_workspace(self.database, self.metric_registry, self.runs)
        role = next(item for item in workspace["agents"] if item["agent_id"] == "intake_admin")
        self.assertEqual("current", role["current_run"]["status"])
        self.assertFalse(role["current_run"]["model_invoked"])
        self.assertEqual("query_metrics", role["current_run"]["tool_trace"][-1]["tool"])
        self.assertEqual(1, len(role["proposals"]))
        action = role["proposals"][0]
        self.assertEqual(["leads:L-001"], action["source_ids"])
        self.assertNotIn("L-001", action["title"])
        self.assertEqual([{"kind": "followup", "text": "Borrador interno", "requires_human_review": True}], action["drafts"])
        self.assertIsNone(action["amount_at_risk_cents"])
        self.assertEqual("pending", action["action_proposal"]["status"])
        self.assertTrue(action["approval_required"])
        self.assertFalse(action["external_execution"])
        self.assertEqual("M-B2C-LEADS", action["metric_ids"][0])
        self.assertEqual(run_dir.as_posix(), role["current_run"]["run_path"].replace("\\", "/"))
        workbook = self.root / "Seguimiento.xlsx"
        written = write_action_workbook(workbook, workspace["decisions"], {
            "snapshot_id": workspace["source"]["sha256"], "as_of": workspace["source"]["as_of"], "synthetic": True,
        })
        self.assertTrue(written)
        self.assertTrue(workbook.is_file())

    def test_query_metrics_accepts_process_metric_ids_and_enforces_role_allowlist(self):
        profile = next(item for item in list_available_agents() if item["id"] == "intake_admin")
        connection = _readonly_connection(self.database)
        try:
            result = query_metrics(connection, profile, ["M-B2C-LEADS", "open_leads"])
            self.assertEqual("M-B2C-LEADS", result["M-B2C-LEADS"]["metric_id"])
            self.assertIn(result["M-B2C-LEADS"]["status"], {"measured", "unknown"})
            self.assertIsInstance(result["open_leads"], int)
            with self.assertRaises(AgentRuntimeError):
                query_metrics(connection, profile, ["M-AR-OVERDUE"])
        finally:
            connection.close()
        self.assertEqual(31, len(build_metric_registry(self.database)["metrics"]))

    def test_stale_current_run_is_not_promoted_and_history_stays_historical(self):
        stale_hash = "0" * 64
        self._write_run(self.runs, source_hash=stale_hash)
        self._write_run(self.history, source_hash=stale_hash)
        workspace = build_agent_workspace(self.database, self.metric_registry, self.runs, self.history)
        role = next(item for item in workspace["agents"] if item["agent_id"] == "intake_admin")
        self.assertEqual("stale", role["current_run"]["status"])
        self.assertEqual([], role["proposals"])
        self.assertEqual("historical_source", role["historical_runs"][0]["status"])
        self.assertFalse(any(item["source_hash"] == stale_hash for item in workspace["decisions"]))

    def test_unmapped_draft_is_one_run_level_proposal_not_replicated_per_case(self):
        run_dir = self._write_run(self.runs)
        result_path = run_dir / "result.json"
        result = json.loads(result_path.read_text(encoding="utf-8"))
        connection = sqlite3.connect(self.database)
        row = connection.execute("SELECT version,channel FROM leads WHERE id='L-002'").fetchone()
        connection.close()
        second_ref = {"entity_type": "leads", "entity_id": "L-002", "field": "channel", "value": row[1], "version": row[0]}
        packet_path = run_dir / "input_packet.json"
        packet = json.loads(packet_path.read_text(encoding="utf-8"))
        packet["tool_context"]["cases"].append({"entity_type": "leads", "entity_id": "L-002", "version": row[0], "record": {"id": "L-002", "version": row[0], "channel": row[1]}})
        packet["tool_context"]["evidence"].append(second_ref)
        packet_path.write_text(json.dumps(packet), encoding="utf-8")
        result["result"]["evidence"].append(second_ref)
        result_path.write_text(json.dumps(result), encoding="utf-8")
        workspace = build_agent_workspace(self.database, self.metric_registry, self.runs)
        actions = [item for item in workspace["decisions"] if item["owner_role"] == "Recepción"]
        self.assertEqual(1, len(actions))
        self.assertEqual(["leads:L-001", "leads:L-002"], actions[0]["source_ids"])
        self.assertEqual(2, len(actions[0]["action_proposal"]["evidence"]))

    def test_forged_or_stale_result_evidence_blocks_same_hash_run(self):
        run_dir = self._write_run(self.runs)
        result_path = run_dir / "result.json"
        result = json.loads(result_path.read_text(encoding="utf-8"))
        for field, value in (("value", "invented"), ("version", 999)):
            forged = json.loads(json.dumps(result))
            forged["result"]["evidence"][0][field] = value
            result_path.write_text(json.dumps(forged), encoding="utf-8")
            workspace = build_agent_workspace(self.database, self.metric_registry, self.runs)
            role = next(item for item in workspace["agents"] if item["agent_id"] == "intake_admin")
            self.assertEqual("blocked", role["current_run"]["status"])
            self.assertIn("revalidation", role["current_run"]["reason"])
            self.assertEqual([], role["proposals"])

    def test_registry_digest_mismatch_fails_closed(self):
        registry = {**self.metric_registry, "source_sha256": "0" * 64}
        with self.assertRaisesRegex(ValueError, "metric registry source hash"):
            build_agent_workspace(self.database, registry, self.runs)

    def test_input_packet_digest_mismatch_blocks_a_current_run(self):
        run_dir = self._write_run(self.runs)
        (run_dir / "input_packet.json").write_text(json.dumps({
            "warehouse_sha256": "0" * 64, "as_of": "2026-09-21T18:00:00Z", "synthetic": True,
        }), encoding="utf-8")
        workspace = build_agent_workspace(self.database, self.metric_registry, self.runs)
        role = next(item for item in workspace["agents"] if item["agent_id"] == "intake_admin")
        self.assertEqual("blocked", role["current_run"]["status"])
        self.assertIn("hashes disagree", role["current_run"]["reason"])
        self.assertEqual([], role["proposals"])


if __name__ == "__main__":
    unittest.main()
