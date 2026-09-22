"""Structural and traceability contract for formal process specifications."""
import json
import re
import unittest
from collections import defaultdict, deque
from pathlib import Path

from milenio.contracts import FIELDS
from milenio.reports import AGENTS


ROOT = Path(__file__).resolve().parent.parent
PROCESS_DIR = ROOT / "processes"
EXPECTED = {
    "b2c_workshop", "parts_procurement", "fleet_sales_service",
    "towing", "collections", "weekly_review",
}
NODE_TYPES = {"start", "task", "decision", "end"}
MANAGED_FIELDS = {"id", "version", "synthetic", "created_at", "updated_at"}


def load_json(path):
    return json.loads(path.read_text(encoding="utf-8"))


def process_definitions():
    return {path.stem: load_json(path) for path in sorted(PROCESS_DIR.glob("*.json"))}


class ProcessSpecTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.processes = process_definitions()
        cls.catalog = load_json(ROOT / "specs" / "process_catalog.json")
        cls.requirements = load_json(ROOT / "specs" / "requirements.json")["requirements"]
        analytics = (ROOT / "specs" / "analytics.md").read_text(encoding="utf-8")
        cls.metrics = set(re.findall(r"\bM-[A-Z0-9-]+\b", analytics))

    def test_six_processes_and_render_catalog_are_complete(self):
        self.assertEqual(set(self.processes), EXPECTED)
        entries = self.catalog["processes"]
        self.assertEqual({entry["id"] for entry in entries}, EXPECTED)
        self.assertEqual(len({entry["order"] for entry in entries}), 6)
        for entry in entries:
            self.assertEqual(entry["definition"], f"processes/{entry['id']}.json")
            self.assertEqual(entry["document"], f"processes/{entry['id']}.md")
            self.assertTrue((ROOT / entry["definition"]).is_file())
            self.assertTrue((ROOT / entry["document"]).is_file())

    def test_process_references_resolve_to_implemented_contracts(self):
        for process_id, spec in self.processes.items():
            with self.subTest(process=process_id):
                self.assertEqual(spec["schema_version"], "1.0")
                self.assertEqual(spec["process_id"], process_id)
                self.assertTrue(set(spec["entities"]) <= set(FIELDS))
                self.assertTrue(set(spec["agents"]) <= set(AGENTS))
                self.assertTrue(set(spec["metrics"]) <= self.metrics)

                role_ids = {role["id"] for role in spec["roles"]}
                self.assertIn(spec["accountable_owner"], role_ids)
                self.assertTrue(all(role["lane"].strip() for role in spec["roles"]))
                evidence_ids = {item["id"] for item in spec["evidence"]}
                control_ids = {item["id"] for item in spec["controls"]}
                self.assertEqual(len(evidence_ids), len(spec["evidence"]))
                self.assertEqual(len(control_ids), len(spec["controls"]))
                for evidence in spec["evidence"]:
                    self.assertIn(evidence["entity"], FIELDS)
                    self.assertIn(evidence["entity"], spec["entities"])
                    allowed = set(FIELDS[evidence["entity"]]) | MANAGED_FIELDS
                    self.assertTrue(set(evidence["fields"]) <= allowed, evidence)

                node_ids = {node["id"] for node in spec["nodes"]}
                self.assertEqual(len(node_ids), len(spec["nodes"]))
                for node in spec["nodes"]:
                    self.assertIn(node["type"], NODE_TYPES)
                    self.assertIn(node["owner"], role_ids)
                    self.assertTrue(set(node["controls"]) <= control_ids)
                    self.assertTrue(set(node["evidence_ids"]) <= evidence_ids)
                    self.assertTrue(set(node["metric_ids"]) <= set(spec["metrics"]))
                    self.assertTrue(set(node["agent_ids"]) <= set(spec["agents"]))
                    for item in node["inputs"]:
                        if "." in item:
                            entity, field = item.split(".", 1)
                            if entity in FIELDS:
                                self.assertIn(field, set(FIELDS[entity]) | MANAGED_FIELDS, item)

                for transition in spec["transitions"]:
                    self.assertIn(transition["from"], node_ids)
                    self.assertIn(transition["to"], node_ids)
                    self.assertTrue(transition["condition"].strip())
                    self.assertTrue(set(transition["evidence_ids"]) <= evidence_ids)

    def test_graph_nodes_are_reachable_and_can_reach_an_end(self):
        for process_id, spec in self.processes.items():
            with self.subTest(process=process_id):
                nodes = {node["id"]: node for node in spec["nodes"]}
                starts = [node["id"] for node in spec["nodes"] if node["type"] == "start"]
                ends = {node["id"] for node in spec["nodes"] if node["type"] == "end"}
                self.assertEqual(len(starts), 1)
                self.assertTrue(ends)
                outgoing, incoming = defaultdict(list), defaultdict(list)
                for edge in spec["transitions"]:
                    outgoing[edge["from"]].append(edge)
                    incoming[edge["to"]].append(edge["from"])

                reached, queue = set(), deque(starts)
                while queue:
                    current = queue.popleft()
                    if current in reached:
                        continue
                    reached.add(current)
                    queue.extend(edge["to"] for edge in outgoing[current])
                self.assertEqual(reached, set(nodes))

                reaches_end, queue = set(), deque(ends)
                while queue:
                    current = queue.popleft()
                    if current in reaches_end:
                        continue
                    reaches_end.add(current)
                    queue.extend(incoming[current])
                self.assertEqual(reaches_end, set(nodes))

                for node in spec["nodes"]:
                    branches = outgoing[node["id"]]
                    if node["type"] == "decision":
                        self.assertGreaterEqual(len(branches), 2, node["id"])
                        self.assertEqual(len({edge["condition"] for edge in branches}), len(branches))
                    elif node["type"] == "end":
                        self.assertEqual(branches, [])
                    else:
                        self.assertGreaterEqual(len(branches), 1, node["id"])

    def test_requirements_trace_to_process_entity_agent_metric_and_acceptance(self):
        acceptance = {
            test["id"]
            for process in self.processes.values()
            for test in process["acceptance_tests"]
        }
        self.assertEqual(len(acceptance), 18)
        requirement_ids = {req["id"] for req in self.requirements}
        self.assertEqual(len(requirement_ids), len(self.requirements))
        covered_processes = set()
        for requirement in self.requirements:
            self.assertRegex(requirement["id"], r"^REQ-[A-Z0-9]+-[0-9]{3}$")
            self.assertIn(requirement["priority"], {"must", "should", "could"})
            self.assertTrue(requirement["statement"].strip())
            self.assertTrue(set(requirement["processes"]) <= EXPECTED)
            self.assertTrue(set(requirement["entities"]) <= set(FIELDS))
            self.assertTrue(set(requirement["agents"]) <= set(AGENTS))
            self.assertTrue(set(requirement["metrics"]) <= self.metrics)
            self.assertTrue(set(requirement["acceptance"]) <= acceptance)
            covered_processes.update(requirement["processes"])
        self.assertEqual(covered_processes, EXPECTED)

    def test_readable_sops_include_diagram_exceptions_raci_and_acceptance(self):
        for process_id in EXPECTED:
            text = (PROCESS_DIR / f"{process_id}.md").read_text(encoding="utf-8")
            with self.subTest(process=process_id):
                self.assertIn("```mermaid", text)
                self.assertRegex(text, r"(?i)exceptions|excepciones")
                self.assertIn("RACI", text)
                self.assertRegex(text, r"(?i)acceptance|aceptación")


if __name__ == "__main__":
    unittest.main()
