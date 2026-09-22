"""Batch analytics entrypoint. No HTTP or live operational command surface."""
import argparse
import json
import sys
from pathlib import Path


def main(argv=None):
    parser = argparse.ArgumentParser(description="Taller Milenio — Analytics sintético local")
    sub = parser.add_subparsers(dest="command", required=True)
    demo = sub.add_parser("demo", help="Genera y analiza la muestra sintética")
    demo.add_argument("--output", default="artifacts/demo")
    analysis = sub.add_parser("analyze", help="Analiza un snapshot JSON o una carpeta con 25 CSV sintéticos")
    analysis.add_argument("--input", required=True)
    analysis.add_argument("--history", help="JSON de eventos sintéticos explícitos")
    analysis.add_argument("--output", required=True)
    failure = sub.add_parser("controlled-failure")
    failure.add_argument("--output", default="artifacts/controlled-failure")
    verify = sub.add_parser("verify")
    verify.add_argument("--output", default="artifacts/verification.json")
    receipt = sub.add_parser("verify-receipt")
    receipt.add_argument("--input", required=True)
    ingest = sub.add_parser("import", help="CSV sintético hacia almacenamiento de preparación")
    ingest.add_argument("--entity", required=True, choices=["customers", "vehicles", "leads", "suppliers", "parts"])
    ingest.add_argument("--file", required=True)
    ingest.add_argument("--db", required=True)
    ingest.add_argument("--actor", default="Analista demo")
    export = sub.add_parser("export")
    export.add_argument("--db", required=True)
    export.add_argument("--output", required=True)
    args = parser.parse_args(argv)
    if args.command == "verify":
        from .verification import verify_project
        return verify_project(Path(args.output))
    if args.command in {"demo", "analyze", "controlled-failure", "verify-receipt"}:
        from .pipeline import run_pipeline, controlled_failure, verify_receipt
        if args.command == "demo":
            result = run_pipeline(args.output)
        elif args.command == "analyze":
            from .pipeline import file_hash
            from .snapshot_io import load_snapshot
            source = Path(args.input)
            if source.is_dir():
                data = load_snapshot(source)
                from .contracts import FIELDS
                inputs = {kind + '.csv': file_hash(source / (kind + '.csv')) for kind in FIELDS}
            else:
                data = json.loads(source.read_text(encoding="utf-8-sig"))
                inputs = {'dataset.json': file_hash(source)}
            history = json.loads(Path(args.history).read_text(encoding="utf-8-sig")) if args.history else None
            if args.history:
                inputs['history.json'] = file_hash(args.history)
            result = run_pipeline(args.output, data, history, input_hashes=inputs)
        elif args.command == "controlled-failure":
            result = controlled_failure(args.output)
        else:
            result = verify_receipt(args.input)
        print(json.dumps({"status": result["status"], "output": getattr(args, "output", getattr(args, "input", None)),
                          "content_sha256": result.get("content_sha256"), "synthetic": True}, ensure_ascii=True))
        return 0
    from .storage import Store
    from .domain import require
    if args.command == "export":
        require(Path(args.db).is_file(), "Almacenamiento de origen inexistente")
    if args.command == "import":
        require(not (Path(args.db).parent / "receipt.json").exists(), "Use una base de preparación fuera de las entregas con recibo")
    store = Store(args.db)
    try:
        if args.command == "import":
            from .importers import apply_csv
            result = apply_csv(store, args.entity, Path(args.file).read_text(encoding="utf-8-sig"), args.actor)
            print(json.dumps(result, ensure_ascii=True))
            return 0 if result["ok"] else 1
        require(store.verify_audit(), "Auditoría de origen alterada")
        output = Path(args.output)
        output.parent.mkdir(parents=True, exist_ok=True)
        with output.open("x", encoding="utf-8") as file:
            json.dump(store.data(), file, ensure_ascii=False, indent=2, sort_keys=True)
        print(json.dumps({"status": "pass", "output": str(output), "synthetic": True}))
        return 0
    finally:
        store.close()


if __name__ == "__main__":
    try:
        sys.exit(main())
    except (ValueError, OSError) as exc:
        print("Error: " + str(exc), file=sys.stderr)
        sys.exit(1)

