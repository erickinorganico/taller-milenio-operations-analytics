# Taller Milenio Operations & Growth Analytics

Toolkit local de Analytics y consultoría agentic para modelar recorridos de particulares, flotillas y grúas; analizar seguimiento, capacidad, servicio, inventario, SLA y cobranza; y producir recomendaciones con evidencia y aprobación humana.

**Todo resultado inicial es sintético.** El proceso real de Taller Milenio no ha sido validado. Este repositorio no es una app, CRM, ERP, frontend/backend ni sistema de despacho. No envía mensajes, diagnostica, fija precios, despacha, factura fiscalmente o mueve dinero.

English: [README.en.md](README.en.md).

## Inicio rápido

Requiere Python 3.12+. La primera instalación en línea descarga y conserva las dependencias; después, la demo funciona sin red.

```powershell
py -3 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -e .
.\.venv\Scripts\python.exe -m milenio demo --output artifacts/demo
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

La demo solo admite el corte congelado `2026-09-21T18:00:00Z`; otro corte se rechaza para evitar resultados que aparenten actualidad. Métricas, umbrales y SLA son supuestos de prueba. No publique inputs, bases, secretos o datos reales.

Repositorio público autorizado: `erickinorganico/taller-milenio-operations-analytics`. Licencia MIT.
