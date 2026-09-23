# Fase 7 — Automatizaciones y agentes

Objetivo: analytics y revisores se ejecutan sin botón mientras el servidor local está abierto. Requisitos AUT-01 a AUT-04 y AGT-04/05.

Decisiones: una cola SQLite persistente almacena disparador de intervalo o AuditEvent, deduplicación, lease, intentos, resultado/corte y error. El trabajador pertenece al proceso servidor Waitress; inicio y apagado explícitos, sin hilo en importación WSGI ni proceso aparte 24/7. Pausa y frecuencia configurables por gerencia; reglas deterministas por defecto; CLI nativa solo opt-in expreso. Trabajo vencido se recupera con lease y reintento acotado. Una inferencia interrumpida tras iniciar CLI queda en revisión/estado ambiguo, nunca se relanza automáticamente sin evidencia de que no corrió. `AuditEvent` no debe provocar bucle por eventos generados por el propio trabajador.

El circuito de agentes reutiliza V5: propuesta con huella de evidencia, decisión humana, responsable, tarea idempotente y resultado; se agrega enlace a corte y trabajo automático. No enviar mensajes a terceros, comprar, cobrar, modificar registros operativos ni diagnosticar mecánica automáticamente.

Gate: pruebas con reloj controlado de intervalo, evento único, deduplicación, pausa, worker caído durante lease, error permanente, reinicio, CLI ambigua y rechazo de propuesta obsoleta. Inspeccionar latido y error desde interfaz con permisos.
