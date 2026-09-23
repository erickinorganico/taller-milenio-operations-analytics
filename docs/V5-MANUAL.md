# Milenio V5: manual operativo

La aplicación registra trabajo real en una instalación local de un taller. El inicio muestra pendientes según los datos capturados; una pantalla vacía indica que aún no hay registros elegibles. Las métricas y las propuestas de agentes dependen de la cobertura del historial y muestran límites cuando faltan datos. La demo está marcada como ficticia y vive en otra base.

La consola de inicio muestra dónde se guardan los datos. En Windows, la ubicación predeterminada es `%LOCALAPPDATA%\Milenio\operational\live` o `...\demo`, separada de la carpeta donde extrajo la aplicación. Si actualiza desde una edición que guardaba datos en `private/operational`, siga el traslado mediante respaldo y restauración descrito en [instalación y recuperación](V5-INSTALACION.md); el inicio no mueve ni borra esa base automáticamente.

## Acceso y responsabilidades

El primer administrador se crea en `/setup/` tanto para una instalación `live` vacía como para la primera apertura de la demo. Cada persona entra con su cuenta y cierra sesión desde el menú lateral. Las escrituras comprueban el permiso en el servidor; el menú visible por sí solo no concede acceso.

| Rol | Trabajo principal |
| --- | --- |
| Gerencia | Configurar equipo, revisar operación, autorizar tareas internas y consultar todas las áreas. |
| Recepción | Capturar clientes, vehículos, citas, órdenes y cotizaciones; coordinar entrega y seguimiento. |
| Técnico | Registrar inspección y avance permitido de trabajo; documentar tiempos y calidad según el flujo. |
| Refacciones | Revisar partes, existencias, compras registradas, reservas y movimientos. |
| Administración | Emitir comprobantes administrativos, registrar pagos y conciliar saldos. |
| Consulta gerencial | Leer información global, incluida cartera y fuentes, sin escrituras; tampoco cerrar tareas aunque antes se le hubieran asignado. |

Gerencia puede crear cuentas y asignar grupos en **Equipo y acceso** (`/team/`). En **Editar acceso** (`/team/<id>/edit/`) puede cambiar el nombre, el rol, la contraseña o desactivar una cuenta sin borrar su historial. La cuenta administradora activa no se puede desactivar desde ese formulario. Cada persona puede cambiar su propia contraseña en **Mi contraseña** (`/account/`). Use cuentas personales; no comparta la cuenta administradora ni conceda permisos de gerencia para resolver una tarea puntual. Si alguien deja el taller, desactive su cuenta y asigne las tareas pendientes a otra persona.

## Una orden completa

1. **Recepción:** registre cliente y vehículo, kilometraje, motivo de visita, responsable y fecha prometida cuando exista un compromiso. Cree la orden desde **Órdenes de trabajo**.
2. **Inspección:** documente hallazgos y evidencia relevante. Si no existe evidencia, consérvela como pendiente; no complete campos con suposiciones.
3. **Cotización:** agregue mano de obra, servicios o partes con cantidad y precio. Envíe la versión para decisión. Guarde nombre y referencia de la autorización humana antes de aprobar; una versión reemplazada no autoriza trabajo nuevo.
4. **Refacciones y ejecución:** reserve partes disponibles para la orden. Registre recepción de compras antes de aumentar stock, consumo real, liberación o devolución según corresponda. Registre tiempo trabajado y bloqueos. El sistema rechaza consumos sin respaldo y stock disponible negativo.
5. **Calidad y entrega:** documente control de calidad aprobatorio después del trabajo. Revise el estado y la evidencia antes de marcar entrega. Una transición inválida se rechaza y queda pendiente de corrección.
6. **Administración:** emita el comprobante administrativo desde la cotización aprobada. Capture cada pago con referencia; los pagos parciales reducen el saldo y no deben superar el total. El comprobante **no es CFDI** ni prueba depósito bancario.

Los cambios de estado generan eventos de auditoría. No edite directamente importes, stock, aprobaciones o estados en la base SQLite. Si se cometió un error, use el flujo permitido y registre la corrección con su responsable.

## Flotillas, grúas y seguimiento

Registre contratos de flotilla con fechas y términos declarados; programe mantenimiento por fecha o kilometraje con la evidencia disponible. Una oportunidad o tarea de seguimiento no equivale a ingreso. En grúas, capture solicitud, operador, referencias de seguridad e hitos; la aplicación **no decide ni autoriza despacho**.

Las propuestas de agentes son borradores revisables. Consulte evidencia y vigencia antes de aceptarlas. Una aceptación autorizada puede crear una tarea interna una sola vez; no envía mensajes, no compra partes y no cobra. El modo nativo de Codex es opcional y requiere autenticación local de CLI; un fallo de modelo no se presenta como una propuesta validada.

Para habilitar el modo nativo opcional, instale Node.js y npm. Abra PowerShell en la carpeta extraída y ejecute `. .\Setup-Agents.ps1` para preparar el CLI oficial de Codex y conservar `MILENIO_CODEX_BIN` en esa misma sesión. Después ejecute `& $env:MILENIO_CODEX_BIN login` y complete el inicio de sesión personal oficial. En esa consola establezca `$env:MILENIO_CODEX_ENABLED = '1'` y abra `Iniciar-Milenio.cmd` o `Iniciar-Demo.cmd`. El ZIP no trae el CLI ni credenciales y la preparación no inicia sesión por usted. Si falta la sesión o el CLI, el modo nativo queda pendiente; puede continuar con reglas locales. No introduzca claves API en el taller.

## Datos y métricas

**Fuentes de datos** permite consultar registros y relaciones con búsqueda y exportación CSV segura. **Métricas** muestra definición, población elegible, valor y cobertura. Orden abierta, tiempo de servicio, saldo y margen tienen reglas distintas: un estado actual no crea por sí solo duración histórica, una cotización no es ingreso y un costo desconocido impide afirmar margen completo. Use el detalle de registros para conciliar cualquier número antes de comunicarlo.

Para iniciar catálogos existentes, gerencia puede abrir **Importar catálogos** y descargar la plantilla CSV de clientes, vehículos o refacciones. Guarde el archivo como UTF-8 con los encabezados exactos; cada archivo admite hasta 1,000 filas y 1 MB. Revise los errores por fila y la vista previa, que no guarda nada, y después pulse **Confirmar importación**. La confirmación vuelve a comprobar el archivo y agrega todos los registros juntos o ninguno. La vista previa vence tras 15 minutos. Importar vehículos requiere que el cliente ya exista con un nombre único; importar refacciones no agrega existencias. Registre el inventario físico con el flujo de compra o ajuste autorizado. La importación rechaza duplicados y no modifica registros previos.

## Soporte cotidiano

- Si no abre la página, verifique la consola del lanzador y que el puerto 8765 (`live`) o 8766 (`demo`) esté libre. No cierre otro proceso sin identificarlo.
- Si falta una opción, revise el rol con gerencia. Si la escritura fue rechazada, lea el mensaje, confirme el estado actual y vuelva a capturar los datos correctos.
- Si la base o los archivos se dañan, detenga el servidor y use el procedimiento de [instalación y recuperación](V5-INSTALACION.md). Conserve el respaldo original y la copia `recovery-before-*`.
- Si una métrica muestra cobertura desconocida, complete o corrija la fuente; no sustituya el valor por cero.

Los registros son administrativos y operativos. Esta versión no integra CFDI, banco, pagos en línea, mensajería externa, telemetría, compras reales ni diagnóstico mecánico automático.

Demo y taller usan cookies diferentes aunque compartan localhost: abrir uno no sustituye la sesión del otro. El técnico no recibe la opción de entregar/cancelar y el servidor rechaza esos intentos. Consulta gerencial sigue sin permiso de cerrar tareas aunque se hubiera asignado antes de cambiar el rol.
