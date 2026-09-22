# Taller Milenio · Workbench analítico V2

Entrega local y reproducible para revisar operación, crecimiento y control gerencial con evidencia. El punto de entrada es el [dossier V2](artifacts/workbench-v2/DOSSIER.html): conecta tablas SQL, seis procesos, métricas longitudinales, un libro Excel y nueve perfiles de agentes con revisión humana.

> **Datos sintéticos.** Los 90 días, 170 órdenes, 160 historias vinculadas, importes, SLA y resultados fueron fabricados para probar el mecanismo. No describen la operación real de Taller Milenio ni demuestran impacto comercial. Los procesos son hipótesis aún no validadas mediante entrevistas.

[English version](README.en.md) · [Inventario de entrega](ENTREGA-MILENIO.md) · [Recorrido práctico](docs/V2-WALKTHROUGH.md)

## Qué se entrega

| Superficie | Contenido verificable |
|---|---|
| Dossier | `DOSSIER.html`, navegación local imprimible con decisiones, tablas, procesos y evidencia |
| Libro | `Milenio_Analisis.xlsx`, 36 hojas: portada, 33 tablas, catálogo de agentes y catálogo de procesos |
| SQL | `warehouse.sqlite` con 33 tablas físicas: 25 entidades, `lifecycle_events`, `journey_links` y seis marts |
| Procesos | seis definiciones JSON, seis mapas SVG y seis SOP con decisiones, excepciones, RACI y aceptación |
| Especificación | cinco contratos normativos y 18 requisitos trazables a proceso, entidad, agente, métrica y prueba |
| Agentes | nueve perfiles de revisión; modo reproducible `rules` y modo opt-in `native_codex` en dos etapas |
| Decisiones | `DECISIONES.md` y `review_queue.csv`, con propuestas pendientes y campos humanos vacíos |
| Evidencia | CSV por tabla, catálogo, DDL, análisis, replay de procesos, checks del libro y recibo con hashes |

Las seis vistas analíticas son `mart_service_journey`, `mart_receivables`, `mart_daily_operations`, `mart_fleet_scorecard`, `mart_inventory` y `mart_process_waits`.

La suite integrada actual pasa sin fallas ni errores; el conteo exacto pertenece al recibo de verificación del mismo estado fuente para evitar cifras congeladas. Excel COM abrió y recalculó las 36 hojas: seis fórmulas, cero errores y conciliación con SQL.

El corte de datos permanece fijo en `2026-09-21T18:00:00Z`. Las ejecuciones nativas ocurrieron el 2026-09-22 y no adelantan, reescriben ni hacen actuales los datos del escenario.

## Generar el workbench

Requiere Python 3.12+.

Windows:

```powershell
.\Setup.ps1
.\Run-Studio.cmd
```

Linux:

```bash
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
.venv/bin/python -m milenio studio --output artifacts/workbench-v2 --days 90
```

`Run-Studio.cmd` abre primero el dossier existente en `artifacts/workbench-v2`. Si todavía no existe, genera esa entrega; al terminar, ejecute el launcher otra vez o abra `DOSSIER.html`. Para conservar la entrega publicada y construir otra, use una carpeta nueva:

```powershell
.\.venv\Scripts\python.exe -m milenio studio --output artifacts/workbench-review-02 --days 90
```

`studio` nunca sobrescribe una carpeta proporcionada. La construcción usa staging y solo publica la carpeta final cuando SQL, marts, agentes base, libro y artefactos terminan correctamente.

### Reanalizar una entrada sintética

La entrega exporta `dataset.json`, `events.json` y `journeys.json`. Puede reproducirlos en una ruta nueva:

```powershell
.\.venv\Scripts\python.exe -m milenio studio `
  --input artifacts/workbench-v2/dataset.json `
  --events artifacts/workbench-v2/events.json `
  --journeys artifacts/workbench-v2/journeys.json `
  --output artifacts/reanalisis
```

También admite una carpeta completa de 25 CSV sintéticos:

```powershell
.\.venv\Scripts\python.exe -m milenio studio `
  --input artifacts/demo/csv `
  --output artifacts/reanalisis-csv
```

Sin `--events` ni `--journeys`, el workbench genera sus 36 hojas pero conserva historia y atribución como `unknown`; no inventa transiciones o enlaces. Este adaptador acepta solo el contrato sintético y el corte fijo `DEMO_NOW`, no datos de producción.

## Recorrido de cinco minutos

1. Abra `artifacts/workbench-v2/DOSSIER.html` y revise las secciones de operación, cartera, flotillas, inventario, procesos y agentes.
2. Abra `Milenio_Analisis.xlsx`: la hoja `INICIO` concilia facturado, cobrado y saldo; las otras 33 hojas permiten filtrar el dato físico.
3. Busque `WO-003` en `work_orders`: es una orden sintética `waiting_parts`, bloqueada por `Falta filtro`, sin QC ni asignación. Compárela con su replay y con el mart de servicios.
4. Abra un mapa en `processes/*.svg` y su SOP homólogo `.md`; el JSON es la definición autoritativa para validación y visualización, no un motor BPMN operativo.
5. Revise `receipt.json` y `workbook_check.json` antes de usar cualquier conclusión.
6. Abra [DECISIONES.md](artifacts/workbench-v2/DECISIONES.md) y [review_queue.csv](artifacts/workbench-v2/review_queue.csv): todas las propuestas empiezan `pending`; los campos de decisión humana están vacíos, sin aprobación fabricada.

El recorrido completo está en [docs/V2-WALKTHROUGH.md](docs/V2-WALKTHROUGH.md).

## Mesa de agentes

Liste los nueve perfiles y sus límites:

```powershell
.\.venv\Scripts\python.exe -m milenio agents
```

La línea base local no invoca un modelo:

```powershell
.\.venv\Scripts\python.exe -m milenio agent `
  --warehouse artifacts/workbench-v2/warehouse.sqlite `
  --output artifacts/agent-runs/operations-rules `
  --id operations_controller `
  --backend rules
```

El modo `native_codex` es opt-in y usa la CLI oficial fijada en `0.155.1` con la cuenta Codex ya autenticada, sin API de pago. `Setup-Agents.ps1` instala ese runtime por separado y define `MILENIO_CODEX_BIN` para la terminal actual:

```powershell
.\Setup-Agents.ps1
.\.venv\Scripts\python.exe -m milenio agent `
  --warehouse artifacts/workbench-v2/warehouse.sqlite `
  --output artifacts/agent-runs/operations-native `
  --id operations_controller `
  --backend native_codex `
  --timeout 300
```

La ejecución hace dos etapas: selección acotada de evidencia y métricas, seguida por diagnóstico, alternativas y borradores para revisión. Los nueve perfiles completaron este recorrido mediante la CLI oficial: 18 eventos `turn.completed`, recibos finales `verified_two_stage_local_cli` y cero acciones externas. Esto verifica ejecución y controles, no efectividad. La revisión detectó evidencia no relacionada y una pregunta de conciliación innecesaria en la salida de cobranza; su corrección y rerun están pendientes.

Para construir una entrega nueva que ejecute los nueve perfiles nativos, use `Setup-Agents.ps1` y después `python -m milenio studio --native --output <carpeta-nueva>`. Es una acción opt-in y puede tardar; nunca se activa en silencio.

Registrar una decisión local no ejecuta acciones externas:

```powershell
.\.venv\Scripts\python.exe -m milenio review `
  --run artifacts/agent-runs/operations-native `
  --reviewer "Responsable de taller" `
  --decision needs_information `
  --note "Confirmar disponibilidad real de la pieza antes de decidir."
```

## Qué puede decidir y qué no

El workbench ayuda a revisar WIP, esperas, cartera, SLA elegible, inventario y siguientes preguntas. No contacta clientes, agenda, despacha grúas, compra partes, fija precios, emite documentos fiscales, cambia estados de negocio o mueve dinero. Las propuestas y aprobaciones son artefactos internos de revisión.

Para crecimiento, consulte [docs/GROWTH-RESEARCH.md](docs/GROWTH-RESEARCH.md): propone investigación con fuentes oficiales y un puntaje de calificación, sin convertir el estrato de personal ocupado del DENUE en tamaño de flotilla ni fabricar contactos o leads.

## Documentación V2

- [Inventario y criterios de aceptación](ENTREGA-MILENIO.md)
- [Recorrido práctico del workbench](docs/V2-WALKTHROUGH.md)
- [Investigación de crecimiento](docs/GROWTH-RESEARCH.md)
- [Eficiencia del proyecto](docs/PROJECT-EFFICIENCY.md)
- [Modelo físico](docs/DATA-MODEL.md), [runtime de agentes](docs/AGENT-RUNTIME.md) y [replay de procesos](docs/PROCESS-MINING.md)
- [Procesos](processes/) y [especificaciones](specs/)

## V1 histórico

La entrega batch V1 permanece como referencia de compatibilidad y pruebas (`demo`, `analyze`, reportes Markdown/HTML). No es la entrada principal. V2 añade tablas físicas tipadas, historia explícita, marts, mapas, especificaciones, libro Excel y workbench de agentes.

Repositorio público autorizado: `erickinorganico/taller-milenio-operations-analytics`. Licencia MIT.
