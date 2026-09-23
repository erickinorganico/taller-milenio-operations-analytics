# Evidencia de entrega · Milenio V5

Corte local: 22 de septiembre de 2026. Alcance: aplicación local Windows, datos sintéticos/desechables (sin datos de clientes), código y paquete candidato. La aceptación operativa con un taller real no se ha realizado.

## Resultado comprobado

| Comprobación | Resultado observado | Evidencia |
| --- | --- | --- |
| Suite operacional completa | 70 pruebas, 0 errores, 0 fallos y 0 omisiones; dependencias fijadas coinciden; check/migraciones sin cambios | `artifacts/v5-verification.json` y `.xml`; `scripts/verify_web.py` |
| Regresión del toolkit V1–V4 | 162 pruebas, 0 errores/fallos y 2 omisiones; scanner de publicación pasa | `artifacts/v5-legacy-verification.json`; no prueba inferencia nativa V5 |
| Recorrido HTTP persistente | Recepción, inspección, presupuesto, autorización, partes, trabajo, calidad, entrega, comprobante y pago parcial | Total 626.40, pago 100, saldo 526.40; test_web.py |
| Autorización de acceso | Técnico limitado a órdenes/fotos/tareas propias; CSV/finanzas generales negados; consulta gerencial sin escrituras; CSRF probado | test_web.py y test_domain.py |
| Importación CSV | Plantilla, vista previa sin escritura, confirmación atómica, sesión/firma/vigencia, límites y duplicados | 6 pruebas en test_import.py |
| Agentes | Reglas persistidas, propuestas vigentes, tareas únicas, pagos nuevos invalidan evidencia, resultado y nueva comprobación | 17 pruebas en test_intelligence.py; recorrido de navegador |
| Datos y métricas | 24 tablas del dominio y 18 definiciones calculadas desde ORM, cobertura/desconocido, fuentes navegables | docs/V5-DATOS.md y V5-METRICAS.md, generados desde código |
| Restauración aislada | Conteos y saldo 1000−300=700, media, secreto destino preservado, sesiones purgadas y copia del estado anterior | test_restore_into_separate_instance_preserves_counts_and_partial_balance |
| Navegador real local | Orden autorizada y en trabajo conservada tras reinicio; 18 métricas, 24 fuentes, cotización imprimible y tarea completa | Observación con Codex browser sobre `127.0.0.1:8766`, 22/09/2026 |
| Diseño móvil | Orden a 390×844; ancho de documento 375 igual al viewport 375, sin desbordamiento global | Captura e inspección DOM después de corregir mínimos de grilla; no ensayo en dispositivo físico |

## Recorrido visual de propuestas

Sobre la demo, una revisión de operación/cobranza/calidad creó una propuesta por orden sin responsable y otra por saldo pendiente. Se aceptó la primera, se creó una tarea, se asignó responsable y vencimiento, se corrigió el responsable de WO-DEMO-2 desde su formulario, y se cerró la tarea con resultado explícito. Todo quedó persistido en la misma instalación. El modo se mostró como **Reglas verificables**, con **Modelo invocado: No**. No se contactó a ningún cliente.

## Instalador y paquete

El paquete usa una lista de archivos permitidos y manifiesto SHA-256, excluyendo bases, media y secretos. Las seis ruedas oficiales corresponden a CPython 3.12 / Windows x64. El ensayo completado instaló seis dependencias con `PIP_NO_INDEX=1`; el Python del entorno nuevo pasó imports y Django setup. La migración/semilla/respaldo/restauración usó el intérprete del repositorio sobre código extraído: 24 conteos idénticos, comprobantes 1102.00, pagos 300.00 y saldo 802.00 conservados, media con hashes idénticos y sesiones purgadas. El ensayo offline y la restauración con esquema completo se documentan en `artifacts/v5-installation-rehearsal.json`; el hash del ZIP final va en su recibo de paquete. Esos recibos deben leerse por separado de la suite: instalar dependencias no acredita por sí solo que el servidor arrancó.

## Pendientes explícitos

**AGT-03: inferencia nativa real.** El adaptador de Codex CLI existe, elimina claves/endpoint de APIs pagadas del proceso hijo, limita herramientas y valida salida/evidencia. La CLI local 0.155.1 respondió `Not logged in`; no hubo una inferencia V5 real. Las pruebas con mocks no cierran este requisito. Se necesita iniciar sesión personalmente en la CLI y ejecutar una revisión nativa sobre la demo. El modo por reglas está disponible sin esa dependencia.

**Aceptación con cliente.** No hay entrevista/observación de un taller, datos reales conciliados, adopción, impacto económico ni aceptación de soporte. La instancia de una estación escucha en loopback. Acceso desde teléfonos/equipos de una red, alojamiento, HTTPS, carga simultánea, retención y operación de respaldo requieren configurar y validar el entorno destino. No se presenta como SaaS multiempresa ni despliegue público.

**Integraciones excluidas.** No CFDI, banco, mensajería/telefonía, pagos en línea, compra externa, telemetría ni despacho/diagnóstico automático. Se emiten documentos administrativos y se registran hechos declarados por personas. La impresión visual está probada; no se realizó envío a una impresora física.

La verificación GSD mantiene AGT-03 pendiente y no declara el hito completo por tener documentación o tests verdes. Los planes, resúmenes y reporte independiente están en `.planning/`.

Se corrigió la validación del entorno del lanzador para reconocer entornos virtuales Linux por `sys.prefix`, y CI crea su propio `.venv`. La misma suite comprueba fuentes/operación en la matriz Windows y Ubuntu; el resultado remoto se consulta en GitHub y no se presume a partir de la ejecución local.
