"""Atomic, offline analytics builds with reproducible lineage and receipts."""
import copy
import hashlib
import json
import os
import platform
import shutil
import uuid
from pathlib import Path

from .agents import run_agents
from .analysis import analyze
from .contracts import DEMO_NOW, FIELDS, SCHEMA_VERSION
from .domain import require, validate_dataset
from .fixtures import make_fixture
from .importers import export_csv
from .presentation import render_reports
from .reports import bootstrap
from .storage import Store, digest
from .timeline import synthetic_history, validate_history
from .sql import create_views, query_snapshots


def write_json(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, sort_keys=True, ensure_ascii=False, allow_nan=False) + "\n", encoding="utf-8")


def file_hash(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def source_manifest():
    root = Path(__file__).resolve().parent.parent
    files = sorted(list((root / "milenio").glob("*.py")) + list((root / "contracts").glob("*.json")) + list((root / "queries").glob("*.sql")))
    for name in ("requirements.txt", "pyproject.toml"):
        if (root / name).exists():
            files.append(root / name)
    return {file.relative_to(root).as_posix(): file_hash(file) for file in files}


def run_pipeline(output, dataset=None, history=None, now=DEMO_NOW, input_hashes=None):
    """Build into a new directory. Invalid input never yields a success receipt.

    No mutation to source dictionaries/files. Exported JSON is the lossless adapter;
    CSV sheets deliberately neutralize formulas. Snapshot-only imports have unknown
    transition coverage unless an explicit synthetic history file is supplied.
    """
    output = Path(output).resolve()
    require(not output.exists(), "La salida ya existe: elija una carpeta nueva para conservar la evidencia")
    data = copy.deepcopy(make_fixture() if dataset is None else dataset)
    validate_dataset(data)
    history = copy.deepcopy(synthetic_history(data, now) if dataset is None and history is None else history or [])
    history_grade = validate_history(data, history, now)
    output.parent.mkdir(parents=True, exist_ok=True)
    # Inherit the destination directory's access policy. Windows Python creates
    # mkdtemp directories with owner-only ACLs, which survive a final rename and
    # prevent the desktop user from opening reports built by a sandbox identity.
    staging = (output.parent / (".milenio-build-" + uuid.uuid4().hex)).resolve()
    staging.mkdir(mode=0o755, exist_ok=False)
    store = None
    try:
        store = Store(staging / "milenio.sqlite")
        store.initialize(data)
        create_views(store)
        packet = bootstrap(store, now)
        require(packet["reconciliation"]["ok"], "Reconciliación fallida")
        analysis = analyze(data, now)
        analysis["meta"]["lifecycle_evidence"] = history_grade
        analysis["action_queue"] = packet["exceptions"]
        proposals, agent_grade = run_agents(data, now)
        write_json(staging / "dataset.json", data)
        write_json(staging / "timeline.json", history)
        write_json(staging / "analysis.json", analysis)
        write_json(staging / "proposals.json", proposals)
        write_json(staging / "exceptions.json", packet["exceptions"])
        write_json(staging / "audit.json", store.audit(limit=1_000_000))
        write_json(staging / "contracts.json", {"schema_version": SCHEMA_VERSION, "fields": FIELDS, "flows": packet["flows"]})
        csv_dir = staging / "csv"
        csv_dir.mkdir()
        for kind, rows in data.items():
            (csv_dir / (kind + ".csv")).write_text(export_csv(kind, rows), encoding="utf-8-sig", newline="")
        reports = render_reports(analysis, staging / "reports")
        require(all(Path(path).is_file() for path in reports), "Reporte incompleto")
        write_json(staging / "quality.json", {"status": "pass", "synthetic": True, "reconciliation": packet["reconciliation"],
                                              "history": history_grade, "agents": agent_grade,
                                              "record_counts": {k: len(v) for k, v in data.items()}})
        store.close()
        store = None
        sql_results = query_snapshots(staging / "milenio.sqlite")
        financial = sql_results["finance"][0]
        for field in ("invoiced_cents", "paid_cents", "receivable_cents", "cash_net_cents"):
            require(financial[field] == analysis["administracion"]["money"][field], "SQL y Python no reconcilian: " + field)
        write_json(staging / "sql_results.json", sql_results)
        files = {p.relative_to(staging).as_posix(): file_hash(p) for p in sorted(staging.rglob("*")) if p.is_file()}
        receipt = {"status": "pass", "schema_version": SCHEMA_VERSION, "synthetic": True, "as_of": now,
                   "data_sha256": digest(data), "input_sha256": input_hashes or {}, "artifacts_sha256": files, "source_sha256": source_manifest(),
                   "content_sha256": digest(files), "runtime": {"python": platform.python_version()},
                   "checks": {"domain": "pass", "audit": "pass", "reconciliation": "pass", "agents": "pass", "history": history_grade["status"]},
                   "publication_scope": "Synthetic outputs only. Real business discovery and pilot not validated."}
        write_json(staging / "receipt.json", receipt)
        staging.rename(output)
        return receipt
    finally:
        if store is not None:
            store.close()
        if staging.exists():
            # Delete only our freshly allocated staging directory, never user output.
            require(staging.parent == output.parent and staging.name.startswith(".milenio-build-"), "Ruta temporal insegura")
            shutil.rmtree(staging)


def verify_receipt(output):
    output = Path(output).resolve()
    receipt = json.loads((output / "receipt.json").read_text(encoding="utf-8"))
    require(receipt.get("status") == "pass" and receipt.get("synthetic") is True, "Recibo inválido")
    expected = receipt.get("artifacts_sha256", {})
    require(bool(expected), "Manifiesto vacío")
    actual = {p.relative_to(output).as_posix(): file_hash(p) for p in sorted(output.rglob("*")) if p.is_file() and p != output / "receipt.json"}
    require(actual == expected and digest(actual) == receipt.get("content_sha256"), "Hash de artefacto alterado o archivo faltante")
    return {"status": "pass", "artifacts": len(actual), "content_sha256": receipt["content_sha256"]}


def controlled_failure(output):
    """Deliberate impossible stock fixture; assert fail-closed with saved evidence."""
    output = Path(output).resolve()
    require(not output.exists(), "La salida ya existe")
    data = make_fixture()
    movement = next(r for r in data["stock_moves"] if r["move_type"] == "consume")
    movement["quantity"] = 1_000_000
    try:
        run_pipeline(output / "must-not-exist", data)
    except ValueError as exc:
        require(not (output / "must-not-exist").exists(), "Fallo dejó entrega parcial")
        output.mkdir(parents=True, exist_ok=False)
        result = {"status": "expected_failure_observed", "case": "stock_overconsumption", "error": str(exc),
                  "success_receipt_created": False, "synthetic": True, "input_sha256": digest(data)}
        write_json(output / "controlled_failure.json", result)
        return result
    raise AssertionError("Invalid stock unexpectedly accepted")
