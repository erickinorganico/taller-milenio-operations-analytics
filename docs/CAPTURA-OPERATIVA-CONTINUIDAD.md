# Captura de imágenes integrada a la operación

Estado vigente del trabajo de captura: **6 de octubre de 2026**. El antecedente
del 1 de octubre en REVISION-Y-PILOTO.md describe un piloto que sólo exportaba.
Esta implementación añade la aplicación transaccional a la base del taller.

Actualización de la entrega: Excel y CSV conservan también tipo, cantidades,
precios, costos y `part_sku` de los servicios revisados. Excel usa celdas numéricas
para calcular sobre importes observados; los datos desconocidos quedan vacíos.
CSV incluye una fila por servicio con la identificación de su documento. Ambos
formatos conservan protección contra fórmulas. La lectura y sus importes no
sustituyen la revisión ni autorizan cotizaciones o cobros.

## Estado activo verificado

Demo activa en **http://127.0.0.1:8766/**, con migración 0005 aplicada después
de un respaldo completo verificado. El acceso conserva la cuenta existente; la
sesión del navegador debe iniciarse de nuevo si expiró. No se cambió contraseña.

Prueba de cola real, proveedor GPT-6 Luna y aplicación: captura **#2**, orden
**#39 / VISION-DEMO-20261006**, cliente ficticio #5, vehículo ficticio #7 y dos
solicitudes de servicio. Duración de cola/lectura/revisión sintética/aplicación:
**12.05 segundos**. La revisión de esta muestra fue técnica por Codex bajo
instrucción del propietario; no acredita aceptación humana del taller. La
actualización analítica se procesó. Recibo: `.workbench/capture-integration/pipeline-real.json`.

Los servicios no generaron cotizaciones aprobadas ni movimientos financieros.
Esta verificación se ejecutó únicamente en demo, sin datos reales de clientes.

**Suite final: 256 pruebas aprobadas**, incluyendo taller, módulo comercial,
captura, validación de visión, aplicación transaccional, recuperación y cancelación
de procesos. Las pruebas de modelos con subprocess simulado están diferenciadas
de las dos lecturas reales con la hoja ficticia. No hay migraciones pendientes
de generar; `git diff --check` no detectó errores de formato. La última suite se
ejecutó con temporales fuera de OneDrive para evitar interferencia de sincronización.

## Flujo disponible

1. En **Capturar documentos**, sube la foto. El título es opcional. Elige GPT
   Luna o lectura local de Windows; Luna aparece seleccionado si la sesión
   de Codex está disponible.
2. Un trabajador propio procesa la imagen. No ocupa los trabajadores de correo
   ni análisis. Conserva proveedor, modelo solicitado, huellas y resultado.
3. Revisa los datos y los servicios estructurados. Cantidad, precio y costo
   desconocidos permanecen vacíos. Confirma la lectura revisada.
4. Pulsa **Ver cambios para aplicar al taller**. Folio, placas y VIN buscan
   registros existentes. Puedes elegir cliente, vehículo u orden si necesitas
   resolver coincidencias. La vista previa indica cada alta/actualización.
5. **Aplicar estos cambios al taller** guarda cliente, vehículo, orden y servicios
   solicitados, vincula la foto y abre la orden actualizada. El cambio queda
   auditado y encola la actualización analítica.

La base de datos muestra los registros operativos. Los servicios de las fotos
tienen su propia fuente, **Servicios solicitados desde fotos**. Son información
pendiente de cotizar; no se cuentan como servicios autorizados o facturados.
Excel/CSV quedan como copia opcional de la captura revisada.

## Infraestructura y controles

- `capture_vision.py`: imagen adjunta al CLI, esquema JSON cerrado, GPT-6 Luna
  o GPT-5.6 Luna y plazo de 90 segundos. Sesión ChatGPT existente; sin ruta
  alternativa a claves API. No habilita herramientas, navegación ni plugins.
- `run_document_captures`: cola persistida, una foto por turno, supervisada por
  el servidor. Separada de `run_automations` y su procesamiento comercial.
  El cierre comunica cancelación al lector y termina solamente su proceso hijo;
  se verificó también la cancelación de un proceso real sin invocar modelos.
- `capture_application.py`: permiso de Recepción, plan firmado por usuario y
  captura durante 15 minutos, validación dentro de transacción y huellas de los
  registros originales. Preview revierte sus escrituras; commit aplica todo
  o revierte todo. Una captura aplicada devuelve su resultado previo al repetir.
- Estado aplicado con orden, usuario, fecha y cambios persistidos. No admite
  volver a revisar o reintentar la lectura para aplicar dos veces.
- Los campos vacíos no borran contactos, notas, propietario, asignación o fechas.
  Cliente incompatible, placa/VIN conflictivos, orden cerrada y kilometraje
  menor quedan bloqueados para resolución. No cambia etapas ni autorizaciones.
- Una segunda foto del mismo folio conserva su evidencia y reutiliza solicitudes
  coincidentes. Renglones con igual descripción y distinto SKU se preservan.
  Dentro de una misma captura, importes incompatibles del mismo concepto requieren
  diferenciación explícita. Entre fotos, cantidades/importes observados de una
  solicitud existente pueden actualizarse con vista previa, confirmación y auditoría.
- Los servicios extraídos conservan cantidades/importes observados en una entidad
  propia. No convierten ausencia de precio en cero ni generan cotización aprobada,
  pago, compra, movimiento de inventario o diagnóstico mecánico.

## Verificación de modelos

Se comprobó el CLI instalado y su sesión ChatGPT con permisos del usuario. El
primer chequeo desde el sandbox no podía ver la autenticación; no se modificaron
credenciales para resolverlo. La prueba externa usó exclusivamente una hoja
ficticia marcada como tal.

**Lectura real con GPT-6 Luna terminada:** exit code 0, `turn.completed`, esquema
validado y dos servicios con cantidades/importes null. Recuperó folio, cliente,
placa, marca, modelo, año, kilometraje y solicitud de la imagen sintética. Recibo
local en `.workbench/capture-integration/vision-real.json`; no es evidencia sobre
la precisión de documentos manuscritos reales.

El argumento de ejecución solicita `gpt-6-luna`; la CLI no devolvió identidad
independiente del modelo (`observed_model=null`). El recibo acredita la ejecución
real y el modelo solicitado, sin sustituir esa comprobación por un supuesto.

La CLI emitió un aviso conocido de exceso del catálogo de skills. Sólo ese
diagnóstico entero se conserva como `cli_warnings` cuando hay finalización y
salida válida; cualquier otro error o uso de herramientas sigue rechazado.

**OpenCode pendiente:** no se encontró ejecutable en las rutas habituales del
usuario. La existencia de opencode.db no acredita sesión, proveedor Go ni entrada
de imagen. Su opción informa que falta conexión; no simula extracción. Antes de
activarlo se necesitan ejecutable, proveedor autenticado, modelo con visión,
contrato de salida y una prueba sintética equivalente. No se instalaron paquetes
ni se accedió a claves, chats o datos reales de clientes para investigar.

## Uso y límites de automatización

La extracción y la identificación se ejecutan automáticamente. Guardar cambios
en registros operativos requiere confirmar el plan. Esto permite corregir letras,
folios, propietario o importes antes de modificar la base. Una foto arbitraria no
acredita autorización de trabajo, cobro recibido o existencia de una refacción.

El envío de fotos por WhatsApp/Gmail, acceso desde otros teléfonos, aplicación
sin revisión y modelos OpenCode siguen pendientes. El punto de entrada actual es
la carga autenticada en la app. El trabajo no altera captación, catálogo comercial,
Site, permisos de publicación ni identidades Library.

## Instalación

Incluye migración `workshop.0005_documentcapture_application_result_and_more`.
Respaldar base y medios antes de iniciar la nueva versión. El lanzador aplica las
migraciones y levanta los dos trabajadores; no ejecutar lectores antiguos dentro
de la cola de automatizaciones. Un servidor anterior debe reiniciarse para tomar
los cambios. No restaurar solamente una migración inversa para recuperar medios
y datos; conservar un respaldo completo y el código compatible.
