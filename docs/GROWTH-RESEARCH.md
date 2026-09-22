# Investigación de crecimiento con fuentes públicas

## Objetivo y límite

Este playbook prepara una lista de organizaciones para investigación humana de flotillas y mantenimiento. No crea leads, contactos, oportunidades ni campañas automáticamente. No autoriza contacto y no convierte señales públicas en intención de compra.

La implementación actual solo trabaja con registros sintéticos. Aplicar este método a datos reales exige una fuente aprobada, propósito definido, revisión de privacidad y decisión humana antes de escribir en cualquier CRM.

## Fuentes oficiales

| Fuente | Uso permitido | Límite explícito |
|---|---|---|
| [Directorio Estadístico Nacional de Unidades Económicas, INEGI](https://www.inegi.org.mx/temas/directorio/) | descubrir establecimientos por actividad y geografía | un establecimiento no equivale a una cuenta calificada |
| [API del DENUE](https://www.inegi.org.mx/servicios/api_denue.html) | consultar identificación, ubicación, actividad, estrato de personal y datos publicados | requiere token; `Estrato` significa personal ocupado, no tamaño de flotilla |
| [Data México: reparación y mantenimiento automotriz](https://www.economia.gob.mx/datamexico/es/profile/industry/automotive-repair-and-maintenance?redirect=true) | contexto sectorial para formular hipótesis y preguntas | contexto agregado, no evidencia sobre una empresa concreta |

Fuentes revisadas el 2026-09-22. Antes de una corrida real, confirme términos, vigencia, campos permitidos y reglas de uso directamente en la fuente.

## Flujo de investigación

### 1. Definir el territorio y la hipótesis

Documente municipio/área, clases de actividad, radio, periodo y motivo comercial. Ejemplo de hipótesis válida: “establecimientos con operación móvil o múltiples sitios pueden requerir revisión de mantenimiento”. No afirme que poseen vehículos sin evidencia.

### 2. Consultar DENUE con token propio

La API documenta métodos de búsqueda por condición, entidad, área/actividad y estrato. Guarde:

- fecha/hora y método de consulta;
- parámetros geográficos y de actividad;
- ID/CLEE de la unidad;
- nombre, razón social, clase, ubicación y estrato tal como fueron publicados;
- URL o referencia de la fuente.

No incluya el token en archivos, logs, capturas, commits o paquetes públicos.

### 3. Normalizar sin inventar

Use una tabla de investigación separada de las entidades operativas. Para cada campo marque `observed`, `inferred`, `unknown` o `review`.

Reglas obligatorias:

- `Estrato` → señal de personal ocupado del establecimiento; nunca mapear a `fleet_accounts.fleet_size`.
- teléfono/correo publicado → dato de directorio sujeto a revisión; nunca crear `contacts.consent=true`.
- nombre similar → candidato de identidad; no fusionar sin una llave o revisión.
- actividad económica → compatibilidad sectorial; no prueba necesidad, presupuesto o autoridad.
- ausencia de contacto → `unknown`; no fabricar nombres, cargos, teléfonos o correos.

### 4. Calificar para investigación humana

Use un puntaje de 0 a 10 solo para ordenar investigación, no para predecir compra:

| Criterio | Puntos | Evidencia aceptable |
|---|---:|---|
| actividad compatible con operación vehicular | 0–2 | clase/descripcion oficial y regla documentada |
| proximidad dentro del territorio acordado | 0–2 | coordenadas/ubicación oficial y radio aprobado |
| múltiples establecimientos vinculables con certeza | 0–2 | razón social/identificador consistente, revisado |
| señal pública explícita de vehículos o servicio móvil | 0–2 | sitio oficial o fuente pública citada; no inferencia por estrato |
| información suficiente para validar identidad | 0–2 | ID/CLEE, razón social, ubicación y fuente |

Estados recomendados:

- `0–3`: descartar o mantener como contexto agregado;
- `4–6`: investigar identidad y necesidad; no contactar;
- `7–8`: preparar ficha para revisión comercial;
- `9–10`: ficha completa para que una persona decida si procede contacto bajo política aprobada.

Un puntaje alto no crea una oportunidad. `opportunities` solo debe recibir un registro tras decisión humana con `fleet_account_id`, título, valor en centavos cuando exista una base aprobada, siguiente paso, fecha y estado. Si no existe precio o valor autorizado, no inventarlo.

## Mapeo al contrato existente

| Entidad | Campo | Regla de escritura futura |
|---|---|---|
| `fleet_accounts` | `customer_id`, `industry`, `fleet_size`, `owner` | crear solo tras validación; `fleet_size` exige evidencia real distinta de DENUE `Estrato` |
| `contacts` | `fleet_account_id`, `name`, `role`, `contact`, `consent` | no crear identidad/cargo/consentimiento a partir de una suposición |
| `opportunities` | `title`, `value_cents`, `next_step`, `follow_up_at`, `status` | requiere decisión y base comercial; nunca usar puntaje como valor monetario |
| `contracts` | SLA, fechas, aprobación, estado | solo contrato autorizado; ninguna fuente pública lo establece |

El workbench actual ofrece lectura y borradores. No incluye adaptador para DENUE, CRM, mensajería o escritura externa.

## Ficha de investigación

```text
ID interno de candidato:
Fecha y analista:
Fuente oficial / URL:
ID DENUE o CLEE:
Nombre y razón social observados:
Actividad y ubicación observadas:
Estrato de personal ocupado (no flotilla):
Señal vehicular explícita y fuente:
Campos desconocidos:
Puntaje y evidencia por criterio:
Riesgo de identidad/privacidad:
Pregunta que debe resolver una persona:
Decisión: descartar / investigar / preparar ficha / autorizar paso posterior
```

## Control semanal

Reporte solo conteos por estado de investigación, cobertura de fuentes, duplicados, campos desconocidos y decisiones humanas. No presente contactos obtenidos, envíos, respuestas, pipeline, conversión, ROI o ingresos cuando no existen. Cualquier contacto futuro debe ocurrir fuera del toolkit, con política, consentimiento/base legal y autorización aplicables.
