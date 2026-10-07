# Actualizar, respaldar y recuperar

## Actualización

Descargar la versión revisada, inspeccionar cambios y ejecutar Setup-Server con el mismo InstallRoot. Prepara otra release por hash; detiene la anterior mediante señal privada; espera liberación del bloqueo real; respalda antes de migrar; aplica esquema y actualiza el puntero privado solo si termina. El supervisor no migra al arrancar y rechaza código cambiado o esquema pendiente. Datos/credenciales permanecen fuera de releases.

El servidor y el mantenimiento de base comparten `.server.lock` del sistema operativo. Si está ocupado, migración/backup falla; no se fuerza. La señal de parada es persistente: un reinicio automático no puede reabrir el servicio durante mantenimiento. `deploy.py resume` la retira explícitamente. Setup-Server y Backup-Server comparten también un lock de instalación que cubre selección de release y reinicio; una segunda operación concurrente se rechaza.

## Backup

`Backup-Server.ps1` detiene el supervisor, espera su lock, hace copia consistente de SQLite y medios con manifiesto/hashes, y reanuda si no estaba previamente detenido. El registro de tareas programa este script a las 03:00. Hay una interrupción breve: no prometer backup sin pausa. La copia previa a actualización también se realiza con servidor detenido.

Configurar destino privado separado del disco principal. No se eliminan copias automáticamente. Revisar espacio y antigüedad. Los backups contienen datos sensibles y no llevan cifrado incorporado: usar almacenamiento cifrado. Ensayar restauración en equipo aislado y documentar resultado privado.

## Restauración

Detener con `deploy.py stop`; usar código compatible con el esquema; ejecutar `deploy.py restore --input <backup> --confirm-restore`. Se verifica manifiesto, integridad y se conserva el estado anterior. Se invalidan sesiones, se revocan tokens de agentes restaurados, se desconecta/deshabilita correo y se crea `.mail-recovery-hold` fuera de la base. La copia por sí sola nunca habilita envíos.

Un backup antiguo puede olvidar correos enviados después de su corte. Revisar en Gmail todo ese intervalo, incluidos mensajes cuyos IDs ya no están en la base. La conciliación automática por Message-ID no basta para registros perdidos. Tras reconciliar, reconectar Gmail, emitir nuevas credenciales y habilitar transporte con `deployment_mail --enable --authorization <referencia> --reconciliation-reference <evidencia>`. El agente no inventa esa evidencia ni retira el hold por su cuenta.

Para volver de una migración incompatible, restaurar código y base compatibles conjuntamente. Una migración inversa no garantiza recuperar información. No permitir que el viejo y el nuevo servidor envíen a la vez: revocar OAuth y acceso de red del anterior antes de promover reemplazo.

## Alcance de supervisión

El supervisor posee el lock central y reinicia hijos que salen con espera creciente hasta 60 s. Cada worker informa heartbeat y estado. Un proceso colgado debe investigarse; no se mata automáticamente un envío en curso porque puede haber sido aceptado por Gmail. Los envíos interrumpidos pasan a resultado incierto para conciliación. La pérdida del padre cierra stdin de hijos y solicita su parada.

Los objetivos de backup diario y recuperación en una jornada son operativos por validar; dependen de hardware, copias y responsable. Pruebas de instalación en dos PCs, reboot y OAuth real se realizan en destino.
