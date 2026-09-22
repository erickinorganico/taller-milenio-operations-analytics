"""Read-only lifecycle event replay and process conformance summaries."""
from __future__ import annotations

from collections import Counter, defaultdict
from copy import deepcopy
from datetime import datetime

from .contracts import FLOWS


def _date(value):
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def analyze_process_events(events, dataset):
    """Analyze synthetic lifecycle events without mutating events or dataset."""
    source = deepcopy(list(events))
    grouped = defaultdict(list)
    for index, event in enumerate(source):
        grouped[(event["entity_type"], event["entity_id"])].append((index, event))
    cases, transitions, durations = [], Counter(), defaultdict(float)
    variants = Counter()
    invalid = 0
    chain_errors = 0
    out_of_order = 0
    for (kind, ident), raw in sorted(grouped.items()):
        original_times = [_date(e["at"]) for _, e in raw]
        out_of_order += sum(1 for before, after in zip(original_times, original_times[1:]) if after < before)
        trace = [event for _, event in sorted(raw, key=lambda pair: (_date(pair[1]["at"]), pair[1].get("event_id", ""), pair[0]))]
        states = [e["to_state"] for e in trace]
        case_invalid = 0
        if not trace or trace[0].get("from_state") != "initial" or (kind in FLOWS and trace[0].get("to_state") != next(iter(FLOWS[kind]))):
            chain_errors += 1
            case_invalid += 1
        stage_hours = {}
        for previous, current in zip(trace, trace[1:]):
            elapsed = (_date(current["at"]) - _date(previous["at"])).total_seconds() / 3600
            durations[previous["to_state"]] += elapsed
            stage_hours[previous["to_state"]] = stage_hours.get(previous["to_state"], 0) + elapsed
            from_state, to_state = previous["to_state"], current["to_state"]
            legal = kind in FLOWS and current.get("from_state") == from_state and to_state in FLOWS[kind].get(from_state, [])
            transitions[(kind, from_state, to_state, "valid" if legal else "invalid")] += 1
            if not legal:
                invalid += 1
                case_invalid += 1
        record = next((r for r in dataset.get(kind, []) if r.get("id") == ident), None)
        endpoint_ok = bool(record and (not record.get("status") or record["status"] == states[-1])) if states else False
        if not endpoint_ok:
            chain_errors += 1
        variant = "→".join(states)
        variants[(kind, variant)] += 1
        cases.append({"entity_type": kind, "entity_id": ident, "states": states, "events": len(trace), "variant": variant, "stage_hours": {key: round(value, 3) for key, value in stage_hours.items()}, "cycle_hours": round(sum(stage_hours.values()), 3), "endpoint_ok": endpoint_ok, "invalid_transitions": case_invalid})
    stateful = [(kind, row) for kind, rows in dataset.items() if kind in FLOWS for row in rows]
    covered = {(case["entity_type"], case["entity_id"]) for case in cases}
    unknown = [{"entity_type": kind, "entity_id": row["id"], "status": row.get("status")} for kind, row in stateful if (kind, row["id"]) not in covered]
    transition_rows = [{"entity_type": kind, "from_state": before, "to_state": after, "validity": validity, "count": count} for (kind, before, after, validity), count in sorted(transitions.items())]
    duration_rows = [{"state": state, "hours": round(hours, 3)} for state, hours in sorted(durations.items())]
    variant_rows = [{"entity_type": kind, "variant": variant, "count": count} for (kind, variant), count in sorted(variants.items())]
    return {"cases": cases, "transitions": transition_rows, "stage_durations": duration_rows, "variants": variant_rows, "summary": {"case_count": len(cases), "stateful_record_count": len(stateful), "history_coverage": {"observed": len(covered), "unknown": len(unknown), "unknown_records": unknown}, "invalid_transition_count": invalid, "chain_error_count": chain_errors, "conformance": "pass" if not chain_errors and not out_of_order else "review", "out_of_order_count": out_of_order, "endpoint_mismatch_count": sum(not case["endpoint_ok"] for case in cases), "cycle_hours": round(sum(case["cycle_hours"] for case in cases), 3), "stage_hours": round(sum(durations.values()), 3)}}


__all__ = ["analyze_process_events"]
