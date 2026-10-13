# Documentos, excepciones y filtros

La pantalla **Documentos y excepciones** (`/capture/`) reúne las fotos existentes,
sus estados y el siguiente paso. Usa Django, HTML y CSS del taller; no necesita
cuentas, servicios, dependencias nuevas ni llamadas de IA para consultar o filtrar.

## Resolver una excepción

1. Abre **Excepciones**. Conserva la búsqueda, persona, tipo, estado y fechas.
2. Puedes limitar **Atención** a lectura sin resultado, espera prolongada o datos
   requeridos faltantes. Cada fila explica el motivo y abre su documento.
3. En el documento compara los datos con la foto. Reintentar o continuar
   manualmente utiliza los controles existentes de versión y permisos.
4. Confirma la revisión y abre la vista previa antes de aplicar al taller.
   Filtrar o abrir una excepción no guarda cambios, confirma servicios ni cobra.

**Lectura sin resultado** usa el recibo de error, la lectura vacía o la nota de
interrupción existente. Un documento confirmado o aplicado no permanece en ese
grupo por un error histórico. El paso a captura manual no se presenta como una
nueva falla del lector.

**Espera prolongada** significa más de tres minutos en cola o lectura, o ausencia
del registro de inicio de una lectura en curso. No prueba que el proceso esté
detenido. Un reintento usa la fecha de su último evento auditado, no la fecha
original de la foto. La consulta no recupera ni reintenta trabajos automáticamente.

**Datos requeridos faltantes** indica que una foto por revisar no tiene folio,
o no tiene solicitud ni servicios. No exige inventar cantidades, precios o costos;
los valores desconocidos conservan su estado vacío. Otros requisitos o
coincidencias se resuelven en la vista previa de aplicación existente.

## Filtros y conteos

- Documento: título, folio, cliente, placa o número de la orden vinculada.
- Estado, orden/hoja de servicio, persona que subió la foto y fechas de captura.
- Los cuatro conteos representan toda la selección, antes del filtro de
  **Atención**, no solamente las 25 filas de la página.
- Cambiar página conserva filtros. **Limpiar filtros** vuelve a toda la bandeja.
- Fechas desde/hasta incluyen días completos en la zona configurada del taller
  (`America/Tijuana` por defecto). Los rangos inválidos muestran un error y no
  amplían la selección silenciosamente.

La señal del lector distingue reciente, antigua y desconocida; no demuestra
éxito de extracción o disponibilidad de un proveedor. El OCR local de Windows
queda seleccionado por defecto al subir una foto. Los lectores opcionales
conservan su configuración y condiciones de acceso previas.

En **Órdenes de trabajo** se combinan búsqueda, etapa, responsable, mis órdenes,
atrasos/falta de fecha/falta de responsable y fechas de recepción o entrega
prometida. Los técnicos conservan acceso únicamente a sus órdenes; los filtros
no amplían permisos. Las alertas de atención excluyen entregadas/canceladas.

Los filtros usan formularios GET y funcionan sin JavaScript. En teléfono los
campos se apilan y la tabla se desplaza horizontalmente; puede enfocarse con Tab
y desplazarse con flechas. Las acciones tienen nombres asociados a cada documento.

## Verificación y entrega

13 de octubre de 2026: 306 pruebas de aplicación, sin fallos ni errores; una
omitida por catálogo privado no distribuido. Veinte pruebas nuevas cubren filtros,
recepción/entrega por día, clasificación, reintentos, conteos/paginación, permisos,
consultas constantes y ausencia de escrituras desde la bandeja. No hay cambios de
esquema ni dependencias. Navegador comprobado con registros ficticios y usuario
de prueba ya existente; sin ejecutar lectores, correo o servicios externos.

Esta entrega de código no acredita actualización de una demo o instalación
central. Para una instalación administrada conserva respaldo y sigue
`infra/DESPLIEGUE-Y-RECUPERACION.md`. El servidor del taller continúa pendiente y
el correo conserva su autorización y estado por separado.
