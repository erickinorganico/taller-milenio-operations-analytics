# Base de datos del taller

El menú **Base de datos** permite consultar clientes, vehículos, refacciones, proveedores, órdenes, servicios cotizados y cobros. Las fuentes completas siguen disponibles debajo de los siete conjuntos y desde **Ver todos los campos**. Las tablas se pueden buscar y paginar, y sus relaciones llevan al registro correspondiente.

## Actualizar desde Excel, CSV o Google Sheets

1. Descarga el **Excel actual** del conjunto que quieres actualizar. Para datos nuevos, descarga una plantilla vacía desde **Importar o actualizar**.
2. Conserva los encabezados y los ID existentes. Puedes editar las demás columnas y añadir filas nuevas dejando el ID vacío. Una celda vacía borra ese valor cuando el campo admite estar vacío. Las filas ausentes del archivo no se eliminan.
3. Sube el archivo y elige **Agregar nuevos y actualizar existentes** o **Sólo agregar nuevos**.
4. Revisa los resultados por fila y los valores anteriores/nuevos antes de **Confirmar y guardar**. La revisión dura 15 minutos y se invalida si cambian los datos que utiliza. Se guarda todo el archivo en una sola transacción o no se guarda ninguna fila.

Para Google Sheets, abre el Excel descargado en Sheets, edita y usa **Archivo → Descargar → Microsoft Excel (.xlsx)** o **Valores separados por comas (.csv)**. La integración de esta versión es carga manual de archivos; no lee enlaces ni sincroniza una cuenta de Google.

Excel requiere una sola hoja sin fórmulas ni errores. CSV requiere UTF-8 y admite coma, punto y coma o tabulador. El límite por carga es 1 MB y 1,000 filas. Las exportaciones de más de 1,000 registros deben dividirse antes de volver a cargar. Guarda teléfonos, placas y códigos como texto para conservar ceros iniciales. Fechas: `AAAA-MM-DD HH:MM`; sin zona explícita se usa la zona configurada del taller. Los importes usan punto decimal y no incluyen símbolo de moneda.

## Identificación y reglas por conjunto

| Información | Identificación y actualización |
| --- | --- |
| Clientes | ID o nombre único. Tipo `individual` o `fleet`. Un ID permite cambiar el nombre manteniendo sus vehículos e historial. |
| Vehículos | ID, placa o VIN; placa y VIN no pueden identificar vehículos distintos. `customer_name` debe identificar un único cliente existente. |
| Refacciones | ID o SKU. Se actualizan nombre, unidad, costo, precio y reposición; existencias/reservas se mantienen. Las entradas físicas usan compras o ajustes desde Refacciones. |
| Proveedores | ID o nombre único. Se actualizan nombre, teléfono y correo. |
| Órdenes | ID o folio. Nuevas órdenes entran en Recepción; se actualizan motivo, entrega prometida y kilometraje de órdenes abiertas. Sólo se cambia el vehículo en Recepción. No se importan etapas, autorizaciones ni evidencia de calidad. |
| Servicios cotizados | ID o descripción/tipo/refacción dentro de una cotización. `order_number` es el folio; `quote_version` la versión. Una versión vacía usa el único borrador o crea uno si la orden está en Inspección o Espera autorización. Se modifican únicamente borradores; los conceptos autorizados se conservan. Tipos `labor`, `service`, `part`; sólo `part` requiere `part_sku`. Los conceptos nuevos requieren autorización antes de contabilizarse como servicios aprobados en analytics. |
| Cobros | Comprobante existente y `idempotency_key` único. Repetir clave y contenido conserva el pago original. Una clave con datos distintos se rechaza. El total del archivo no puede exceder el saldo y un comprobante anulado no admite cobros nuevos. Métodos `cash`, `transfer`, `card`, `other`. `received_at` vacío usa el momento de carga. |

Los cobros son registros administrativos de pagos ya recibidos; cargar un archivo no realiza una transferencia bancaria. Los comprobantes se emiten desde el flujo de entrega existente.

## Consulta, trazabilidad y dashboard

La carga confirmada aparece inmediatamente en las tablas y crea un nuevo corte analítico cuando hubo filas nuevas o modificadas. Los cortes históricos se conservan. El dashboard respeta su periodo y sólo incluye los registros que cumplen las reglas de cada métrica.

Gerencia puede importar. Gerencia, Administración y Consulta gerencial pueden consultar y descargar; el resto conserva sus permisos de operación. Cada cambio registra responsable y valores anteriores/nuevos, y la portada muestra las últimas cinco cargas. Las exportaciones excluyen cuentas, sesiones y credenciales.

El Excel descargado conserva los valores como texto literal y es la opción preferida para editar y volver a cargar. El CSV antepone una comilla a valores que podrían interpretarse como fórmulas al abrirlos en una hoja de cálculo; revisa esos valores si vuelves a cargar un CSV exportado.

## Verificación

Las pruebas en `workshop/tests/test_data_exchange.py` cubren creación/actualización por Excel, ausencia de escrituras durante la vista previa, cambio concurrente y recibo de otro usuario, CSV con punto y coma, exportación y recarga con ID/ceros, creación de órdenes, servicios en borrador, pagos repetidos y sobrepago conjunto, archivos inválidos, filas repetidas, límite de filas, fórmulas literales, caducidad y permisos. La suite previa de importación CSV sigue en `workshop/tests/test_import.py`.

Verificación local del 1 de octubre de 2026: 132 pruebas de `workshop.tests` pasaron; tras ajustar la búsqueda por relaciones y el acceso a todos los campos de servicios, se repitieron las 32 pruebas de importación/intercambio y HTTP, todas correctas. `makemigrations --check --dry-run` no detectó cambios. La revisión visual utilizó respuestas HTML reales de Django con datos sintéticos en una base separada, a tamaño normal y 390 px; portada y formulario no desbordaron el documento y la tabla mantuvo su desplazamiento interno. El detalle de cambios mostró el teléfono anterior y el nuevo. Esto verifica las pantallas de ejemplo; no acredita un piloto con datos reales ni una sincronización con Google.
