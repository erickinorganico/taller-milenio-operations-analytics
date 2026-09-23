---
plan: 07-01
status: complete_local
requirements-completed: [AUT-01, AUT-02, AUT-03, AUT-04, AGT-04, AGT-05]
---

# Automatizaciones y agentes — ejecución

`workshop/automation.py` crea trabajos persistentes por intervalo y eventos AuditEvent, con deduplicación, pausa, intentos acotados, lease renovable y recuperación. `run_automations.py` es el proceso trabajador hijo lanzado por `scripts/run_web.py`; el estado y controles se ven en `/automations/`. Reglas son predeterminadas; modo nativo automático requiere habilitación local y decisión de Gerencia. Un trabajo nativo interrumpido no se reintenta a ciegas.

El ciclo guarda corte, corridas de agentes y propuestas con evidencia; la revisión y las tareas humanas V5 conservan su comprobación de vigencia. El corte se toma antes de las corridas de agentes: si aparecen eventos auditados después, el trabajo registra y muestra el avance del cursor, sin afirmar lectura simultánea. Semántica y límites: `docs/V6-AUTOMATIZACIONES.md` y `.planning/V6-INTEGRATION-REVIEW.md`.

Las pruebas de `test_automation.py` cubren intervalo/evento, pausa, modo opt-in, deduplicación, lease, latido, reintentos, error parcial y ambigüedad nativa. `artifacts/v6-browser-verification.json` registra un trabajo de intervalo y uno por cambio de negocio, un trabajo retenido en pausa por dos minutos y completado al reanudar; `artifacts/v6-worker-restart.json` registra que, al detener el servidor PID 16672, el trabajador PID 16864 no sobrevivió.

`artifacts/v6-native-verification.json` acredita el trabajo nativo #5, completado con los tres revisores (`operations` #18, `collections` #19, `data_quality` #20), cada uno con `model_invoked=true`, salida aceptada y 14 propuestas en datos demo sintéticos. También preserva el intento previo #4 fallido por salida rechazada, sin reintento automático. El recibo registra eventos de error intermedios del proveedor antes de `turn.completed`; por ello se concluye éxito de la corrida validada, no ausencia de incidencias internas ni disponibilidad universal del modelo.
