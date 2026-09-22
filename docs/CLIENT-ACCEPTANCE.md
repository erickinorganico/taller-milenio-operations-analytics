# Acta de alcance y aceptación del paquete cliente

Plantilla para completar con el cliente. Los campos de nombres, decisiones,
fechas y firmas se dejan en blanco hasta que una persona autorizada los
confirme. Una corrida técnica aprobada no equivale a una aprobación de negocio,
seguridad, contacto, pago o producción.

## 1. Identificación de la entrega

| Campo | Valor |
|---|---|
| Cliente | `[ ]` |
| Sponsor | `[ ]` |
| Corrida / versión | `[ ]` |
| Ruta local privada | `[ ]` |
| Fecha de entrega | `[ ]` |
| Analista responsable | `[ ]` |
| Snapshot ID / hash | `[ ]` |
| Fecha de corte y zona horaria | `[ ]` |
| Periodo analizado | `[ ]` |
| Fuente y propietario | `[ ]` |
| Retención y eliminación acordadas | `[ ]` |

## 2. Preguntas y alcance aceptados

| Pregunta de decisión | Dataset | Fuente declarada | Owner de validación | Estado |
|---|---|---|---|---|
| `[ ]` | `[ ]` | `[ ]` | `[ ]` | `[ ]` |
| `[ ]` | `[ ]` | `[ ]` | `[ ]` | `[ ]` |
| `[ ]` | `[ ]` | `[ ]` | `[ ]` | `[ ]` |
| `[ ]` | `[ ]` | `[ ]` | `[ ]` | `[ ]` |
| `[ ]` | `[ ]` | `[ ]` | `[ ]` | `[ ]` |

| Elemento | Incluido / excluido | Nota |
|---|---|---|
| `Ordenes` | `[ ]` | `[ ]` |
| `Facturas` | `[ ]` | `[ ]` |
| `Pagos` | `[ ]` | `[ ]` |
| `Inventario` | `[ ]` | `[ ]` |
| Otros módulos V2 | `[ ]` | fuera del flujo client-ready de cuatro datasets |
| PII, notas libres y documentos | `[ ]` | `[ ]` |
| Consentimiento / anonimización | `[ ]` | `[ ]` |

## 3. Evidencia y calidad

Marque cada control solamente después de revisar la evidencia de la corrida.

- [ ] El input original está conservado en una ubicación privada y separada.
- [ ] El cutoff, zona horaria, snapshot ID y hash aparecen en la configuración,
      `analysis.json` y el recibo de artefactos.
- [ ] El modo `synthetic` está declarado y coincide con el uso de la carpeta.
- [ ] `CALIDAD.json` fue revisado, o la consola reportó cero issues de entrada.
- [ ] Los control totals acordados cuadran y los importes conservan centavos
      MXN exactos.
- [ ] Las referencias de `Gerencia.xlsx` permiten localizar tabla, registro,
      campo y snapshot de origen.
- [ ] Las limitaciones de cobertura, grain y causalidad están documentadas.
- [ ] Consentimiento, seguridad, frescura, ownership, acceso y retención fueron
      revisados por los responsables fuera del adaptador.
- [ ] No se utilizaron datos reales para reclamar impacto, ROI, SLA, seguridad
      o adopción sin validación adicional.

| Control pendiente | Owner | Fecha objetivo | Nota |
|---|---|---|---|
| `[ ]` | `[ ]` | `[ ]` | `[ ]` |
| `[ ]` | `[ ]` | `[ ]` | `[ ]` |
| `[ ]` | `[ ]` | `[ ]` | `[ ]` |

## 4. Decisiones y acciones humanas

`Seguimiento.xlsx` tiene una sola clave de seguimiento: `action_id`. Las
columnas de origen (`action_id`, `category`, `title`, `priority`, `owner_role`,
`why_now`, `recommended_next_step`, `amount_at_risk_cents`, `source_ids`,
`evidence` y `source_snapshot`) son inmutables durante la revisión. Solo se editan `owner`,
`status`, `target_date`, `note` y `outcome_evidence`. Un status `done` exige
owner, nota y evidencia del resultado; `accepted` e `in_progress` exigen owner
y fecha objetivo; `dismissed` exige una nota. Aun así, el resultado es
auto-reportado.

| Action ID | Owner | Status | Target date | Note | Outcome evidence |
|---|---|---|---|---|---|
| `[ ]` | `[ ]` | `pending / accepted / in_progress / done / dismissed` | `[ ]` | `[ ]` | `[ ]` |
| `[ ]` | `[ ]` | `pending / accepted / in_progress / done / dismissed` | `[ ]` | `[ ]` | `[ ]` |
| `[ ]` | `[ ]` | `pending / accepted / in_progress / done / dismissed` | `[ ]` | `[ ]` | `[ ]` |

| Action ID | Resultado declarado | Evidencia del resultado | Revisor auto-reportado |
|---|---|---|---|
| `[ ]` | `[ ]` | `[ ]` | `[ ]` |
| `[ ]` | `[ ]` | `[ ]` | `[ ]` |

## 5. Entregables recibidos

- [ ] `INICIO.html`
- [ ] `Gerencia.xlsx`
- [ ] `Seguimiento.xlsx`
- [ ] `Seguimiento_original.xlsx`
- [ ] `analysis.json`
- [ ] `receipt.json`
- [ ] `CALIDAD.json`, si se solicitó mediante `--errors <ruta>`
- [ ] `GUIA.html`, `snapshot.json` y `warehouse.sqlite`, si forman parte de la
      carpeta de corrida
- [ ] Comparación `client-compare`, si existe una corrida anterior
- [ ] Limitaciones y preguntas abiertas
- [ ] Próximo owner de export y próxima fecha de revisión

## 6. Estado de aceptación de la entrega

Estos estados pertenecen a esta acta y requieren una decisión humana; no son
los estados de fila de `Seguimiento.xlsx` y no activan ninguna acción.

| Estado | Marcar | Condición |
|---|---|---|
| `pending` | `[ ]` | falta revisión o información |
| `accepted` | `[ ]` | alcance, evidencia, límites y acciones fueron revisados |
| `accepted_with_follow_up` | `[ ]` | entrega usable con pendientes nombrados y fechados |
| `rejected` | `[ ]` | controles o alcance no cumplen el acuerdo |

### Pendientes aceptados

| Pendiente | Riesgo o impacto para la decisión | Owner | Fecha de resolución |
|---|---|---|---|
| `[ ]` | `[ ]` | `[ ]` | `[ ]` |
| `[ ]` | `[ ]` | `[ ]` | `[ ]` |

## 7. Confirmación humana

La firma o aprobación siguiente confirma la recepción y el estado de la
entrega descrita. No autoriza automáticamente mensajes, pagos, despachos,
compras, reparaciones, cambios en sistemas ni publicación de datos.

| Rol | Nombre | Fecha | Firma o aprobación verificable |
|---|---|---|---|
| Aprobador del cliente | `[ ]` | `[ ]` | `[ ]` |
| Sponsor | `[ ]` | `[ ]` | `[ ]` |
| Analista / proveedor | `[ ]` | `[ ]` | `[ ]` |

**Comentarios del cliente:**

`[ ]`
