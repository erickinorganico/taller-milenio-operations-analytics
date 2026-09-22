"""Batch analytics entrypoint. No HTTP or live operational command surface."""
import argparse
import json
import sys
from pathlib import Path


def main(argv=None):
    parser = argparse.ArgumentParser(description="Taller Milenio — Analítica local y revisión del cliente")
    sub = parser.add_subparsers(dest="command", required=True)
    template = sub.add_parser('client-template', help='Plantilla Excel para un extracto mínimo del cliente')
    template.add_argument('--output', required=True)
    template.add_argument('--sample', action='store_true')
    template.add_argument('--as-of', help='Corte ISO con zona horaria; obligatorio para muestra')
    template.add_argument('--business', default='')
    template.add_argument('--snapshot-id')
    client = sub.add_parser('client-analyze', help='Analizar Excel/CSV local; salidas de cliente sólo en private/')
    client.add_argument('--input', required=True)
    client.add_argument('--output', help='Carpeta nueva; por defecto private/clients/<id-fecha>')
    client.add_argument('--errors', help='Escribir errores de calidad en una ruta privada JSON')
    cr = sub.add_parser('client-review', help='Importar anotaciones humanas del libro de seguimiento')
    cr.add_argument('--input', required=True)
    cr.add_argument('--report', required=True)
    cr.add_argument('--reviewer', required=True)
    cc = sub.add_parser('client-compare', help='Comparar dos cortes sin asumir resueltos los registros ausentes')
    cc.add_argument('--before', required=True)
    cc.add_argument('--after', required=True)
    cc.add_argument('--output', required=True)
    cv = sub.add_parser('client-verify', help='Validar integridad de la entrega de cliente')
    cv.add_argument('--input', required=True)
    studio = sub.add_parser("studio", help="Entrega integrada con tablas físicas, procesos, agentes y Excel")
    studio.add_argument("--output", default="artifacts/workbench-v2")
    studio.add_argument("--days", type=int, default=90)
    studio.add_argument('--native', action='store_true', help='Ejecutar también los nueve agentes con la suscripción Codex autenticada')
    studio.add_argument('--input',help='Snapshot sintético JSON o carpeta completa de 25 CSV')
    studio.add_argument('--events',help='Historial validable JSON; omitir conserva cobertura desconocida')
    studio.add_argument('--journeys',help='Vínculos explícitos entre lead, cotización, cita y orden')
    studio_verify = sub.add_parser('verify-studio',help='Comprobar integridad de la entrega v2')
    studio_verify.add_argument('--input',required=True)
    agent = sub.add_parser("agent", help="Ejecutar un perfil de agente sobre un warehouse")
    agent.add_argument("--warehouse", required=True)
    agent.add_argument("--output", required=True)
    agent.add_argument("--id", required=True)
    agent.add_argument("--backend", choices=['rules','native_codex'], default='rules')
    agent.add_argument("--timeout", type=int, default=300)
    sub.add_parser("agents", help="Listar perfiles y herramientas de agentes")
    review = sub.add_parser("review", help="Registrar una revisión local; no ejecuta acciones externas")
    review.add_argument("--run", required=True)
    review.add_argument("--reviewer", required=True)
    review.add_argument("--decision", choices=['approved','rejected','needs_information'], required=True)
    review.add_argument("--note", required=True)
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
    if args.command.startswith('client-'):
        from .client_delivery import run_client_command
        return run_client_command(args)
    if args.command == 'studio':
        from .studio import build_studio
        print(json.dumps(build_studio(args.output,args.days,args.native,args.input,args.events,args.journeys),ensure_ascii=True))
        return 0
    if args.command == 'verify-studio':
        from .studio import verify_studio
        print(json.dumps(verify_studio(args.input)))
        return 0
    if args.command in ('agent','agents','review'):
        from .agent_runtime import prepare_agent_run, list_available_agents, record_review_decision
        if args.command == 'agents': result = list_available_agents()
        elif args.command == 'review': result = record_review_decision(args.run,args.reviewer,args.decision,args.note)
        else: result = prepare_agent_run(args.warehouse,args.output,args.id,args.backend,timeout_seconds=args.timeout)
        print(json.dumps(result,ensure_ascii=True))
        return 1 if isinstance(result,dict) and result.get('status') == 'blocked' else 0
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
