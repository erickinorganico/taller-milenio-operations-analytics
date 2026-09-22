# Contrato de entrada para clientes

`milenio.client_input` es un adaptador local para un corte de datos de taller.
Acepta un libro `.xlsx`/`.xlsm` o una carpeta de CSV. No abre conexiones,
contacta personas, modifica un sistema de negocio ni ejecuta acciones de CRM,
facturación o pagos.

## Archivos y hojas

El libro contiene `Config`, `Instrucciones`, `Ordenes`, `Facturas`, `Pagos` e
`Inventario`. Los libros `.xlsm` se leen como archivos de entrada, pero sus
macros nunca se ejecutan. Una importación CSV usa los archivos `config.csv`, `orders.csv`,
`invoices.csv`, `payments.csv` e `inventory.csv`; también acepta los nombres de
hoja en español. La primera fila reconocible de cada hoja es el encabezado, de
modo que las instrucciones y títulos de la plantilla no afectan la carga.

`Config` usa filas `campo,valor` con estos campos:

| campo | requerido | regla |
| --- | --- | --- |
| `business_name` | sí | Nombre de negocio; no requiere nombres de personas ni datos de contacto. |
| `as_of` | sí, salvo que se pase a la API | Corte explícito ISO-8601 con zona horaria. |
| `snapshot_id` | sí | Identificador del corte. |
| `synthetic` | sí | `true` o `false`; no habilita conexiones externas. |

Las columnas de entrada tienen encabezados en español en la plantilla, pero el
adaptador también acepta sus alias canónicos en inglés. El resultado siempre
usa estas tablas y claves:

| tabla | claves |
| --- | --- |
| `orders` | `order_id`, `customer_ref`, `segment`, `received_at`, `delivered_at`, `status`, `promised_at`, `block_reason`, `technician_ref`, `estimated_hours` |
| `invoices` | `invoice_id`, `order_id` opcional, `customer_ref`, `issued_at`, `due_at` opcional, `amount_mxn`, `status` |
| `payments` | `payment_id`, `invoice_id`, `paid_at`, `amount_mxn`, `method` |
| `inventory` | `part_id`, `description`, `on_hand`, `reserved`, `reorder_point`, `unit_cost_mxn` opcional |

Los estados admitidos son:

- órdenes: `received`, `in_service`, `waiting_parts`, `rework`, `ready`, `delivered`, `cancelled`;
- facturas: `issued`, `void`;
- pagos: `cash`, `card`, `transfer`;
- segmento: `particular`, `fleet`.

## Fechas, importes y blancos

Se recomienda escribir fechas como texto ISO-8601 con zona, por ejemplo
`2026-09-22T12:00:00-07:00`. Una fecha o fecha-hora nativa de Excel no tiene
zona: el adaptador la interpreta como UTC y lo deja en
`metadata.assumptions`. Una cadena ISO sin zona se rechaza. `as_of` recibido
directamente en `load_client_input(..., as_of=...)` debe ser timezone-aware.

`amount_mxn` y `unit_cost_mxn` se leen como `Decimal` y se convierten sin
pérdida a `amount_cents` o `unit_cost_cents`. Se permiten hasta dos decimales;
NaN, infinito, negativos y fracciones de centavo fallan la carga. La salida
usa fechas UTC ISO-8601 terminadas en `Z` y enteros de centavos MXN.

Un blanco opcional se devuelve como `None`, nunca como cero. Por ejemplo,
`delivered_at` desconocido no prueba que una orden no se entregó y un costo de
parte vacío no prueba que su costo sea cero.

## Forma de salida

Una carga exitosa devuelve:

```python
{
    "schema_version": 1,
    "metadata": {
        "business_name": "...",
        "as_of": "2026-09-22T19:00:00Z",
        "snapshot_id": "...",
        "synthetic": True,
        "quality": {...},
        "assumptions": {...},
    },
    "tables": {
        "orders": [...],
        "invoices": [...],
        "payments": [...],
        "inventory": [...],
    },
    "source_hashes": {"archivo.xlsx": "sha256..."},
}
```

`metadata.quality` conserva señales observadas como facturas vencidas con pago
parcial, facturas liquidadas, órdenes entregadas sin factura emitida, órdenes
canceladas excluidas de WIP, y partes con existencia reservada mayor a la disponible. Estas señales
no se convierten en ceros silenciosos. Una entrada sin registros falla con
`no_data`, evitando generar un reporte vacío con apariencia de resultado.

La carga reconcilia IDs duplicados, `invoices.order_id`, la coincidencia de
cliente entre factura y orden, `payments.invoice_id`, pagos anteriores a la
emisión y pagos que exceden el importe de la factura. Las fechas de recepción,
entrega, emisión y pago posteriores al corte fallan; `promised_at` y
`due_at` pueden estar después del corte porque representan una promesa o
vencimiento futuro.

## Errores y uso

Los errores levantan `ClientInputError`. Su atributo `.issues` es una lista de
objetos con `sheet`, `row`, `column`, `code` y `message`, por ejemplo:

```python
try:
    packet = load_client_input("client_input.xlsx")
except ClientInputError as error:
    for issue in error.issues:
        print(issue["sheet"], issue["row"], issue["column"], issue["code"])
```

Un error de calidad no debe producir un resultado analítico. Corrija la fuente
y ejecute una nueva carga; conserve el archivo original, los errores y sus
hashes fuera del repositorio si contienen datos privados.

## Plantillas

`write_client_template(..., sample=False)` genera la plantilla en blanco y
`write_client_template(..., sample=True, as_of=...)` genera un caso sintético
con órdenes `waiting_parts`, `ready`, `delivered` y `cancelled`, una orden
entregada sin factura, una factura vencida con pago parcial, una factura
liquidada y una parte escasa. `generate_client_templates` produce ambas
versiones de Excel y CSV a partir de un `as_of` que debe proporcionar la
persona que ejecuta la generación; el adaptador no usa el reloj `DEMO_NOW`.
