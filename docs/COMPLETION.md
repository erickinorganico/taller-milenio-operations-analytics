# Cierre de la versión 1.0.0

El alcance del handoff quedó implementado como toolkit analítico y paquete de consultoría reproducible. El proceso y los datos del ejemplo son sintéticos; no se realizó un piloto con la operación real de Taller Milenio.

## Entregables

| Área | Entrega revisable |
|---|---|
| Modelo integrado | 25 entidades, 112 registros sintéticos, contratos, SQLite y CSV |
| Taller y partes | Estados auditables, capacidad instantánea, órdenes detenidas, consumo/devolución y reconciliación |
| Particulares | Estado de leads, cotizaciones, citas, seguimiento y cobertura de consentimiento |
| Flotillas | Pipeline comercial, contratos, cobertura, mantenimiento, downtime y SLA elegible |
| Grúas | Recorrido, tiempos observables y referencias de revisión humana |
| Administración | Cotización, factura, pago, cuentas por cobrar, gasto, piezas y efectivo separados |
| Reportes | Cinco informes de dominio, cola de revisión, HTML imprimible y cinco gráficas en PNG/SVG |
| Agentes | Nueve asistentes deterministas, 18 propuestas con evidencia, aprobación requerida y sin ejecución externa |
| Consultoría | Oferta en español, playbook, discovery, diccionario, checklist de datos, seguimiento y aceptación |
| Distribución | Código MIT, ejemplo completo, manifiesto SHA-256 y wheels para Windows x64/Python 3.12 |

## Evidencia de aceptación

- `artifacts/final-verification.json` y XML: 50 pruebas descubiertas; 49 aprobadas y una omitida en este Windows por ausencia de permisos para crear enlaces simbólicos. Cero fallos/errores. La omisión es visible, no se cuenta como aprobación.
- `artifacts/demo/receipt.json`: manifiesto de 52 artefactos, reconciliaciones y hashes del código analítico. Los hashes de código se compararon también con los objetos publicados en Git.
- `artifacts/controlled-failure/controlled_failure.json`: sobreconsumo imposible rechazado, sin entrega parcial ni recibo de éxito.
- Exportación/reingestión de las 25 tablas CSV: aprobada; se conservan hashes de los archivos de entrada y la historia queda `unknown` sin eventos suministrados.
- Instalación nueva mediante `Setup.ps1 -Offline`, usando exclusivamente el wheelhouse local: aprobada.
- ZIP extraído sin `.git`, instalación nueva y verificación completa: aprobadas. La demo reconstruida produjo el mismo hash de contenido `b76d54e815fc6fd6631703ec807ace28a87b8d0b1f744df7f836738ef5e8b1fc`.
- Revisión Astra: 9 hallazgos analíticos y 5 de empaquetado corregidos; ver `ADVERSARIAL-REVIEW.md` y sus regresiones.
- El CI ejecuta instalación, pruebas, demo, reingestión CSV, verificación del ejemplo publicado y fallo controlado en Windows/Ubuntu. La ejecución [35704667360](https://github.com/erickinorganico/taller-milenio-operations-analytics/actions/runs/35704667360) aprobó ambos sistemas sobre `ea42a0d`.

La prueba del ZIP usó el mismo código analítico y dependencias que la entrega; ajustes posteriores en documentos y normalización de rutas se verificaron con sus pruebas afectadas y CI. El manifiesto del ZIP identifica los bytes exactos distribuidos. Python 3.12 debe estar instalado; las dependencias de terceros se distribuyen como wheels con sus metadatos y avisos de licencia originales.

## Uso inmediato

1. Extraer el ZIP y abrir `source/`.
2. Abrir `artifacts/demo/reports/informe_ejecutivo.html` para revisar el ejemplo sin instalar nada.
3. Para ejecutar: instalar Python 3.12, correr `Setup.ps1 -Offline` y `Run-Demo.cmd`.
4. Usar la cola de revisión junto con `examples/consulting/decision-action-tracker.csv`.
5. Adaptar `OFERTA-CONSULTORIA.md` para presentar un diagnóstico y acordar un piloto futuro.

## Límite comercial

El paquete permite mostrar una metodología, reproducir análisis y estructurar una oferta de consultoría. No demuestra demanda de mercado, adopción, rentabilidad ni mejoras reales del taller. La entrevista, validación de definiciones y un piloto con exports reales requieren un alcance separado; `REAL-DATA.md` detalla los cambios técnicos y de gobierno necesarios. La aceptación de esta versión sintética está registrada en `artifacts/completion.json`.
