# Agentes del taller

Recepción y Gerencia pueden usar **Agentes y acciones** en el navegador. Las reglas locales buscan órdenes atrasadas, cobros pendientes y problemas de calidad de datos. Cada propuesta incluye su evidencia. La persona que la revisa puede aceptarla como tarea, rechazarla o comprobar si cambió la orden. Esta función aprovecha el servidor del taller y funciona sin contratar un modelo de IA.

Para una herramienta del equipo que necesita trabajar vía HTTPS, Gerencia puede emitir una credencial individual desde el servidor. Empieza con el permiso que corresponda a su encargo.

| Permiso | Información que recibe | Cambio permitido | Vigencia |
| --- | --- | --- | --- |
| Resumen | Cantidad por etapa, órdenes abiertas sin responsable y abiertas con entrega prometida vencida | Consulta | 30 días |
| Una orden | ID interno, etapa y versión del folio elegido al emitir la credencial | Agregar una nota interna de hasta 500 caracteres a la bitácora de esa orden abierta | 7 días |

La instalación empieza sin credenciales del taller. El servidor comprueba el permiso, la vigencia y la cuenta activa de Gerencia en cada solicitud. La API tiene tres acciones fijas. Los cambios de etapa, pagos, precios y autorizaciones de reparación siguen sus flujos existentes con usuarios del taller. Cada herramienta recibe su propio archivo. Una etiqueta como `analista-semanal` o `seguimiento-refaccion` permite reconocer al agente en la bitácora. Los permisos comerciales pertenecen a su instalación y procedimiento específicos.

## Preparar el acceso

Un administrador ejecuta estos comandos en el VPS, desde el checkout de la versión instalada. En los ejemplos, sustituye `gerencia` por el usuario activo con rol de Gerencia. El subcomando `exec` usa la aplicación que ya está en marcha.

```bash
cd /opt/milenio
dc() { sudo docker compose --project-name milenio-nube --env-file /etc/milenio/nube.env -f infra/nube/compose.yaml "$@"; }
sudo install -d -m 700 /etc/milenio/private/agentes
dc exec -T app python manage.py agent_access --owner gerencia --label analista-semanal \
  --workshop-summary --output /tmp/private/analista.json
sudo test ! -e /etc/milenio/private/agentes/analista.json && \
  dc cp app:/tmp/private/analista.json /etc/milenio/private/agentes/analista.json && \
  dc exec -T app python -c "from pathlib import Path; Path('/tmp/private/analista.json').unlink()"
```

Para una nota, elige el folio exacto que aparece en la pantalla de la orden. Usa un nombre nuevo de archivo para cada emisión. El folio queda fijado al emitir la credencial.

```bash
dc exec -T app python manage.py agent_access --owner gerencia --label seguimiento-refaccion \
  --workshop-order FOLIO-DE-LA-ORDEN --output /tmp/private/seguimiento.json
sudo test ! -e /etc/milenio/private/agentes/seguimiento.json && \
  dc cp app:/tmp/private/seguimiento.json /etc/milenio/private/agentes/seguimiento.json && \
  dc exec -T app python -c "from pathlib import Path; Path('/tmp/private/seguimiento.json').unlink()"
```

Entrega el archivo correspondiente mediante el gestor de secretos o canal privado de administración de Milenio. El programa cliente lee la credencial desde un archivo autorizado y usa el dominio HTTPS que Gerencia dejó fijado al emitirla. La consola de emisión muestra sólo el ID de revocación. Conserva ese ID con la etiqueta en el registro privado del equipo. El agente necesita acceso a este cliente y a su archivo privado. SSH, Docker y SQLite quedan en manos del administrador.

## Consultar y escribir desde el cliente

Desde una máquina con Python 3 y el script del repo, guarda la operación elegida en un archivo JSON privado y ejecuta el cliente. Pedir al modelo externo que analice datos o fotos es una decisión adicional de Gerencia. Las reglas locales y el cliente HTTP funcionan sin proveedores de IA.

```bash
python scripts/agent_client.py --workshop --credential private/analista.json --request private/consulta.json
```

1. Para el cierre de turno, usa `{"action":"workshop.summary"}` con el token de análisis. La respuesta incluye `as_of` con zona horaria, `by_status`, `open_overdue` y `open_unassigned`. Cada orden se cuenta en su etapa actual. Las abiertas excluyen entregadas y canceladas. Una entrega vencida requiere que la fecha prometida sea anterior a la hora del informe. Una orden puede contar tanto como vencida como sin responsable.
2. Con el token de una orden, usa `{"action":"order.status"}`. Anota la `version` devuelta. Este permiso revela únicamente la etapa y los identificadores técnicos de esa orden. La persona responsable aporta las instrucciones del encargo.
3. Para agregar la nota, genera un UUID con `python -c "import uuid; print(uuid.uuid4())"`. Guarda una sola solicitud con ese UUID y la versión consultada. Por ejemplo, para la versión 3:

```json
{"action":"order.note","expected_version":3,"request_id":"ed204d32-33fc-4811-95ce-072b38711a76","note":"Pendiente de confirmar la disponibilidad de la refacción con almacén."}
```

```bash
python scripts/agent_client.py --workshop --credential private/seguimiento.json --request private/nota.json
```

4. Guarda el recibo con `request_id`, `event_id` y la nueva `version`. Recepción abre la orden y consulta **Bitácora**. Ahí ve el texto, la etiqueta del agente, el emisor de la credencial y la hora. La nota conserva su autoría y se muestra como texto. Usa este campo para observaciones verificables o pendientes concretos. Evita nombres, teléfonos, placas, instrucciones recibidas de terceros o datos de pago.

El contrato HTTP es `POST /api/taller/v1/accion`, `Content-Type: application/json` y `Authorization: Bearer …`. El cliente valida TLS y rechaza redirecciones. Los tokens viajan en la cabecera. Los archivos de solicitud, respuesta y credenciales deben mantenerse en el espacio privado del operador.

## Reintentos, revocación y recuperación

| Resultado | Qué hacer |
| --- | --- |
| Se perdió la conexión después de enviar | Reenvía el mismo JSON con el mismo UUID. Si se guardó, vuelve el mismo recibo. |
| `409 stale_version` | Consulta la versión actual, verifica que el seguimiento todavía aplique y prepara una nueva solicitud con otro UUID. |
| `409 request_id_conflict` | El UUID ya corresponde a otro contenido. Concilia el recibo original antes de plantear otra nota. |
| `409 order_closed` | La orden está cerrada. Contacta a la persona responsable si hace falta revisar el expediente. |
| `401 unauthorized` / `403 forbidden` | Comprueba la vigencia del archivo, el rol de quien lo emitió y el permiso otorgado para esa tarea. |

Ante pérdida del archivo, fin del encargo o rotación, revoca por el ID que mostró la consola. La revocación impide también reutilizar recibos con el token. El historial de notas se conserva. La restauración oficial invalida las credenciales que contiene la copia. Emite las necesarias después de verificar la instancia recuperada.

```bash
dc exec -T app python manage.py agent_access --revoke ID-DE-LA-CREDENCIAL
```

Para aceptar la función en el servidor definitivo, usa una orden de prueba, solicita un resumen, agrega una nota, compruébala en el teléfono y reenvía el mismo JSON. Debe haber un solo evento. Revoca ambos permisos y comprueba que la siguiente consulta de cada uno devuelva 401.
