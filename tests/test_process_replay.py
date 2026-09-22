import unittest
from datetime import datetime, timedelta, timezone

from milenio.process_replay import analyze_process_events
from milenio.scenarios import make_operating_scenario


class ProcessReplayTests(unittest.TestCase):
    def test_variants_wait_rework_and_cycle_reconcile(self):
        scenario = make_operating_scenario()
        result = analyze_process_events(scenario["events"], scenario["dataset"])
        self.assertGreaterEqual(result["summary"]["case_count"], 150)
        self.assertEqual(result["summary"]["invalid_transition_count"], 0)
        self.assertTrue(any("waiting_parts" in row["variant"] for row in result["variants"]))
        self.assertTrue(any("rework" in row["variant"] for row in result["variants"]))
        self.assertAlmostEqual(result["summary"]["cycle_hours"], result["summary"]["stage_hours"])

    def test_invalid_out_of_order_is_detected_without_mutation(self):
        scenario = make_operating_scenario()
        events = list(reversed(scenario["events"][:8]))
        original = [dict(event) for event in events]
        result = analyze_process_events(events, scenario["dataset"])
        self.assertGreater(result["summary"]["out_of_order_count"], 0)
        self.assertEqual(events, original)

    def test_missing_history_is_unknown_and_invalid_transition_is_counted(self):
        scenario = make_operating_scenario()
        events = [dict(scenario["events"][0]), dict(scenario["events"][1])]
        events[1]["from_state"], events[1]["to_state"] = "received", "delivered"
        result = analyze_process_events(events, scenario["dataset"])
        self.assertGreater(result["summary"]["invalid_transition_count"], 0)
        self.assertGreater(result["summary"]["history_coverage"]["unknown"], 0)

    def test_equivalent_timezone_offsets_sort_by_time_not_text(self):
        scenario = make_operating_scenario()
        baseline = analyze_process_events(scenario["events"], scenario["dataset"])
        shifted = [dict(event) for event in scenario["events"]]
        original = shifted[0]["at"]
        parsed = datetime.fromisoformat(original.replace("Z", "+00:00"))
        shifted[0]["at"] = parsed.astimezone(timezone(timedelta(hours=-7))).isoformat()
        replayed = analyze_process_events(shifted, scenario["dataset"])
        self.assertEqual(replayed["summary"]["cycle_hours"], baseline["summary"]["cycle_hours"])
        self.assertEqual(replayed["summary"]["invalid_transition_count"], baseline["summary"]["invalid_transition_count"])


if __name__ == "__main__":
    unittest.main()
