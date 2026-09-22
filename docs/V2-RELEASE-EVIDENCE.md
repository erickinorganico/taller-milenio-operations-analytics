# Evidencia de entrega V2

Validación del 22 de septiembre de 2026. El corte analítico permanece en `2026-09-21T18:00:00Z` y todos los datos de negocio son sintéticos.

| Superficie | Resultado comprobado | Evidencia |
|---|---|---|
| Pruebas locales | 101 ejecutadas, 100 aprobadas, 1 omitida por permisos de symlink Windows; cero fallas/errores | `artifacts/v2-verification.json` y XML |
| Instalación offline | Entorno Python 3.12 nuevo, dependencias fijadas instaladas exclusivamente desde wheels locales | `Setup.ps1 -Offline`; suite completa ejecutada en ese entorno |
| Almacén | 27 tablas fuente STRICT, 6 marts; DDL recrea las 33 tablas | `schema.sql`, `catalog.json`, `delivery_validation.json` |
| Reanálisis | Snapshot JSON + eventos + journeys exportados reproducen exactamente los seis marts | `studio --input ... --events ... --journeys ...` |
| Excel | 36 hojas, 6 fórmulas recalculadas en Excel, cero errores; conciliación financiera en cero | `workbook_check.json` |
| Agentes | 9 roles, 18 turnos nativos finales, modelo configurado `gpt-5.6-luna`, sin acciones externas | `native_verification.json`, `native_runs/*` |
| Procesos y especificaciones | 6 mapas/SOP, 5 specs, 18 requisitos con referencias verificadas | `processes/`, `specs/`, pruebas de grafo y trazabilidad |
| Presentación | 9 agentes visibles, gráficos cargados, sin desbordamiento a 390 px | `previews/` y `delivery_validation.json` |
| Integridad | Manifest de todos los archivos y hash del contenido; prueba negativa detecta alteraciones | `receipt.json`; `verify-studio` |

La integración de Windows y Ubuntu se conserva en [los controles de la revisión V2](https://github.com/erickinorganico/taller-milenio-operations-analytics/pull/1/checks). CI genera una entrega independiente con reglas y verifica la entrega publicada; no simula llamadas nativas ni necesita autenticación del usuario.

La revisión independiente corrigió continuidad y extremos del historial, tipado SQL, relojes con distintos offsets, consistencia de SLA y límites del contrato de agentes. La revisión de respuestas reales corrigió selección de pagos por factura, alcance de flotillas, corte temporal y denominadores de muestra. Las recomendaciones siguen pendientes de revisión humana: no se registraron aprobaciones ficticias.

`DECISIONES.md` y `review_queue.csv` convierten los resultados en material revisable. La conciliación usa 164 facturas emitidas y 56 con saldo; la muestra de cobranza contiene seis facturas, dos con pago parcial. La muestra y el universo se identifican por separado.

La entrega acredita capacidad técnica y un mecanismo reproducible. La validación del proceso real, el piloto con datos autorizados, la adopción y el impacto comercial permanecen fuera de esta evidencia sintética.
