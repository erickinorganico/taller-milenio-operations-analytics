"""Independent adversarial regressions; all data and artifacts are synthetic."""
import copy
import json
import tempfile
import unittest
from datetime import timedelta
from pathlib import Path
from unittest.mock import patch

from milenio.agents import evaluate_proposals, run_agents
from milenio.analysis import analyze
from milenio.contracts import DEMO_NOW
from milenio.domain import DomainError, date_value, validate_dataset
from milenio.fixtures import make_fixture
from milenio.pipeline import file_hash, verify_receipt
from milenio.presentation import render_reports
from milenio.reports import projections
from milenio.storage import digest
from milenio.timeline import synthetic_history, validate_history


class AdversarialTests(unittest.TestCase):
    def test_on_track_open_sla_is_not_at_risk(self):
        data = make_fixture()
        contract = data['contracts'][0]
        contract['sla_hours'] = 200
        work = copy.deepcopy(next(x for x in data['work_orders'] if x['id'] == 'WO-009'))
        work.update(id='WO-SLA-OPEN', status='received', quote_id=None,
                    completed_at=None, bay_id=None, technician_id=None, qc_ref=None)
        data['work_orders'].append(work)
        validate_dataset(data)
        self.assertEqual(next(x['sla_status'] for x in projections(data)['work_orders']
                              if x['id'] == work['id']), 'on_track')
        ratio = analyze(data)['flotillas']['contracted']['sla_open_at_risk']
        self.assertEqual((ratio['numerator'], ratio['denominator']), (0, 1))

    def test_nonoperative_contract_does_not_establish_sla(self):
        for state in ('draft', 'cancelled'):
            with self.subTest(state=state):
                data = make_fixture()
                data['contracts'][0]['status'] = state
                validate_dataset(data)
                work = next(x for x in projections(data)['work_orders'] if x['id'] == 'WO-009')
                self.assertEqual(work['sla_status'], 'unknown')
                self.assertEqual(analyze(data)['flotillas']['contracted']['sla_completed_met']['denominator'], 0)

    def test_snapshot_cannot_be_relabelled_with_earlier_as_of(self):
        # Snapshot contains September 18-21 services and cash. Without point-in-
        # time reconstruction an earlier label is a materially false report.
        with self.assertRaises(DomainError):
            analyze(make_fixture(), '2026-09-01T00:00:00Z')

    def test_cancelled_work_is_excluded_even_when_contract_is_unknown(self):
        data = make_fixture()
        work = copy.deepcopy(next(x for x in data['work_orders'] if x['id'] == 'WO-009'))
        work.update(id='WO-CANCELLED-FLEET', status='cancelled', quote_id=None,
                    completed_at=None)
        data['work_orders'].append(work)
        data['contracts'][0].update(status='draft', approval_ref=None)
        validate_dataset(data)
        projected = next(x for x in projections(data)['work_orders'] if x['id'] == work['id'])
        self.assertEqual(projected['sla_status'], 'excluded')

    def test_nonterminal_work_cannot_freeze_downtime_with_completion(self):
        data = make_fixture()
        work = next(x for x in data['work_orders'] if x['status'] == 'in_service')
        work['completed_at'] = work['opened_at']
        with self.assertRaises(DomainError):
            validate_dataset(data)

    def test_fully_returned_parts_cannot_retain_consumption_cost(self):
        data = make_fixture()
        returned = next(x for x in data['stock_moves'] if x['move_type'] == 'return')
        returned.update(quantity=2, unit_cost_cents=0)
        with self.assertRaises(DomainError):
            validate_dataset(data)

    def test_state_history_must_match_observed_work_timestamps(self):
        data = make_fixture()
        history = synthetic_history(data)
        for event in history:
            if event['entity_type'] == 'work_orders' and event['entity_id'] == 'WO-001':
                event['at'] = (date_value(event['at']) - timedelta(days=1)).isoformat()
        with self.assertRaises(DomainError):
            validate_history(data, history)

    def test_nested_receipt_is_not_exempt_from_artifact_manifest(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            artifact = root / 'analysis.json'
            artifact.write_text('{}', encoding='utf-8')
            files = {'analysis.json': file_hash(artifact)}
            receipt = {'status': 'pass', 'synthetic': True,
                       'artifacts_sha256': files, 'content_sha256': digest(files)}
            (root / 'receipt.json').write_text(json.dumps(receipt), encoding='utf-8')
            verify_receipt(root)
            (root / 'unexpected').mkdir()
            (root / 'unexpected' / 'receipt.json').write_text('unmanifested', encoding='utf-8')
            with self.assertRaises(DomainError):
                verify_receipt(root)

    def test_zero_duration_is_a_measurement_in_rendered_report(self):
        result = analyze(make_fixture())
        result['gruas']['timing']['median_request_to_close_hours'] = 0.0
        result['taller']['wip']['median_open_hours'] = 0.0
        with tempfile.TemporaryDirectory() as directory, patch('milenio.presentation._chart'):
            render_reports(result, directory)
            for report in ('gruas.md', 'taller.md'):
                self.assertNotIn('Sin casos', Path(directory, report).read_text(encoding='utf-8'))

    def test_proposals_reject_invented_evidence_and_external_execution(self):
        data = make_fixture()
        proposals, grade = run_agents(data, DEMO_NOW)
        self.assertEqual(grade['critical_violations'], 0)
        self.assertEqual(grade['external_tools'], [])
        for key, value in (('external_execution', True), ('approval_required', False)):
            bad = copy.deepcopy(proposals)
            bad[0][key] = value
            with self.assertRaises(DomainError):
                evaluate_proposals(data, bad)
        bad = copy.deepcopy(proposals)
        bad[0]['evidence'][0]['value'] = 'invented evidence'
        with self.assertRaises(DomainError):
            evaluate_proposals(data, bad)

    def test_source_proposals_cannot_smuggle_false_field_evidence(self):
        data = make_fixture()
        data['proposals'][0]['evidence'][0].update(
            field='does_not_exist', value='invented evidence', version=999)
        with self.assertRaises(DomainError):
            validate_dataset(data)

    def test_capacity_duplicate_assignment_rejected(self):
        data = make_fixture()
        busy = [x for x in data['work_orders'] if x['status'] in {'in_service', 'quality_check'}]
        busy[1]['bay_id'] = busy[0]['bay_id']
        with self.assertRaises(DomainError):
            validate_dataset(data)

    def test_invoice_customer_join_rejected(self):
        data = make_fixture()
        data['invoices'][0]['customer_id'] = 'C-002'
        with self.assertRaises(DomainError):
            validate_dataset(data)

    def test_negative_service_durations_are_rejected(self):
        for kind, identifier, start, end in (
            ('work_orders', 'WO-001', 'opened_at', 'completed_at'),
            ('tows', 'TW-001', 'requested_at', 'closed_at'),
        ):
            with self.subTest(kind=kind):
                data = make_fixture()
                record = next(x for x in data[kind] if x['id'] == identifier)
                record[end] = (date_value(record[start]) - timedelta(minutes=1)).isoformat()
                with self.assertRaises(DomainError):
                    validate_dataset(data)

    def test_receipt_detects_edited_and_missing_artifacts(self):
        for changed in ('edited', 'missing'):
            with self.subTest(changed=changed), tempfile.TemporaryDirectory() as directory:
                root = Path(directory)
                artifact = root / 'analysis.json'
                artifact.write_text('{}', encoding='utf-8')
                files = {'analysis.json': file_hash(artifact)}
                receipt = {'status': 'pass', 'synthetic': True,
                           'artifacts_sha256': files, 'content_sha256': digest(files)}
                (root / 'receipt.json').write_text(json.dumps(receipt), encoding='utf-8')
                if changed == 'edited':
                    artifact.write_text('{"tampered":true}', encoding='utf-8')
                else:
                    artifact.unlink()
                with self.assertRaises(DomainError):
                    verify_receipt(root)


if __name__ == '__main__':
    unittest.main()
