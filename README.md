# Taller Milenio Operations & Growth Analytics

Toolkit turnkey, local y de solo lectura para Analytics y consultoría: modela recorridos de particulares, flotillas y grúas; analiza seguimiento, capacidad, servicio, inventario, SLA y cobranza; y produce recomendaciones con evidencia y aprobación humana.

**Todo resultado inicial es sintético.** El proceso real de Taller Milenio no ha sido validado. Este repositorio no es una app, CRM, ERP, frontend/backend ni sistema de despacho. No envía mensajes, diagnostica, fija precios, despacha, factura fiscalmente o mueve dinero.

English: [README.en.md](README.en.md).

## Entrega lista para revisar

- [Descargar la versión y el paquete offline para Windows](https://github.com/erickinorganico/taller-milenio-operations-analytics/releases/latest)
- [Informe de ejemplo](artifacts/demo/reports/administracion.md), [cola de revisión](artifacts/demo/reports/cola_revision.md) y [recibo verificable](artifacts/demo/receipt.json)
- [Oferta de consultoría](docs/OFERTA-CONSULTORIA.md), [playbook del cliente](docs/CLIENT-PLAYBOOK.md) y [plantillas editables](examples/consulting/)
- [Pruebas automáticas en Windows y Linux](https://github.com/erickinorganico/taller-milenio-operations-analytics/actions)

El ZIP incluye código, reportes HTML/Markdown, SQLite, CSV y dependencias para Python 3.12 en Windows x64. Extraiga el ZIP, entre a `source/` y ejecute `Setup.ps1 -Offline`; Python debe estar instalado. Abra `artifacts/demo/reports/informe_ejecutivo.html` para revisar el ejemplo o use `Run-Demo.cmd` para generar una corrida nueva.

## Inicio rápido

Requiere Python 3.12+.

Windows:

```powershell
.\Setup.ps1
.\.venv\Scripts\python.exe -m milenio demo --output artifacts/my-demo
```

Linux:

```bash
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
.venv/bin/python -m milenio demo --output artifacts/my-demo
```

Para probar una instalación limpia sin red después de preparar el wheelhouse:

```powershell
.\Setup.ps1 -Offline -EnvironmentPath .runtime/clean-env
```

La corrida genera:

- `dataset.json`, snapshot SQLite y CSV por entidad;
- análisis, calidad, excepciones y timeline en JSON;
- reportes separados de particulares, flotillas, grúas y administración;
- `reports/informe_ejecutivo.html` y charts PNG/SVG;
- `proposals.json` con evidencia, aprobación requerida y sin ejecución externa;
- `receipt.json` con controles, conteos y hashes.

## Reanalizar los CSV exportados

La demo produce un directorio CSV completo que puede volver a entrar al pipeline:

```powershell
.\.venv\Scripts\python.exe -m milenio analyze --input artifacts/demo/csv --output artifacts/from-csv
```

Use una ruta de salida nueva. El importador exige el conjunto contractual completo y conserva cobertura histórica como `unknown` cuando los CSV no contienen un historial validado.

## Verificar

```powershell
.\.venv\Scripts\python.exe -m milenio verify --output artifacts/verification.json
```

Los tests trabajan sin red ni producción. Una corrida verde verifica el mecanismo con ese input; no prueba resultados reales del taller.

## Cuatro lentes

- **Particulares:** conversión, citas, seguimiento, autorización, entrega/retrabajo y recurrencia.
- **Flotillas:** pipeline vs. contrato, mantenimiento, downtime, SLA, facturación y cobranza.
- **Grúas:** recorrido, tiempos registrados, gates humanos y excepciones; nunca decide seguridad/despacho.
- **Administración:** capacidad, trabajo detenido, inventario, costos/gastos, factura, pago, saldo y efectivo separados.

## Documentación

- [Proceso sintético e entrevistas](docs/PROCESS.md)
- [Plan y E2E](docs/PLAN.md)
- [Arquitectura batch](docs/ARCHITECTURE.md)
- [Runbook](docs/RUNBOOK.md)
- [Ruta a exports reales](docs/REAL-DATA.md)

La demo solo admite el corte congelado `2026-09-21T18:00:00Z`; otro corte se rechaza para evitar resultados que aparenten actualidad. Métricas, umbrales y SLA son supuestos de prueba. El toolkit puede servir como muestra comercial de un servicio de consultoría, pero no demuestra despliegue, adopción o resultados reales. No publique inputs, bases, secretos o datos reales.

Repositorio público autorizado: `erickinorganico/taller-milenio-operations-analytics`. Licencia MIT.
