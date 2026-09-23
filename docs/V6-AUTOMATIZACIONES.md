# Automatizaciones V6: cortes y revisión local

Milenio V6 inicia un trabajador local junto con el servidor. Sigue funcionando mientras la consola del lanzador y la aplicación están abiertas; al cerrar el servidor se detiene. La vista `/automations/` muestra el último latido, la próxima revisión, el cursor de eventos, los trabajos pendientes o completados y sus errores. “Sin latido reciente” exige revisar servidor y registro del trabajador; no equivale a operación sana.

## Qué dispara y produce una ejecución

Por defecto, el trabajador observa eventos de negocio registrados y un intervalo de 60 minutos. Agrupa cambios cercanos con una espera breve y guarda un trabajo de cola antes de avanzar el cursor. Gerencia puede habilitar o deshabilitar la programación, cambiar el intervalo desde la interfaz entre 1 y 1440 minutos, y pausar el procesamiento. Quienes tienen permiso de revisión pueden poner una ejecución manual en cola. Pausar deja trabajos pendientes sin procesar hasta reanudar. Un trabajo dura después de cerrar el navegador; para procesarlo debe haber trabajador activo.

Cada ejecución primero guarda un corte analítico y luego ejecuta los revisores de operaciones, cobranza y calidad de datos. La salida de revisores son propuestas internas con evidencia y estado de revisión. Aceptar una propuesta puede crear una tarea interna; el equipo decide, asigna, ejecuta y registra el resultado. El trabajador no cambia órdenes, inventario, facturas ni pagos, y no envía comunicaciones externas. Un corte o una tarea completada no prueba que la intervención haya mejorado el negocio.

## Reglas y Codex nativo

Las reglas verificables son el modo predeterminado y funcionan sin Codex. Codex nativo sólo aparece si la instalación habilitó `MILENIO_CODEX_ENABLED=1` y configuró una sesión oficial local; Gerencia debe activarlo además para trabajos automáticos. Una ejecución manual nativa también requiere esa habilitación. El CLI y la sesión no vienen en el paquete; el uso nativo consume los límites de la cuenta autenticada en esa instalación. Los revisores trabajan con un paquete de evidencia acotado y campos permitidos; los contactos de clientes no son necesarios para sus prompts. Los resultados nativos requieren revisión humana igual que los de reglas.

## Fallos, reintentos y lectura del historial

La cola registra disparador, modo, intentos, corte, revisores y errores. Los trabajos de reglas pueden reintentarse dentro de un máximo de tres intentos con espera creciente cuando falla su ejecución. Una ejecución nativa tiene un solo intento: si se interrumpe o vence su concesión, el resultado puede ser ambiguo y no se invoca de nuevo automáticamente. Un trabajo fallido no debe presentarse como revisión completada; el operador inspecciona sus errores y decide si necesita una nueva ejecución manual. Un corte ya guardado por un intento fallido puede existir aunque los revisores no hayan terminado.

El cursor de eventos y las claves de deduplicación evitan crear múltiples trabajos para el mismo intervalo observado. La hora de un corte registra cuándo se leyó la operación, no cuándo ocurrió históricamente cada cambio. Los respaldos incluyen cortes, filas analíticas, política, cursor y cola; al restaurar se purgan sesiones de usuario por seguridad y se exige el mismo modo y esquema de migraciones con el servidor detenido. Consulte [Analytics V6](V6-ANALYTICS.md) para fechas, cobertura y límites de los indicadores.
