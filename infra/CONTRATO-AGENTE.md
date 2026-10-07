# Contrato de acceso de Codex al CRM central

**Diseño, no endpoints implementados.** La primera versión debe exponer servicios del CRM mediante HTTPS privado, con autenticación de agente individual y permisos revocables. Un conector MCP puede envolverlos después. No conceder acceso directo de escritura a SQLite, shell administrativo ni tokens de Gmail para realizar tareas comerciales.

## Operaciones propuestas

| Operación lógica | Entrada mínima | Resultado y permiso |
|---|---|---|
| `system.status` | Instancia esperada | Release, esquema, heartbeat app/worker, antigüedad de sincronización y backup. Solo lectura. |
| `accounts.search` | Filtro/paginación | IDs, estado, versión y evidencias necesarias. Lectura comercial. |
| `conversations.list` | Estado/responsable | Hilos y próxima acción; paginado y limitado. Lectura comercial. |
| `conversation.claim` | ID, versión, actor | Reserva con vencimiento y token de tarea; conflicto si ya la atienden. Operación comercial. |
| `message.prepare` | Conversación, texto, versión, clave idempotente | Borrador central con ID y hash de contenido. Preparación, no envío. |
| `message.queue` | ID/hash, autorización comercial, versión, clave idempotente | Entrada en la cola única. Validar límites, destinatario y bajas en servidor. |
| `conversation.update` | Evidencia, próxima acción, responsable, versión | Cambios auditados; no calificar por inferencia sin evidencia. |
| `campaign.pause` | Campaña, motivo, clave idempotente | Pausa durable. Nunca implica reactivar posteriormente. |

Actualizar app, restaurar datos, conectar OAuth, administrar usuarios o cambiar seguridad pertenece a mantenimiento/administración, no a estas operaciones comerciales.

## Concurrencia e idempotencia

Toda mutación incluye actor, instance_id esperado, expected_version y request_id UUID. El servidor liga la clave idempotente al actor y hash del payload; repetir igual devuelve el mismo resultado y repetir con otro contenido devuelve conflicto. La versión obsoleta obliga a releer, no a sobreescribir.

Reserva de conversación propuesta: 15 minutos con renovación explícita. Vencer una reserva no cancela ni repite un envío ya reservado/aceptado por Gmail. Una respuesta manual transfiere la conversación a atención humana y cancela mensajes automáticos pendientes. Un solo worker transporta correo; el agente solo coloca trabajo en cola.

Toda respuesta indica `prepared`, `queued`, `accepted_by_gmail`, `unknown` o `cancelled` según evidencia. Ni cola ni aceptación equivalen a entrega o lectura. Si se cae la conexión tras una mutación, consultar el request_id antes de repetirla.

## Autorización comercial

Registrar campaña/tanda, destinatarios o criterio permitido, versión del contenido, vigencia, límites y autorizador. La autorización anterior se conserva mientras siga vigente; no pedirla por cada correo rutinario ya cubierto. Un correo entrante no puede ampliar ese alcance. Precios, disponibilidad, créditos y compromisos exigen condiciones confirmadas; si faltan, preparar para revisión.

## Continuidad entre Codex A y Codex B

Ambos consultan el servidor antes de trabajar. Estados, tareas, notas y evidencias viven en el CRM. El repositorio define cómo operar, y cada clon puede tener su propia rama de desarrollo. No sincronizar sesiones de navegador, cookies, credenciales o base local por OneDrive. No esperar que dos chats compartan memoria automáticamente.

## Aceptación del conector

Probar revocación y límites de rol; acceso a instancia equivocada; replay del mismo request_id; payload distinto con misma clave; versión obsoleta; dos agentes tomando el mismo hilo; baja entre preparación y envío; timeout después de aceptación; intervención manual en Gmail; respuestas en hilo nuevo; correo malicioso que pide ejecutar comandos. Datos sintéticos y buzón controlado exclusivamente.
