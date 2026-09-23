# Retrospectiva V5

Fecha: 22 de septiembre de 2026. Cuatro fases y nueve planes cerrados técnicamente; entrega como candidato para piloto.

## Resultado

Se convirtió el toolkit analítico en una aplicación que captura trabajo diario y usa esos mismos registros para explicar indicadores y propuestas. La evidencia diferencia código, pruebas, inferencia real, instalación y aceptación comercial.

## Lo que funcionó

Contratos de dominio y propiedad de archivos permitieron trabajar con Sol y Luna sin reemplazar cambios ajenos. Los tests transaccionales descubrieron errores reales de roles, evidencia obsoleta y estados; la auditoría independiente encontró un enlace de exportación improcedente. Backup/restore se comprobó además desde un entorno nuevo.

## Lo que requirió retrabajo

Se generaron candidatos ZIP antes de congelar código/documentos, por lo que sus hashes tuvieron que regenerarse. La autenticación vista desde el sandbox no equivalía a la del usuario de Windows: verificar la CLI oficial bajo el usuario real permitió ejecutar el modelo. Un mock de CLI dependía de un binario local y falló en CI Windows; se aisló el resolver. Un mensaje de diagnóstico añadido al assert equivocado fue detectado y corregido antes de la suite final.

## Reglas para la siguiente iteración

Congelar implementación, verificar, auditar documentos y sólo entonces empaquetar. Comprobar identidad y entorno al diagnosticar autenticación sin leer ni copiar secretos. El recibo real del proveedor es distinto de un test con mocks. Mantener la aceptación del taller como evidencia separada.

## Costos y modelos

Se utilizaron modelos nativos Sol y Luna y una comprobación de inferencia GPT-6 Luna por la sesión ChatGPT. No se midió el costo total ni se estiman ahorros. No se incorporaron proveedores de inferencia facturados por separado.
