# Runbook del toolkit analítico

## Setup

Requiere Python 3.12+ en Windows. La instalación inicial necesita red para resolver/descargar dependencias y preparar el wheelhouse local. Después de esa preparación, la demo no necesita internet, cuentas ni credenciales.

```powershell
py -3 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -e .
```

Prueba de setup limpio offline con las ruedas ya preparadas:

```powershell
.\Setup.ps1 -Offline -EnvironmentPath .runtime/clean-env
```

El modo offline debe fallar claramente si falta una rueda; no debe consultar internet como fallback.

## Demo completa

```powershell
.\.venv\Scripts\python.exe -m milenio demo --output artifacts/demo
```

El destino debe ser nuevo. La corrida genera `dataset.json`, CSV por entidad, SQLite, análisis, excepciones, timeline, calidad, propuestas, cuatro reportes, informe HTML, charts y recibo. No mezcle archivos de corridas distintas.

## Analizar un dataset preparado

```powershell
.\.venv\Scripts\python.exe -m milenio analyze --input path\to\dataset.json --output artifacts\analysis-run
```

La primera versión admite solo datos sintéticos. El dataset debe contener todas las entidades contractuales. Un contrato roto falla; faltantes analíticos permitidos permanecen `unknown/review` según la definición.

## Verificar y probar el fallo controlado

```powershell
.\.venv\Scripts\python.exe -m milenio verify --output artifacts/verification.json
.\.venv\Scripts\python.exe -m milenio controlled-failure --output artifacts/controlled-failure
```

`verify` ejecuta pruebas offline e informa código distinto de cero ante fallos. `controlled-failure` demuestra rechazo sin recibo completo. Nunca use un recibo verde anterior para describir código/input nuevo.

## Revisión de una corrida

1. Abra `receipt.json`; confirme status, reloj, versión, conteos, reconciliaciones y hashes.
2. Revise `quality.json` y `analysis.json` antes de interpretar conclusiones.
3. Compare `exceptions.json` y `proposals.json`; toda propuesta debe citar evidencia y requerir aprobación.
4. Lea por separado los cuatro Markdown.
5. Abra/imprima `reports/informe_ejecutivo.html`.
6. Confirme que charts y tablas usan el mismo grain/definición.
7. Trate toda cifra como sintética; el reloj congelado no es estado actual.

La versión inicial solo soporta `2026-09-21T18:00:00Z`. Solicitar otro corte debe fallar, porque recalcular con un `now` arbitrario podría aparentar actualidad sin una fuente real.

## Estados de evidencia

- `measured`: calculado desde esa corrida.
- `unknown`: falta evidencia necesaria; no equivale a cero.
- `review`: ambigüedad o decisión humana requerida.
- `blocked`: un control impide formar una conclusión responsable.
- `synthetic`: demostración, no dato de Taller Milenio.

## Fallos comunes

| Falla | Respuesta |
|---|---|
| referencia/ID inválido | corrija la fuente; no descarte filas silenciosamente |
| fecha sin zona | declare fuente/zona y regenere |
| dinero decimal | transforme a centavos enteros en un adaptador probado |
| stock negativo | investigue movimientos; no fuerce disponibilidad |
| factura/pago no reconcilian | preserve saldo como review/blocked |
| SLA sin término/clock | no calcule cumplimiento |
| grúa sin evidencia humana | registre gate faltante; no concluya que puede despacharse |
| destino existente | elija ruta nueva; el pipeline protege artefactos previos |
| corrida interrumpida | retire staging incompleto y repita |
| hash distinto | trate input/código/salida como ejecución diferente |

## Conservación

Archive el directorio completo con `receipt.json`; conservar solo HTML pierde trazabilidad. Mantenga `artifacts/`, inputs, SQLite y exports reales fuera de Git salvo ejemplos sintéticos deliberadamente revisados.

Una corrida verde evidencia que el mecanismo local funcionó con ese input. No prueba salud operacional, adopción, causalidad, seguridad vial, contabilidad fiscal ni desempeño real.
