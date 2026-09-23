---
phase: 07-automatizaciones
status: passed
---

# Verificación de fase 7

| Requisito | Evidencia observada | Resultado |
| --- | --- | --- |
| AUT-01 | Pruebas de intervalo y AuditEvent; trabajo de intervalo y tres de evento completados en navegador local, según orquestador | passed_local |
| AUT-02 | Pruebas de política/roles y opt-in; trabajo retenido en pausa más de dos minutos y completado al reanudar, según orquestador | passed_local |
| AUT-03 | `test_expired_rules_lease_recovers_and_claims_job`, `test_expired_native_lease_fails_without_reinvoking_ambiguous_work`, retry y heartbeat en `test_automation.py` | passed_local |
| AUT-04 | Estado/latido en `/automations/`; `artifacts/v6-worker-restart.json` registra cierre del trabajador hijo tras matar servidor; prueba de recuperación de lease | passed_local |
| AGT-04 | `test_worker_orchestration_does_not_mutate_business_records`; propuesta usa evidencia viva y aprobación V5 | passed_local |
| AGT-05 | `test_queued_cycle_links_snapshot_runs_proposals_and_human_followup`; cursor del corte y avance posterior visibles | passed_local |

La revisión independiente de 38 pruebas afectadas está en `.planning/V6-INTEGRATION-REVIEW.md`; el recibo de suite más reciente de 115 pruebas en `artifacts/v6-verification.json`. `artifacts/v6-browser-verification.json` registra pausa/reanudación, trabajos, estado nativo fallido visible y persistencia de sesión; `artifacts/v6-worker-restart.json` registra el cierre del trabajador. `artifacts/v6-native-verification.json` acredita una corrida nativa local real completada con tres revisores y `model_invoked=true`; conserva el intento fallido anterior. `artifacts/v6-delivery-verification.json` prueba el paquete con reglas y declara `native_invoked=false`. Operación 24/7, acciones externas y resultado de negocio quedan fuera de esta verificación.
