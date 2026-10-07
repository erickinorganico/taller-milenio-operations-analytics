# Criterios para habilitar uso en dos computadoras

Todos pendientes salvo el diagnóstico portátil y sus pruebas unitarias incluidas. Un documento o configuración de ejemplo no constituye evidencia de despliegue.

| Prueba | Resultado exigido |
|---|---|
| Release reproducible | Clon limpio contiene CRM/correo y dependencias; pruebas pasan; SHA identificado. |
| Dos usuarios | Ven la misma empresa y actualización; cada acción conserva autor. |
| Identidad de servidor | Ambas PCs confirman mismo instance_id persistente y misma release, incluso después de reiniciar. |
| Cliente aislado | Sin red central, no inicia worker/base live ni se presenta como servidor. |
| Red | Equipo autorizado entra por HTTPS; equipo no autorizado y acceso público quedan bloqueados. |
| Acceso | Contraseña errónea limitada; revocación efectiva; permisos y CSRF probados; segundo factor conforme al diseño. |
| Arranque | Servidor y workers vuelven después de reinicio con pantalla bloqueada y sin intervención; solo una instancia. |
| Correo real controlado | Envío, recepción, respuesta, bajas, rebote, timeout y conciliación; sin prospectos durante QA. |
| Dos agentes | Reserva/versión impiden respuestas simultáneas; uno solo encola por solicitud. |
| Cadencia | Topes y horario se mantienen tras reinicio, retraso y cambio horario de Tijuana. |
| Pausa | Respuesta, baja o intervención manual cancelan seguimientos; no vuelven al expirar una reserva. |
| Backup | Copia cifrada fuera del disco; restauración abre datos y medios con permisos correctos. |
| Recuperación de correo | Restauración permanece pausada hasta reconciliar lo ocurrido desde el backup. |
| Actualización | Cambio/reversa de release con esquema compatible o restauración conjunta; sin pérdida silenciosa de datos. |

Guardar en reporte privado: fecha, operador, equipos, SHA, esquema, checks y limitaciones. Publicar solo un resumen saneado y actualizar `estado.json`. Una prueba fallida mantiene deshabilitada la capacidad afectada.
