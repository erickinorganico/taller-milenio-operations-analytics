# Operar Milenio desde Codex

## Instrucción corta para cualquiera de las computadoras

> Lee AGENTS.md e infra/README.md. Identifica si este equipo es servidor, cliente o desarrollo. Revisa el estado de Milenio sin enviar correos ni modificar producción. Dime qué funciona, qué está pendiente y qué requiere intervención. Usa el CRM central como fuente de datos.

No se necesita pegar conversaciones anteriores. El repo explica el sistema; la configuración privada identifica el equipo y el CRM central conserva los hechos. Si el repo está desactualizado, comparar el SHA con la release desplegada antes de actuar. GitHub no contiene la base ni los correos.

## Diagnóstico disponible hoy

Con Python 3.12, desde la raíz:

```powershell
python scripts/infra_doctor.py --config private/infra.local.json
```

No importa Django, no crea una base, no lee tokens, no modifica archivos y no envía correo. Sin configuración devuelve pendientes y código 2. El ejemplo sin completar también debe dar pendientes; nunca presentarlo como sistema sano.

Solo cuando la URL ya esté configurada, agregar `--probe` para comprobar `/health/` mediante HTTPS, con certificado válido y sin seguir redirecciones. No consulta buzones. El endpoint actual identifica aplicación/modo/arranque; no acredita versión desplegada, worker sano ni identidad persistente del servidor. Por eso el diagnóstico distingue conectividad de aceptación operativa.

En el servidor, `--inspect-local-db` permite abrir **en solo lectura** la base indicada por el inventario, si coincide el hostname asignado. Devuelve conteos de cola y migraciones, nunca nombres, destinatarios ni cuerpos de correo. No ejecutar esa opción en clientes ni en datos de prueba que se pretendan presentar como producción.

Las rutas son relativas al clon; no dependen de un nombre personal de usuario. La instalación inicial de Python es un requisito externo. El script utiliza únicamente biblioteca estándar.

## Permisos y modos de trabajo

| Solicitud | Acción de Codex | Límite |
|---|---|---|
| «Revisa el sistema» | Diagnóstico, estado, incidencias y propuesta concreta de reparación. | No activa campañas ni reinicia producción por defecto. |
| «Prepara el seguimiento» | Consultar conversación central, redactar y preparar cola usando servicios del CRM cuando esté habilitado el acceso. | No duplicar envíos desde el conector Gmail de Codex. |
| «Envía esta tanda» | Ejecutar dentro de destinatarios, contenido y límites autorizados; registrar cada resultado. | Si falta autorización explícita de envío, preparar la tanda para revisión. |
| «Mantén/actualiza la app» | Comparar versiones, arreglar en rama, probar y preparar despliegue; ejecutar lo que cubra la autorización vigente. | No sobreescribir cambios ajenos ni migrar la copia de un cliente como si fuera el central. |
| «Responde cotizaciones» | Preparar respuesta con hechos y condiciones confirmados. | No inventar precios, crédito, capacidad, agenda ni aceptación del cliente. |

Autorización de mantenimiento y autorización comercial son alcances diferentes. No pedir otra aprobación para acciones ya autorizadas. Pausar solo la parte que requiera una decisión pendiente, continuando trabajo independiente.

## Revisión diaria propuesta

Comprobar central y worker; sincronización Gmail reciente; cola vencida; envíos inciertos; bajas/rebotes; respuestas pendientes; copias de seguridad; conflictos de conversación. Atención humana primero en urgencias y solicitudes comerciales concretas. Registrar una tarea con responsable y vencimiento; no tratar una notificación en chat como asignación confirmada.

Las revisiones programadas de Codex se configuran como automatizaciones del producto cuando el usuario lo solicite y el acceso central funcione. Crear una sola por función, con avisos de cambios relevantes; registrar responsable y destino para evitar dos automatizaciones equivalentes en dos PCs. No se programó ninguna en esta entrega.

## Operación simultánea

El servidor debe ofrecer la toma de conversación definida en el contrato. Codex A y Codex B consultan la misma versión; uno adquiere la tarea y el otro ve quién la atiende. Una versión obsoleta devuelve conflicto y obliga a releer. Las bajas se verifican nuevamente al enviar, independientemente de quién redactó.

Si no existe todavía la toma de conversación, asignar un único responsable de responder y limitar el segundo equipo a consulta/preparación; no prometer prevención completa de colisiones. La API y esa toma están pendientes, aunque la cola de correo local tenga protección contra duplicados.

## Cuando algo falla

- Central caído: comprobar red privada, proceso y energía. El cliente no crea una instalación sustitutiva.
- Error de Gmail: detener nuevos envíos, conservar cola y revisar autorización desde el servidor. No copiar tokens entre usuarios de Windows.
- Envío incierto: reconciliar con Gmail; no reintentar a mano.
- Sospecha de cuenta comprometida: Gerencia revoca sesión/dispositivo y permisos Google afectados, conserva evidencia y cambia credenciales; no borrar registros para ocultar el incidente.
- Cambios concurrentes de otro Codex: leer estado y coordinar por tareas/PRs. No deshacerlos ni enviar mensajes a otros chats sin autorización del usuario.

## Formato de entrega del agente

Informar: equipo/rol verificado, release observada o desconocida, controles ejecutados, cambios realizados, validación, incidencias y siguiente acción. Guardar evidencia operativa sensible solo en el servidor o reporte privado. En GitHub publicar únicamente resultados saneados y código/procedimientos pertinentes.
