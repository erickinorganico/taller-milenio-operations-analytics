# Cotizar los servicios de una foto

La orden conserva la solicitud observada y el presupuesto que revisa el equipo.
El paso **Cotizar servicios de las fotos** evita volver a capturar los conceptos.

1. Revisa y aplica la foto al taller mediante Capturar documentos.
2. En la orden, avanza a Inspección y abre Información recibida en fotos.
3. Pulsa **Cotizar servicios de las fotos**. Selecciona los conceptos que usarás.
4. Confirma tipo, cantidad y precio. Si no aparecen en la foto, complétalos;
   el costo desconocido puede quedar vacío. Una refacción necesita un SKU existente.
5. Revisa la tasa aplicable y confirma los datos. Guarda en borrador de presupuesto.
6. Presenta el presupuesto y registra la autorización del cliente por el flujo habitual.

Si existe un borrador, se agregan líneas a esa versión y se conservan sus líneas
manuales. Si el presupuesto ya fue presentado, crea explícitamente una nueva
versión desde Cotización. Un presupuesto autorizado queda protegido.

La tabla de fotos indica qué conceptos siguen pendientes y cuáles pertenecen al
presupuesto activo. Cada línea de presupuesto enlaza a sus documentos de origen.
La solicitud observada conserva sus cantidades/importes originales aunque el
equipo corrija esos valores al cotizar. No se convierte un dato desconocido en cero.

Se procesan hasta 50 conceptos por confirmación; vuelve a abrir el paso para
continuar con los restantes. Repetir el mismo guardado devuelve su presupuesto
sin duplicar líneas. Los cambios posteriores en fuente, orden o presupuesto
invalidan una revisión pendiente, que dura 15 minutos y pertenece a quien la abrió.

El guardado es transaccional y auditado. No presenta, autoriza ni cobra el presupuesto,
no modifica stock ni crea reservas, y requiere Recepción o Gerencia. La nueva
migración es `workshop.0006_photo_quote_provenance`; aplicar tras un respaldo mediante
el instalador del servidor o, en demo, su lanzador. Las líneas anteriores conservan
origen vacío y siguen funcionando.

Las pruebas del flujo utilizan datos ficticios; el piloto con órdenes reales y
los conectores de recepción de fotos siguen teniendo su aceptación propia.
