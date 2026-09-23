# Contrato de entrega al cliente V3

La pregunta de aceptación es: ¿puede una persona decidir qué tres casos revisar,
asignar responsables y regresar la siguiente semana sin reconstruir el análisis?
El cliente recibe archivos locales; el analista prepara cortes de datos. No hay
servidor, cuenta nueva, suscripción de inferencia, CRM ni ejecución externa.

| ID | Recorrido | Criterio observable |
|---|---|---|
| CLI-01 | Incorporación | Cuatro tablas más Config/Instrucciones admiten Excel o CSV, alias y corte explícito. Errores con hoja, fila, campo y código. Sin reporte parcial ante error. |
| CLI-02 | Priorización | Saldo = importe menos pagos vinculados. Anuladas excluidas. Cada señal tiene registro, motivo, siguiente paso, rol y evidencia. |
| CLI-03 | Operación | Canceladas fuera de WIP; entregadas sin factura vinculada activan conciliación, sin inferir ingresos perdidos. |
| CLI-04 | Partes | Disponible = existencia menos reservado. Déficit requiere revisión, sin compra ni costo supuesto. |
| CLI-05 | Revisión | Seguimiento inicia pending, sin owner. Origen e IDs validados; done requiere responsable, nota y evidencia declarada. |
| CLI-06 | Continuidad | IDs estables. Comparación conserva revisión humana; ausentes no se dan por resueltos y diferencias no se atribuyen al servicio. |
| CLI-07 | Privacidad | synthetic=false sólo genera dentro de private/. Git y empaquetador excluyen private/. Sin llamadas de modelos. |
| CLI-08 | Integridad | Hashes de resultados inmutables. Seguimiento.xlsx, reviews.jsonl y REVISION.html mutables, explícitamente fuera del recibo. |
| CLI-09 | Gerencia | Informe imprimible, búsqueda, Excel de siete hojas, guía de 30 minutos. Leer ejemplos no requiere Python. |

Todas las métricas corresponden al extracto, cuya cobertura total no se presume.
Sin filas significa sin cobertura. Para saldos se necesitan todos los pagos de
cada factura al corte; omitirlos sobrestima saldo. Se valida consistencia, no
veracidad ni completitud del universo. Sin vencimiento no se clasifica atraso.

P1: cartera con al menos 15 días de atraso, servicio con compromiso vencido o
retrabajo, disponibilidad no positiva con reservas. P2: otros atrasos, bloqueos,
preparación de entrega, conciliación y stock bajo mínimo. P3: datos faltantes.
La política es explícita, no una calificación de IA.

No se suman importes de colas superpuestas. Pagos no equivalen a efectivo,
utilidad ni recuperación atribuible. Este contrato mínimo no calcula capacidad,
margen, SLA contractual, seguridad de grúa ni autorización de contacto. V2
mantiene sus contratos sintéticos separados.

La carpeta privada no cifra ni anonimiza automáticamente; el usuario declara
el modo y aplica los accesos y retención acordados. El producto no detecta si
una muestra declarada sintética contiene datos reales. La aceptación de cliente
y el piloto real permanecen pendientes. Se desarrolla con ejemplos sintéticos.
