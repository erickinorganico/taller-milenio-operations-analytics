# Milenio: servidor compartido, CRM y Codex

**Para entrar desde el celular**, Gerencia guarda un perfil privado y un favorito en el teléfono. El equipo puede abrir órdenes desde Safari o Chrome con su usuario habitual. [Preparar el teléfono y entrar al taller](infra/CELULAR.md).

En la computadora central con Windows x64 y Python 3.12, extraiga el ZIP completo y abra **Instalar-Servidor.cmd**. Al terminar, abra la dirección que muestra el instalador y cree la cuenta de Gerencia. Para actualizar una instalación, siga la [guía de mantenimiento](infra/DESPLIEGUE-Y-RECUPERACION.md). Administración encontrará las opciones de PowerShell en la [guía de instalación](infra/INSTALAR.md).

Para explorar datos ficticios sin instalar un servidor compartido, use `Abrir-Demo.cmd`. Los lanzadores de trabajo V6 anteriores se conservan para migración explícita y no deben usarse en los clientes. No sustituya una instalación antigua sin respaldo y revisión de sus datos; el instalador no adopta carpetas de datos ajenas silenciosamente.

Código y dependencias se distribuyen; Gerencia, llaves de acceso, OAuth y datos privados se configuran en el equipo elegido. Consulte [mantenimiento y recuperación](infra/DESPLIEGUE-Y-RECUPERACION.md). Las secciones siguientes describen las funciones del taller.

El inicio muestra el panorama gerencial de [analytics V6](docs/V6-ANALYTICS.md). Sus seis tablas analíticas se construyen desde la operación y quedan guardadas por corte con referencias a los registros fuente. Los filtros de fechas comparan periodos de igual duración; el trabajo abierto y el saldo pendiente muestran el estado al momento del corte. En [Automatizaciones V6](docs/V6-AUTOMATIZACIONES.md) se explica cómo funciona el trabajador local, la cola, el modo de reglas y la opción de Codex.

El dashboard tiene tres vistas: **Resumen**, con indicadores, tendencias y distribución de órdenes; **Demanda**, con servicios y refacciones que puede buscar y ordenar; y **Seguimiento**, con propuestas, acciones, cobertura y tablas fuente. Seleccione 7, 30 o 90 días, un rango propio, tipo de cliente y corte. Use las flechas sobre el gráfico para consultar los importes diarios. La [especificación de la interfaz](docs/ANALYTICS-DESIGN.md) explica qué representa cada gráfico y su relación con los registros del taller.

El trabajador funciona mientras el servidor está abierto. Se pueden solicitar actualizaciones desde “Actualizar y revisar” o esperar las revisiones automáticas. Los resultados preparados por agentes son propuestas y tareas internas sujetas a revisión humana; no envían mensajes ni cambian órdenes, pagos o inventario. Si no hay corte, revise el estado y los errores de la cola en `/automations/`.

Si el ZIP contiene `.runtime/wheels/`, `Setup-Web.ps1 -Offline` instala las dependencias sin acceso a Internet. Ejecute `powershell -NoProfile -ExecutionPolicy Bypass -File .\Setup-Web.ps1 -Offline` antes de abrir el lanzador. Las ruedas incluidas son para CPython 3.12 en Windows x64. Sin ruedas incluidas, el instalador usa los paquetes fijados en `requirements-web.txt`.

El modo Codex nativo es opcional. Requiere Node.js/npm, el CLI oficial instalado y una sesión propia: desde PowerShell en esta carpeta, ejecute `. .\Setup-Agents.ps1`, `& $env:MILENIO_CODEX_BIN login` y `$env:MILENIO_CODEX_ENABLED = '1'` antes de abrir el lanzador desde esa consola. El ZIP no contiene el CLI, claves API, contraseñas, bases de clientes, fotos ni respaldos operativos. Sin Codex, siguen disponibles las reglas locales. Las pruebas de V6 no afirman inferencia nativa en otra instalación.

El [manual operativo V5](docs/V5-MANUAL.md) conserva el flujo de cuentas, roles, CSV, órdenes e inventario que V6 amplía. Los documentos `V5-*` y las verificaciones de esa versión describen su evidencia histórica; no son pruebas de una instalación V6 ni de adopción con datos reales. La documentación en `.planning/` describe alcance y planes.


## Abrir y cerrar sin depender de Codex

El personal entra al servidor central por su acceso guardado. Si el servidor está detenido, la persona responsable revisa la tarea de inicio y el supervisor de la instalación según la [guía de operación](infra/OPERACION-CODEX.md). Para practicar con datos ficticios en esta computadora, haga doble clic en `Abrir-Demo.cmd`.

Para cerrar la demo, ejecute `powershell -NoProfile -ExecutionPolicy Bypass -File .\Abrir-Milenio.ps1 -Mode demo -Stop`. Para detener y reanudar el servidor central, siga el [procedimiento del supervisor](infra/DESPLIEGUE-Y-RECUPERACION.md).

Si se usa una ruta personalizada, `Abrir-Milenio.ps1 -Mode demo -DataDir "C:\ruta\demo"` la recuerda en `private/launcher-demo.json`, que no se incluye en el ZIP. El modo y la instancia se comprueban antes de reutilizar o cerrar el servidor. Un puerto de otra aplicación no se detiene. Los datos heredados no se trasladan automáticamente.
