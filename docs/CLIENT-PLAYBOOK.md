# Playbook de entrega para clientes

Este playbook describe el uso local del paquete de diagnóstico operativo. Está
escrito para una primera lectura de 30 minutos, una reunión semanal de 20
minutos y el seguimiento de las acciones acordadas. El paquete prepara
evidencia para que responsables humanos decidan; no ejecuta decisiones de
negocio.

El demostrador público usa datos sintéticos. Un piloto con datos autorizados
requiere una copia local separada, consentimiento o base legítima documentada,
minimización, responsables nombrados, retención y aceptación del cliente. El
piloto real todavía no se ha realizado.

## Qué recibe el cliente

La corrida principal se guarda por defecto bajo `private/clients/` y debe
conservarse fuera del repositorio público. La demostración sintética puede
vivir bajo `examples/client_delivery/`.

| Artefacto | Uso en la reunión | Evidencia mínima |
|---|---|---|
| `INICIO.html` | lectura ejecutiva y agenda priorizada | cutoff, estado de calidad, decisiones abiertas y limitaciones |
| `Gerencia.xlsx` | tablas curadas para revisar excepciones | fuente, población, definición, estado de evidencia y referencia |
| `Seguimiento.xlsx` | registro editable de revisión humana | `action_id`, owner, status, target_date, note y outcome_evidence |
| `analysis.json` | paquete reproducible de análisis | input, controles, estados de evidencia y referencias |
| `receipt.json` | recibo técnico de la corrida | versión, hashes, cutoff, artefactos y resultado de controles |
| `CALIDAD.json` | errores de entrada, cuando se solicita | hoja, fila, columna, código y mensaje |

La carpeta también puede conservar `Seguimiento_original.xlsx`, `GUIA.html`,
`snapshot.json` y `warehouse.sqlite`. `Seguimiento_original.xlsx` es la copia
sellada para comparar el origen; `Seguimiento.xlsx` es la copia editable.

El contrato de columnas de `Seguimiento.xlsx` separa origen y anotación humana.
Las columnas de origen son `action_id`, `category`, `title`, `priority`,
`owner_role`, `why_now`, `recommended_next_step`, `amount_at_risk_cents`,
`source_ids`, `evidence` y `source_snapshot`. Las únicas columnas editables son
`owner`, `status`, `target_date`, `note` y `outcome_evidence`.

Se recomienda trabajar con alias o identificadores proporcionados por el
cliente. El adaptador conserva los valores recibidos y no redacciona ni
anonimiza PII; cualquier mapa interno que relacione alias con personas,
teléfonos, vehículos o cuentas debe permanecer fuera del paquete compartido.

## Ruta de ejecución

Use una carpeta nueva por cliente y por corrida. El ejemplo siguiente es una
ruta local; no publica ni envía datos.

```powershell
python -m milenio client-template `
  --output private/clients/<cliente>/Entrada.xlsx `
  --business "<cliente>"
python -m milenio client-analyze `
  --input private/clients/<cliente>/Entrada.xlsx `
  --output private/clients/<cliente>/corrida-<cutoff> `
  --errors private/clients/<cliente>/CALIDAD-<cutoff>.json
python -m milenio client-review `
  --input private/clients/<cliente>/corrida-<cutoff>/Seguimiento.xlsx `
  --report private/clients/<cliente>/corrida-<cutoff> `
  --reviewer "<nombre y rol>"
python -m milenio client-compare `
  --before private/clients/<cliente>/corrida-anterior `
  --after private/clients/<cliente>/corrida-<cutoff> `
  --output private/clients/<cliente>/comparacion-<cutoff>
```

Para practicar con la muestra sintética use una fecha explícita, separada de
la carpeta privada:

```powershell
python -m milenio client-template `
  --output examples/client_delivery/client_input_sample.xlsx `
  --sample `
  --as-of 2026-09-22T18:00:00Z `
  --business "Ejemplo sintético"
```

`client-template` sin `--sample` genera un libro en blanco con las hojas
`Config`, `Instrucciones`,
`Ordenes`, `Facturas`, `Pagos` e `Inventario`. Las cuatro últimas son las hojas
de datos; las dos primeras explican y configuran la captura. Complete en
`Config` `business_name`, `as_of`, `snapshot_id` y `synthetic` antes de
analizar. `--sample` agrega un ejemplo sintético y exige `--as-of` explícito;
no debe mezclarse con datos reales.

`client-analyze` acepta una fecha de corte declarada por el cliente. No exige
PII para funcionar, pero no elimina ni anonimiza PII y conserva los alias que
recibe. Si encuentra errores, devuelve issues JSON en la consola y, con
`--errors <ruta>`, escribe `CALIDAD.json`; mantenga esa ruta como archivo
privado junto a la corrida, no dentro de la carpeta de salida que todavía debe
crearse. Cada issue contiene `sheet`, `row`, `column`, `code` y `message`.
Corrija la fuente y genere otra corrida; no corrija manualmente una cifra del
resultado.

`client-review` registra la revisión humana de `Seguimiento.xlsx` en el reporte
existente indicado por `--report`; el registro es auto-reportado y la etiqueta
del revisor no verifica identidad o autoridad. `client-compare` compara dos
corridas con `receipt.json` de integridad verificada, un negocio/modo de datos
compatibles, un snapshot distinto y una fecha posterior. Muestra cambios de
estado y continuidad de acciones; no prueba que una acción se haya ejecutado
ni que un resultado sea atribuible al servicio. Ninguno de estos comandos
llama modelos, envía mensajes, contacta personas, modifica el CRM, despacha,
cobra, compra o cambia la fuente del cliente.

Los nueve agentes V2 y su análisis profundo siguen disponibles para el
demostrador sintético cuando se necesita una revisión especializada. No son un
requisito para la primera lectura ni para la reunión semanal de este playbook.

## Preparación antes de la primera corrida

El sponsor y el analista completan la información siguiente antes de abrir el
reporte:

- cliente, sponsor, dueño de la fuente, responsable operativo, revisor y
  aprobador de aceptación;
- pregunta o decisión concreta que se quiere responder, idealmente tres a
  cinco, y módulos incluidos;
- fuente autoritativa, periodo, fecha de corte, zona horaria, moneda, grain,
  IDs, estados y regla de deduplicación;
- campos faltantes, restringidos o desactualizados, con owner y fecha de
  resolución;
- tratamiento de consentimiento, acceso, retención y eliminación, acordado
  fuera del adaptador;
- criterio de aceptación: controles que deben cuadrar, preguntas respondidas,
  limitaciones aceptadas y próxima fecha de revisión.

La ausencia de un dato se conserva como blanco/`null` cuando el campo es
opcional. Un blanco no significa cero, aprobación, seguridad, disponibilidad,
pago ni resultado exitoso. El adaptador valida estructura, tipos, estados,
fechas, referencias y conciliaciones del extracto; no valida consentimiento,
seguridad, frescura de la fuente, ownership, retención o autorización de
negocio.

## Primera lectura en 30 minutos

### Minutos 0–5: alcance y privacidad

Abra `INICIO.html` y confirme negocio, snapshot, fecha de corte, modo de datos
y cobertura aportada. Verifique que la corrida está en `private/clients/` para
datos no sintéticos y que la copia original permanece intacta. La revisión de
consentimiento, autoridad de la fuente, acceso y retención ocurre fuera del
adaptador y debe quedar documentada por los responsables antes de compartir el
paquete.

### Minutos 5–10: calidad que cambia la decisión

Abra la sección de calidad de `INICIO.html` o `CALIDAD.json`. Revise únicamente
los controles que pueden cambiar una decisión: filas rechazadas, IDs
duplicados, referencias rotas, fechas fuera del cutoff, importes no
conciliados, pagos que exceden una factura, y faltantes de los cuatro datasets.
Cada issue debe mostrar hoja, fila, columna, código y mensaje. Consentimiento,
seguridad, frescura y ownership requieren una revisión fuera del adaptador.

### Minutos 10–20: bandeja de decisiones

Use la tabla curada de `Gerencia.xlsx`. Ordene por esta regla inicial:

1. `P1` — revisar hoy;
2. `P2` — revisar esta semana;
3. `P3` — completar información.

El producto conserva ese orden y, dentro de cada prioridad, ordena por importe
en riesgo descendente, categoría y `action_id`. Use la evidencia de fecha y
antigüedad para conversar el caso, sin convertirla en un SLA. La prioridad es
una regla de revisión del producto, no una instrucción de cobro o compra.

La política incorporada marca como `P1` una cartera con al menos 15 días de
atraso y un servicio con promesa vencida o retrabajo. Los faltantes de
información, como una orden sin promesa o una factura sin vencimiento, se
mantienen en `P3`. El inventario puede producir `P1` cuando no hay unidades
disponibles pero existen reservas; en los demás faltantes de inventario se usa
`P2`.

Cada fila debe responder en una sola lectura: qué caso se revisa, qué registro
lo origina, qué evidencia existe, qué falta, qué rol debe revisarlo y por qué
la regla lo ordenó.

### Minutos 20–30: primera revisión y acciones

En `Seguimiento.xlsx`, revise cada `action_id` y use solamente estos estados:
`pending`, `accepted`, `in_progress`, `done` o `dismissed`. Complete `owner`,
`target_date`, `note` y `outcome_evidence` únicamente con información humana.
`accepted` e `in_progress` requieren `owner` y `target_date`; `dismissed`
requiere `note`; `done` requiere `owner`, `note` y `outcome_evidence`.
Para pedir información, diferir o dejar un bloqueo, conserve el estado que
corresponda y explíquelo en `note`; no invente un estado nuevo. El resultado de
esta sesión es una agenda que puede leer el cliente, no una modificación de su
sistema.

La primera lectura se acepta cuando una persona del cliente puede identificar
las tres decisiones prioritarias, su owner, su fecha, la evidencia faltante y
la siguiente revisión sin navegar las tablas físicas completas.

## Reunión semanal de 20 minutos

La reunión usa la corrida más reciente y, cuando existe, el resultado de
`client-compare`.

| Tiempo | Actividad | Registro que queda |
|---|---|---|
| 0–3 min | confirmar cutoff, frescura, calidad y cambios frente a la corrida anterior | estado de corrida y pendientes de calidad |
| 3–8 min | revisar P1 y confirmar evidencia con el owner de la fuente | status y nota en `Seguimiento.xlsx` |
| 8–14 min | revisar P2 y P3 según impacto y datos faltantes | owner, target_date y nota |
| 14–18 min | revisar acciones con estado `pending`, `accepted`, `in_progress`, `done` o `dismissed` | estado y evidencia de resultado |
| 18–20 min | confirmar próximo export, próxima revisión y aceptación | fecha, responsable y preguntas abiertas |

No se debe llenar la reunión con métricas sin decisión. Toda cifra debe
declarar cutoff, población, definición, grain y limitación. Toda revisión debe
conservar su `action_id`, `source_snapshot` y evidencia de origen. Si no hay
resultado observado, `outcome_evidence` queda vacío y la nota explica qué
falta.

## Seguimiento de una acción

Entre reuniones, el owner actualiza únicamente `Seguimiento.xlsx` o una copia
controlada. En la próxima corrida:

1. conserve el `action_id`, `source_snapshot` y las columnas de origen sin
   modificarlos;
2. complete solamente `owner`, `status`, `target_date`, `note` y
   `outcome_evidence`;
3. marque la acción como `done` solo cuando existan owner, nota y evidencia del
   resultado; el resultado sigue siendo auto-reportado;
4. use `pending`, `accepted`, `in_progress` o `dismissed` cuando la acción no
   pueda marcarse como `done`;
5. importe el libro con una etiqueta de revisor auto-reportada y conserve el
   `reviews.jsonl` y `REVISION.html` generados;
6. compare la siguiente corrida con `client-compare`; un registro ausente se
   marca para verificar, nunca como resuelto.

El registro permite recorrer `evidence → action_id → owner/status/note →
outcome_evidence` sin cambiar el snapshot original. Los campos de origen son
inmutables durante la importación de la revisión.

## Caso trabajado sintético

El paquete de demostración de entrada contiene un patrón de servicio y
cobranza que sirve para practicar la reunión. `ORD-002` aparece `in_service` y
se vincula con `INV-001`. La factura sintética es de $1,500.00 MXN, hay un pago
`PAY-001` de $500.00 MXN y queda un saldo documentado de $1,000.00 MXN. La
orden tiene además una promesa anterior al corte, por lo que el analizador la
coloca en `P1`; la factura tiene un atraso corto y se revisa según la regla de
cartera.

La pregunta de revisión no es “cobrar ahora”. Es: “¿El saldo y la aplicación
del pago están documentados y quién debe confirmar el siguiente paso interno?”
La fila contiene el `action_id`, el caso, el importe en centavos, la evidencia,
el rol sugerido y el siguiente paso. Una persona puede llenar `owner`,
`status`, `target_date`, `note` y `outcome_evidence`; no puede convertir la
anotación en un cobro. El ejemplo es sintético y no demuestra una deuda real,
un incumplimiento, una recuperación ni un resultado comercial.

## Evidencia, roles y entrega

El analista conserva `receipt.json`, `analysis.json`, `CALIDAD.json` si existe,
la entrada original, `Gerencia.xlsx`, `Seguimiento.xlsx` y el reporte de
comparación. El cliente conserva autoridad sobre definiciones, prioridades,
seguridad, dinero, contacto y aceptación.

| Rol | Responsabilidad |
|---|---|
| Sponsor | confirma preguntas prioritarias y alcance |
| Dueño de fuente | confirma autoridad, frescura y significado de campos fuera del adaptador |
| Owner operativo | valida el hallazgo y ejecuta fuera del paquete cualquier acción autorizada |
| Revisor | decide, pide información o rechaza una propuesta |
| Analista | prepara, reconcilia, documenta límites y no ejecuta acciones externas |
| Aprobador de aceptación | firma el estado de la entrega y sus pendientes |

La aceptación humana se registra en `docs/CLIENT-ACCEPTANCE.md` o en la copia
controlada de la entrega. Los campos de nombre, rol, fecha, decisión y firma
deben permanecer vacíos hasta que una persona los complete. El estado
`accepted` de una fila solo registra una revisión humana; no acredita que la
acción de negocio haya ocurrido.

## Límites del servicio

El paquete no es CRM, ERP, sistema de despacho, sistema fiscal, sistema de
pagos ni mensajería. No contacta clientes o prospectos, no publica campañas,
no diagnostica vehículos, no autoriza reparaciones, no decide seguridad, no
fija precios, no agenda, no compra partes y no mueve dinero. Un `accepted` en
`Seguimiento.xlsx` sigue siendo una anotación humana; no ejecuta la acción ni
verifica por sí sola su resultado.
