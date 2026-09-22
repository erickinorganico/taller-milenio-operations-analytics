# Arquitectura del toolkit analítico

## Alcance

Este repositorio produce un paquete reproducible de análisis y consultoría a partir de datos sintéticos. No es una aplicación, CRM, ERP, backend, frontend ni sistema de despacho. No expone servidor y no administra una operación en vivo.

```text
fixtures sintéticos o dataset.json validado
                    |
                    v
contratos, relaciones, estados e invariantes
                    |
                    v
snapshot SQLite + transformaciones deterministas
                    |
        +-----------+-----------+
        |           |           |
        v           v           v
  análisis     excepciones   propuestas
        |           |           |
        +-----------+-----------+
                    v
cuatro reportes + informe ejecutivo + charts
                    |
                    v
receipt.json con controles y hashes
```

## Componentes

- `milenio/fixtures.py`: casos sintéticos normales y problemáticos con IDs estables.
- contratos/modelo: entidades, campos, referencias, estados y grain. Los estados reconstruyen recorridos analíticos; no ejecutan operación.
- validación/importación: verifica archivos antes del análisis. La primera versión acepta únicamente datos sintéticos.
- SQLite: snapshot consultable y local para reconciliación; no es base operativa multiusuario.
- pipeline: valida, preserva fuentes, calcula análisis, genera propuestas read-only, renderiza salidas y escribe el recibo al final.
- reportes: cuatro lentes separados y un informe ejecutivo estático imprimible.
- evidencia: hallazgos y propuestas citan registros/controles locales; el recibo fija hashes SHA-256.

## Ejecución fail-closed

`run_pipeline(output, dataset)` recibe una ruta nueva y un dataset completo opcional. Debe rechazar un destino existente para evitar mezclar corridas. Escribe primero en staging; publica el directorio final y su recibo solo después de que validación, análisis, reports, reconciliaciones y hashing terminen. Un input inválido no deja un recibo completo.

El pipeline no muta el diccionario de entrada. Conserva `dataset.json` y CSV por entidad como snapshot fuente. Los hashes de contenido excluyen timestamps/logs de runtime no deterministas; por ello dos corridas con mismo código/input producen el mismo digest de contenido aunque sus rutas difieran.

## Contrato de salida

```text
artifacts/demo/
  dataset.json
  csv/<entidad>.csv
  milenio.sqlite
  analysis.json
  exceptions.json
  proposals.json
  timeline.json
  quality.json
  reports/
    particulares.md
    flotillas.md
    gruas.md
    administracion.md
    informe_ejecutivo.html
    charts/<PNG o SVG>
  receipt.json
```

`analysis.json` conserva definiciones, grain, cutoff, métricas y reconciliaciones. `quality.json` separa validez, completitud y límites. `exceptions.json` contiene hallazgos accionables con evidencia. `timeline.json` ordena hitos sin presentarlos como log productivo. `proposals.json` contiene borradores con `approval_required=true` y `external_execution=false`. El HTML es un documento, no una interfaz navegable.

## Semántica

- La demo solo admite el tiempo congelado `2026-09-21T18:00:00Z`; otro corte se rechaza para impedir una falsa apariencia de actualidad.
- Fechas: ISO-8601 con zona. Dinero: enteros en centavos MXN.
- Cotización, orden, factura, pago, costo/gasto, cuenta por cobrar y efectivo son hechos distintos.
- Compra ordenada no equivale a stock; reserva y consumo son movimientos diferentes.
- Oportunidad, propuesta, contrato y servicio cumplido no se intercambian.
- Solicitud, precio, asignación y despacho de grúa permanecen separados. El toolkit analiza registros; no decide seguridad o despacho.
- `unknown`, `review` y `blocked` nunca se convierten silenciosamente en cero.

## Seguridad y límites de confianza

No hay conectores de escritura, mensajería, pagos, fiscal, mapas, scraping ni despacho. Los hashes son tamper-evident, no tamperproof: un actor con acceso al equipo puede sustituir archivos y recalcular salidas. No existe autenticación porque no existe servicio compartido.

Los procesos, responsables, SLA, umbrales y datos capturables reales siguen sin validar. Los resultados son demostraciones sobre fixtures, nunca afirmaciones de desempeño real.

## Decisiones metodológicas

Python 3.12, SQLite y dependencias open source instaladas desde un wheelhouse local sostienen la ejecución offline después del setup inicial. Markdown, HTML estático y PNG/SVG hacen el paquete portable sin crear una aplicación. Las reglas deterministas gobiernan métricas y controles. Laya solo se evalúa, después de existir callers reales, para una clasificación repetida y cerrada en shadow con `REVIEW` y fallback; nunca para diagnóstico, precio, seguridad, despacho, contacto o dinero.

## Publicación

El repositorio público autorizado es `erickinorganico/taller-milenio-operations-analytics`. Solo se versionan código, documentación, fixtures inequívocamente sintéticos y artefactos de ejemplo revisados. Inputs reales, bases locales, secretos y exports sensibles quedan fuera de Git.
