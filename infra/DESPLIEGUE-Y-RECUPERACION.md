# Despliegue, mantenimiento y recuperación

## Versiones y carpetas

GitHub conserva versiones revisadas. Producción ejecuta una release inmutable, identificada por SHA, fuera de OneDrive y del checkout de desarrollo. Usar directorios separados para releases, datos live, datos de pruebas, configuración privada y respaldos. La selección de rutas se registra en inventario privado. La app no se actualiza por sincronizar una carpeta compartida.

Antes del primer despliegue compartido, integrar el código comercial/Gmail local y sus dependencias en un PR propio. El main identificado en `estado.json` todavía no lo contiene. No instalar en la segunda computadora suponiendo que clonar main reproduce el workspace original. Esta infraestructura no publica cambios ajenos de captura de documentos que estaban en edición.

## Alta de servidor (pendiente de ejecución)

1. Asignar hostname, identificador persistente de instalación (UUID), identidad de servicio y rutas. Registrar configuración local `private/infra.local.json`. La plantilla no activa permisos ni workers.
2. Preparar release probada, dependencias fijas y directorio de datos central. Crear Gerencia desde loopback y usuarios individuales. Instalar red privada/proxy con las condiciones de seguridad.
3. Implementar supervisor de arranque con identidad fija. Un solo supervisor inicia app y workers; no duplicar además el worker de correo en el Programador de tareas. Configurar reintentos con espera y detenerlos ante configuración incompatible.
4. Probar arranque sin sesión interactiva y Gmail DPAPI. La autorización OAuth interactiva inicial debe realizarse bajo la identidad que ejecutará el servicio, mediante un procedimiento controlado; cambiar de usuario después exige reconexión.
5. Completar pruebas de `ACEPTACION.md`, registrar SHA, esquema, versión de configuración y resultado en manifiesto privado. Solo entonces marcar capacidades como desplegadas en `estado.json`.

La identidad persistente del servidor es distinta del `launch_id`, que cambia al reiniciar. El endpoint `/health/` actual no demuestra versión, base ni worker sano. Añadir un diagnóstico autenticado que los vincule antes de automatizar mantenimiento remoto.

## Actualizar desde cualquiera de las computadoras

1. **Preparar:** revisar Git y estado de producción; trabajar en rama `codex/...`; pruebas con datos sintéticos y revisión de los archivos exactos a publicar. Crear PR con problema, cambio, pruebas y alcance de despliegue.
2. **Reservar mantenimiento:** un único operador/agente obtiene un bloqueo central con propietario, duración y heartbeat. Registrar ticket/commit y ventana. Este bloqueo está por implementar; mientras tanto, un único responsable ejecuta el despliegue y los demás no intervienen.
3. **Pausar y respaldar:** detener admisión de nuevos envíos; esperar intentos activos y conciliar resultados inciertos; detener servicios ordenadamente; generar respaldo consistente de base y medios. Registrar integridad, hash y esquema. No copiar solo el `.sqlite3` abierto y olvidar archivos auxiliares.
4. **Instalar:** preparar nueva release en otra carpeta; aplicar migraciones con entorno live explícito y una única vez; nunca al abrir un cliente. Mantener datos fuera de la release. El lanzador actual migra al arrancar; el supervisor futuro debe separar migración del arranque ordinario y fallar ante esquema incompatible.
5. **Verificar:** salud, login, roles, estáticos, acceso desde ambas PCs, identificador persistente, SHA y workers. Gmail debe sincronizar antes de liberar la cola. No usar un email a prospectos como prueba de humo.
6. **Cerrar:** registrar resultado y release; liberar bloqueo; reanudar únicamente la campaña que estaba autorizada. Actualizar estado y continuidad, preservando antecedentes.

Un PR aprobado/publicado no significa que producción haya cambiado. No configurar despliegue automático a la computadora del taller desde GitHub Actions en esta fase. CI prueba código; producción mantiene credenciales y acceso separados.

## Retorno a versión anterior

Si cambia solo código compatible con el esquema, volver a la release anterior con la cola pausada. Si hay migración incompatible, restaurar backup y código compatible conjuntamente. No asumir que una migración inversa recupera los datos.

Restaurar una base antigua puede olvidar envíos ya aceptados por Gmail después del respaldo. Mantener correo deshabilitado, reconciliar **todos** los envíos y respuestas desde el corte del backup con Gmail y no liberar la cola hasta resolver diferencias. El reconciliador local por Message-ID no basta si el respaldo perdió el registro y su ID: ese caso requiere investigación o una herramienta adicional. Nunca reactivar automáticamente tras restauración.

## Fallos y sustitución del central

| Incidente | Respuesta |
|---|---|
| Corte de luz/red | Clientes muestran indisponibilidad. No crean otra base. Al volver, sincronizar y respetar topes; registrar retraso. |
| Proceso bloqueado | Verificar instancia/lease; cierre ordenado y reinicio supervisado. No matar un PID de un registro antiguo sin comprobar identidad. |
| Disco dañado | Restaurar backup verificado en equipo de reemplazo; reconstruir permisos y reconectar Gmail. |
| Central perdido | Antes de promover reemplazo, impedir que el anterior vuelva a enviar: revocar autorización Gmail y acceso de red; deshabilitar su servicio si es accesible. |
| Dos copias activas | Pausar ambas y conciliar antes de elegir una. El lease SQLite protege una base, no dos bases clonadas. |

No hay failover automático en la primera etapa. Conservar una copia de respaldo no la convierte en un servidor activo.

## Objetivos propuestos de recuperación

Backup diario cifrado y previo a cada actualización; retención inicial 7 diarios y 4 semanales, ajustable según espacio. Ensayo mensual en entorno aislado sin correo habilitado. Objetivo propuesto de pérdida máxima de datos: 24 h entre copias; objetivo de recuperación: una jornada, sujeto a hardware y responsable. Son objetivos por validar, no garantías ni tareas ya programadas.

La inspección de un respaldo no sustituye una restauración de ensayo. Los informes públicos solo indican resultado y fecha; rutas privadas, datos y credenciales quedan fuera de GitHub.
