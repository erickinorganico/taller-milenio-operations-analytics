# API central para Codex

Implementada en `POST /agent/v1/action`. Autenticación `Authorization: Bearer <token>` individual; no admite autenticación por cookies. Credenciales hash SHA-256 en base, scopes, expiración 90 días y revocación local. Cada solicitud requiere `instance_id` esperado. El cliente oficial admite HTTPS o loopback por túnel SSH declarado, sin redirecciones.

| action | scope | Datos adicionales |
|---|---|---|
| system.status | read | ninguno |
| accounts.search | read | query, offset opcionales; máximo 50 |
| account.get | read | account_id |
| conversations.list | read | offset opcional; máximo 50 pendientes; contenido no confiable |
| conversation.claim | prepare | account_id, expected_version, request_id; reserva 15 minutos renovable |
| conversation.update | prepare | reserva, versión, request_id, next_action, next_action_on |
| message.prepare | prepare | reserva, versión, request_id, inbound_id, body; devuelve draft_id y hash |
| message.queue | send | reserva, versión, request_id, draft_id, content_hash, authorization_reference |
| campaign.enroll | send | reserva, versión, request_id, contact_id, authorization_reference; reglas del piloto |
| campaign.pause | prepare | request_id, reason; pausa global de la instalación |

Toda mutación incluye request_id UUID. Repetir el mismo payload bajo la misma credencial devuelve el resultado previo; cambiarlo con el mismo ID da 409. La reserva y la versión protegen edición entre agentes; las escrituras se realizan en transacción SQLite IMMEDIATE. La cola unique por inbound protege respuestas duplicadas también contra el panel humano. Versiones obsoletas y conflictos obligan a releer, no a forzar.

La API prepara respuestas a mensajes recibidos y permite incorporar contactos ya revisados a la secuencia. No crea cotizaciones ni modifica combustible/evidencia mediante inferencias automáticas. La clasificación del correo mantiene su allowlist; precios, urgencias y compromisos requieren atención humana.

Ejemplo de solicitud privada para consultar, sin token:

```json
{"action":"accounts.search","query":"empresa","offset":0}
```

El CLI agrega instance_id desde la configuración. Tras tomar una conversación, usar la versión devuelta para la siguiente mutación. `authorization_reference` conserva la referencia humana/comercial; no prueba por sí sola que una autorización exista: Codex debe comprobar el alcance en la conversación o registro antes de encolar. Solo conceder send a agentes autorizados.

Preparado y encolado no significan enviado; aceptación Gmail tampoco acredita entrega ni lectura. Un envío desconocido se concilia y no se reintenta ciegamente. Restaurar un backup revoca todas las credenciales de agentes recuperadas y bloquea correo hasta reconciliación.
