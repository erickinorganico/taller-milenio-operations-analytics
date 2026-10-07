# Revisión de mejoras y piloto de documentos

**Actualización vigente, 6 de octubre de 2026:** la captura ya incluye lectura
visual con GPT Luna y aplicación revisada a clientes, vehículos, órdenes y
servicios solicitados. Ver [continuidad de captura operativa](CAPTURA-OPERATIVA-CONTINUIDAD.md).
El resto de este documento conserva el corte histórico del piloto del 1 de octubre.

Revisión del código y los flujos de la demo, 1 de octubre de 2026. Las cifras de
la demo son ficticias: las prioridades reflejan facilidad de uso y control del
proceso, no un diagnóstico de los resultados reales de Milenio.

| Área | Lo que ya existe | Mejora aplicada en esta revisión |
| --- | --- | --- |
| Control de órdenes | Etapas protegidas, responsable, fecha, historial y calidad obligatoria | Indicación del siguiente paso dentro de cada orden; enlaces a órdenes sin responsable, sin fecha y vencidas |
| Captura de información | Formularios y Excel/CSV con revisión previa | Bandeja independiente para fotos de órdenes y hojas de servicio, lectura local, corrección y Excel/CSV |
| Evidencia | Fotos por punto de inspección con acceso protegido | Capturas de documentos privadas, identificación de fotos repetidas y registro de quién revisó |
| Comprensión | Guía general, métricas y fuentes | Guía del piloto y nombres más claros de los disparadores automáticos |
| Automatización | Revisiones por intervalo/eventos, propuestas vigentes y tareas después de aceptación | Lectura de una foto por ciclo en el trabajador existente, fuera de las solicitudes del navegador |

## Oportunidades siguientes, en orden de prioridad

| Prioridad | Cambio concreto | Disparador / control | Cómo verificarlo |
| --- | --- | --- | --- |
| 1 | Tablero por etapa con edad del bloqueo | Tiempo desde el último cambio de etapa; responsable visible | Cada orden tiene etapa, siguiente acción y tiempo de espera; distinguir reparación de espera de piezas |
| 1 | Checklist guiado por etapa | Inspección → presupuesto → autorización → trabajo → calidad → entrega | Mostrar sólo acciones pertinentes y explicar requisitos faltantes antes de guardar |
| 1 | Pendientes con responsable y vencimiento | Aceptación de propuesta; ya existen alertas de órdenes vencidas, piezas bajas y datos incompletos | Sugerir responsable/plazo, confirmar asignación y evitar tareas duplicadas |
| 1 | Validación del formato real del taller | 20–30 hojas impresas y manuscritas, con permiso de uso del taller | Comparar folio, placas, kilometraje y servicios contra el original; medir correcciones y tiempo por hoja |
| 2 | Vincular documento revisado a la orden | Folio y vehículo coincidentes | Previsualizar vínculo; nunca crear duplicados ni cambiar una orden cerrada automáticamente |
| 2 | Crear borrador operativo desde captura | Datos revisados y vehículo existente | Reutilizar los servicios de dominio y la importación con vista previa; conservar origen y validaciones |
| 2 | Recepción de compras con foto del comprobante | Entrega de piezas; cantidad ordenada frente a recibida | Identificar faltantes antes de ingresar existencias; revisión de Refacciones |
| 2 | Resumen diario por responsable | Al inicio del turno y al cambiar una promesa | Pendientes internos, sin enviar WhatsApp/correos hasta configurar y autorizar canales |
| 2 | Estado de salud y continuidad | Último análisis, cola, error, último respaldo | Mensajes de recuperación comprensibles y restauración ensayada |
| 3 | Google Sheets conectado | Fuente elegida y permisos definidos | Dirección de sincronización, cambios por fila, duplicados y conflictos visibles |
| 3 | Conciliación de cobros | Comprobante administrativo frente a movimiento bancario | Diferencias revisadas por Administración; el sistema actual registra cobros, no concilia bancos |
| 3 | Acceso desde celular | Despliegue con HTTPS y acceso por rol | Subir una foto real desde cámara; el servidor actual escucha sólo en el equipo local |

Las alertas de inventario bajo, órdenes vencidas y problemas de calidad de datos
ya se calculan en los revisores. La oportunidad está en hacer su resolución más
directa y medible. La asignación automática, avisos externos y sincronización de
Sheets permanecen propuestas para una etapa posterior.

## Piloto disponible: foto → revisión → Excel

En **Capturar documentos · Piloto**:

1. Sube una fotografía JPEG, PNG o WebP de una hoja de orden/servicio (máximo
   5 MB y 20 megapíxeles). En la demo también puedes probar una hoja ficticia.
2. El trabajador lee el texto en segundo plano con OCR de Windows. Se procesan
   las fotos por turno; la pausa de la cola detiene nuevas lecturas. Mantén el
   servidor abierto. Si el lector no está disponible, puedes capturar manualmente.
3. Compara la foto con folio, cliente, teléfono, placas, vehículo, kilometraje,
   solicitud y servicios propuestos. El lector identifica encabezados explícitos;
   una tabla arbitraria o escritura a mano puede requerir captura manual.
4. Corrige los campos y marca la confirmación de revisión. Sólo entonces se
   habilitan las descargas.
5. El Excel tiene **Orden revisada** y **Servicios revisados**; incluye el
   identificador del documento, revisor y fecha. El CSV contiene una fila con
   todos los datos. Puedes abrir ambos en Excel o Google Sheets.

Este archivo es un registro revisado del piloto; no es todavía la plantilla de
importación operativa. El piloto conserva el documento y los datos en la bandeja,
sin crear órdenes, cotizaciones, autorizaciones, pagos ni existencias.

Las fotos se guardan en la carpeta privada de la instalación, con nombres
generados y sin metadatos de cámara. El acceso corresponde a Gerencia/Recepción.
No se envían fotos a un servicio externo. El lector usa los idiomas OCR presentes
en Windows; [Microsoft documenta esta disponibilidad y selección de idioma](https://learn.microsoft.com/en-us/uwp/api/windows.media.ocr.ocrengine.trycreatefromuserprofilelanguages).

## Qué medir antes de ampliar el piloto

- Número de hojas intentadas y leídas; fotos repetidas y fallos de lectura.
- Tiempo desde subir hasta terminar la revisión humana.
- Exactitud por campo contra una transcripción verificada, separando texto
  impreso y manuscrito. No confundir una lectura terminada con datos correctos.
- Correcciones por folio y placas: letras O/I y números 0/1 pueden confundirse.
- Tiempo de carga de otras pantallas mientras se procesan documentos.

La prueba inicial usó una hoja ficticia y el lector real de Windows en español.
Leyó el documento y propuso campos, pero confundió caracteres de folio y placas;
por eso la revisión humana es parte obligatoria del recorrido. Una sola muestra
no permite afirmar exactitud sobre las hojas reales del taller.

Validación final: 144 pruebas aprobadas, incluida protección por rol, fotos
repetidas, lectura interrumpida, captura manual con cola pausada, revisión
concurrente y exportación literal de texto. El recorrido en la interfaz produjo
un Excel descargado con dos hojas y dos servicios, después de corregir folio
y placas. La migración de la bandeja está aplicada en la demo; se conservó un
respaldo verificado antes de reiniciarla.
