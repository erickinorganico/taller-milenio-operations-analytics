"""Independent adversarial cases for the normalized v2 analytical warehouse."""
import copy
import sqlite3
import tempfile
import unittest
from datetime import timedelta, timezone
from pathlib import Path

from milenio.agent_runtime import (
    AgentRuntimeError, _load_profiles, _readonly_connection, _result_schema,
    _validate_shape, query_metrics,
)
from milenio.contracts import DEMO_NOW
from milenio.domain import date_value
from milenio.process_replay import analyze_process_events
from milenio.reports import projections
from milenio.scenarios import make_operating_scenario
from milenio.studio_analytics import build_marts
from milenio.warehouse import build_warehouse


class V2AdversarialTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.scenario = make_operating_scenario()

    def build(self, events=None, journeys=None, data=None):
        path = self.root / 'warehouse.sqlite'
        build_warehouse(path, data or self.scenario['dataset'],
                        self.scenario['events'] if events is None else events,
                        self.scenario['journeys'] if journeys is None else journeys)
        return path

    def test_initial_event_cannot_jump_directly_to_delivery(self):
        event = dict(self.scenario['events'][7], from_state='initial')
        with self.assertRaises(ValueError):
            self.build(events=[event])

    def test_missing_initial_event_rejects_with_a_validation_error(self):
        with self.assertRaises(ValueError):
            self.build(events=[self.scenario['events'][7]])

    def test_valid_open_work_history_does_not_require_completion(self):
        work = next(x for x in self.scenario['dataset']['work_orders'] if x['id'] == 'WO-007')
        event = {'event_id': 'EV-OPEN-001', 'entity_type': 'work_orders', 'entity_id': work['id'],
                 'from_state': 'initial', 'to_state': 'received', 'at': work['opened_at'],
                 'actor': 'Synthetic observer', 'process_id': 'PROC-OPEN', 'synthetic': True}
        self.assertTrue(self.build(events=[event]).is_file())

    def test_event_identifier_cannot_be_null(self):
        events = copy.deepcopy(self.scenario['events'])
        events[0]['event_id'] = None
        with self.assertRaises(ValueError):
            self.build(events=events)

    def test_individually_legal_edges_must_form_a_contiguous_chain(self):
        events = copy.deepcopy(self.scenario['events'])
        events[1].update(from_state='inspected', to_state='authorized')
        with self.assertRaises(ValueError):
            self.build(events=events)

    def test_lifecycle_endpoints_match_business_timestamps(self):
        events = copy.deepcopy(self.scenario['events'])
        for event in events[:8]:
            event['at'] = (date_value(event['at']) - timedelta(hours=1)).isoformat()
        with self.assertRaises(ValueError):
            self.build(events=events)

    def test_lifecycle_events_cannot_be_after_snapshot_cutoff(self):
        events = copy.deepcopy(self.scenario['events'])
        for i, event in enumerate(events[:8]):
            event['at'] = (date_value(DEMO_NOW) + timedelta(hours=i+1)).isoformat()
        with self.assertRaises(ValueError):
            self.build(events=events)

    def test_timezone_spelling_does_not_change_process_metrics(self):
        events = copy.deepcopy(self.scenario['events'][:8])
        expected = analyze_process_events(events, self.scenario['dataset'])
        events[3]['at'] = date_value(events[3]['at']).astimezone(timezone(timedelta(hours=-12))).isoformat()
        actual = analyze_process_events(events, self.scenario['dataset'])
        self.assertEqual(actual['cases'], expected['cases'])
        self.assertEqual(actual['summary']['invalid_transition_count'], 0)

    def test_timezone_spelling_does_not_change_materialized_stage_metrics(self):
        baseline = build_marts(self.build())['marts']['mart_process_waits']
        altered = copy.deepcopy(self.scenario['events'])
        altered[3]['at'] = date_value(altered[3]['at']).astimezone(timezone(timedelta(hours=-12))).isoformat()
        path = self.root / 'offset.sqlite'
        build_warehouse(path, self.scenario['dataset'], altered, self.scenario['journeys'])
        self.assertEqual(build_marts(path)['marts']['mart_process_waits'], baseline)

    def test_cents_columns_enforce_integer_storage(self):
        con = sqlite3.connect(self.build())
        try:
            for invalid in ('nonnumeric', 1.5):
                with self.subTest(value=invalid), self.assertRaises(sqlite3.IntegrityError):
                    con.execute('UPDATE invoices SET amount_cents=? WHERE id=?', (invalid, 'INV-001'))
        finally:
            con.close()

    def test_journey_quote_must_equal_the_work_order_quote(self):
        journeys = copy.deepcopy(self.scenario['journeys'])
        first = journeys[0]
        work = next(x for x in self.scenario['dataset']['work_orders'] if x['id'] == first['work_order_id'])
        alternate = next(x for x in self.scenario['dataset']['quotes']
                         if x['customer_id'] == work['customer_id'] and x['vehicle_id'] == work['vehicle_id']
                         and x['id'] != work['quote_id'])
        first['quote_id'] = alternate['id']
        with self.assertRaises(ValueError):
            self.build(journeys=journeys)

    def test_marts_cannot_relabel_fixed_snapshot_as_an_earlier_cutoff(self):
        path = self.build()
        with self.assertRaises(ValueError):
            build_marts(path, as_of='2026-01-01T00:00:00Z')

    def test_agent_active_contract_metric_respects_effective_window(self):
        data = copy.deepcopy(self.scenario['dataset'])
        data['contracts'][0].update(starts_at='2027-01-01T00:00:00Z', ends_at='2028-01-01T00:00:00Z')
        path = self.build(data=data)
        con = _readonly_connection(path)
        try:
            metric = query_metrics(con, _load_profiles()['fleet_sla_watcher'], ['active_contracts'])
            self.assertEqual(metric['active_contracts'], 0)
        finally:
            con.close()

    def test_sla_risk_is_consistent_between_mart_and_existing_projection(self):
        data = copy.deepcopy(self.scenario['dataset'])
        work = copy.deepcopy(next(x for x in data['work_orders'] if x['id'] == 'WO-009'))
        work.update(id='WO-SLA-COMPARE', status='received', quote_id=None,
                    completed_at=None, bay_id=None, technician_id=None,
                    opened_at=(date_value(DEMO_NOW) - timedelta(hours=40)).isoformat())
        data['work_orders'].append(work)
        expected = next(x['sla_status'] for x in projections(data)['work_orders'] if x['id'] == work['id'])
        actual = build_marts(self.build(data=data))['marts']['mart_service_journey']
        self.assertEqual(next(x['sla_status'] for x in actual if x['work_order_id'] == work['id']), expected)

    def test_local_native_result_validation_enforces_schema_array_limits(self):
        result = {
            'diagnosis': 'Synthetic internal review.', 'alternatives': ['Option'] * 7,
            'manual_next_steps': ['Review'], 'drafts': [], 'missing_information': [],
            'sensitivity': {'level': 'low', 'reason': 'Synthetic'},
            'evidence': [{'entity_type': 'leads', 'entity_id': 'L-001', 'field': 'status', 'value': 'new', 'version': 1}],
            'workplan': ['Review'],
        }
        with self.assertRaises(AgentRuntimeError):
            _validate_shape(result, _result_schema())


if __name__ == '__main__':
    unittest.main()
