# Fotos desde el celular

## Recibir un vehículo que ya está registrado

En **Órdenes de trabajo → Recibir vehículo**, busca por placa, cliente o modelo y **selecciona el vehículo**. La búsqueda admite placas con o sin guion y nombres con o sin acento. Escribe el motivo de la visita y toca **Crear orden de trabajo**. Si el vehículo ya tiene trabajo abierto, aparecen los folios, sus etapas y sus motivos. Abre el folio que corresponda. Si el cliente trae otro trabajo, marca **Es un trabajo distinto para este vehículo** y toca **Crear otra orden**. Los campos que ya llenaste siguen en la pantalla. Si otra persona abrió un folio entre tanto, verás la lista actualizada. Un vehículo con todas sus órdenes entregadas o canceladas pasa directamente a la nueva visita.

## Fotografiar un hallazgo

1. Entra en la dirección del taller con tu cuenta. Abre **Mis órdenes**, elige el folio y comprueba las placas. Los técnicos trabajan en sus órdenes asignadas.
2. En **Inspección y fotos**, escribe el punto revisado, elige el resultado y añade las observaciones. La orden permite registrar puntos durante la etapa **Inspección**.
3. Usa **Tomar foto** para abrir la cámara trasera si el navegador lo permite. **Elegir una foto de la galería** abre un archivo existente. Puedes registrar el punto sin foto o registrar otro punto para añadir más evidencia.
4. Comprueba la vista previa y el folio. Si elegiste la foto equivocada, **Quitar foto** conserva tus observaciones y te permite elegir otra. Toca **Guardar inspección** y espera **Inspección guardada en la orden**. Si intentas salir con cambios pendientes, los navegadores compatibles permiten cancelar la salida. Mantén la página abierta hasta recibir la confirmación.

Recepción puede dejar el mismo folio abierto en otro dispositivo. La lista visible consulta cambios cada 20 segundos y al volver a la pestaña. **Actualizar** consulta de inmediato. La actualización conserva el texto que alguien esté escribiendo. La miniatura abre la copia privada en tamaño completo. Para revisar el cambio en la bitácora general, vuelve a abrir el folio.

## Si falla la conexión

El celular necesita internet para guardar. Si ves **Sin confirmación**, mantén el formulario abierto, recupera la conexión y pulsa **Guardar inspección** de nuevo. El servidor reconoce el mismo envío, incluso si ya guardó la foto antes del corte. Una captura nueva recibe otro identificador.

Si venció la sesión, inicia sesión con la misma cuenta en otra pestaña, regresa a la primera y reintenta. La aplicación vuelve a comprobar la cuenta antes de transmitir. Si cerraste o recargaste la pestaña, comprueba el folio y su lista antes de crear el punto otra vez. El borrador y la vista previa viven en la memoria de esa página.

## Tamaño, formatos y privacidad

El formulario móvil con JavaScript permite elegir una imagen de hasta 25 MiB que el navegador pueda abrir. Reduce en el dispositivo las fotos de más de 2400 px en su lado largo o más de 5 MiB y muestra la copia que se enviará. Para HEIC/HEIF la compatibilidad depende del navegador. Si aparece un error, exporta una copia JPEG o selecciona **Más compatible** en los ajustes de cámara del iPhone.

El servidor comprueba el archivo por su contenido y acepta una foto fija JPEG, PNG o WebP de hasta 5 MiB y 20 megapíxeles. También aplica estos límites si el navegador envía el formulario sin JavaScript. Corrige la orientación, genera un nombre interno y guarda una copia JPEG de hasta 2400 px por lado, sin los metadatos EXIF del dispositivo. Los accesos al archivo requieren una sesión con permiso actual para ver esa orden. Una copia descargada por el usuario queda bajo su control. Las fotos anteriores a esta versión conservan su archivo y metadatos originales.

Las imágenes de inspección y las hojas se procesan de una en una en cada proceso web para limitar el pico de memoria del servidor. Pueden llegar solicitudes de varios técnicos a la vez. Sólo la conversión de imagen espera su turno. En la nube económica, base y fotos viven en el volumen privado y entran juntas en el respaldo cifrado. [Respaldo y recuperación](backup/README.md)

## Fotografiar una hoja para llenar campos

En **Documentos y excepciones**, recepción sube la foto de la hoja. El lector local prepara un borrador. Compara placa, folio, servicios y datos reconocidos contra el original, corrige y confirma la revisión. Usa la vista previa para elegir la orden y aplicar los campos. Este flujo guarda la hoja como documento vinculado y permite rastrear el origen de los datos. [Flujo de foto a presupuesto](../../docs/FOTOS-A-PRESUPUESTO.md)

## Verificación reproducible

Desde la raíz del repo, con dependencias web instaladas y un entorno desechable:

```sh
MILENIO_MODE=test MILENIO_DATA_DIR="$(mktemp -d)" python manage.py test workshop.tests.test_mobile_inspection workshop.tests.test_document_capture
```

El ensayo de interfaz abre un taller temporal en loopback y sesiones de Chromium independientes. Requiere Playwright, Chromium y Pillow en el entorno de pruebas. El intérprete pasado en `--app-python` debe tener instaladas las dependencias web. Sirve para probar la vista previa, un acuse perdido, el reintento desde la misma cuenta y la llegada a recepción sin recargar la página.

```sh
python infra/nube/tests/fotos_navegador.py --app-python /ruta/al/python-del-taller
```

El 25 de noviembre de 2026 el ensayo local pasó con Chromium a 390 px y 1280 px. Un archivo de 4032 × 3024 quedó en 2400 px en la vista previa. Tras descartar la respuesta HTTP de un envío ya guardado, el cambio de usuario quedó bloqueado y el técnico original pudo reautenticarse y reintentar sin duplicar la foto. La orden abierta en recepción mostró el punto automáticamente y conservó su borrador. También pasaron dos cargas simultáneas directas de 12 MP y dos reintentos concurrentes con el mismo identificador. La prueba usó datos ficticios.

Antes de activar el servicio, en un Android o iPhone real abre el folio de ensayo, autoriza la cámara y guarda una foto de prueba desde datos móviles. Comprueba el mismo punto y abre su foto desde recepción con Wi-Fi. Ese paso verifica el permiso de la cámara, el dominio, el certificado público y la red móvil del taller.
