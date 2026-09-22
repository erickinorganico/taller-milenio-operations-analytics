"""Safe adapter for complete synthetic CSV snapshots or dataset JSON."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

from .contracts import DEMO_NOW, FIELDS
from .domain import validate_dataset
from .snapshot_io import load_snapshot


def _json(path):
    value = json.loads(path.read_text(encoding="utf-8-sig"))
    if not isinstance(value, dict):
        raise ValueError("dataset JSON must be an object keyed by entity type")
    validate_dataset(value)
    return value


def _optional_list(path, label):
    if path is None:
        return []
    value = json.loads(Path(path).read_text(encoding="utf-8-sig"))
    if not isinstance(value, list):
        raise ValueError(f"{label} JSON must be a list")
    return value


def load_studio_input(input_path, events_path=None, journeys_path=None):
    source = Path(input_path).resolve()
    if source.is_dir():
        dataset = load_snapshot(source)
        files = sorted(source.glob("*.csv"))
    elif source.is_file() and source.suffix.lower() == ".json":
        dataset = _json(source)
        files = [source]
    else:
        raise ValueError("input_path must be a complete CSV snapshot directory or dataset JSON")
    events = _optional_list(events_path, "events")
    journeys = _optional_list(journeys_path, "journeys")
    hashes = {path.name: hashlib.sha256(path.read_bytes()).hexdigest() for path in [*files, *([Path(events_path)] if events_path else []), *([Path(journeys_path)] if journeys_path else [])]}
    return {"dataset": dataset, "events": events, "journeys": journeys, "manifest": {"synthetic": True, "history_unknown_when_events_absent": not bool(events), "cutoff": DEMO_NOW, "input_hashes": hashes, "input_filenames": sorted(hashes), "entity_types": sorted(FIELDS)}}


__all__ = ["load_studio_input"]
