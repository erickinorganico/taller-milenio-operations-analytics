# Milenio / Cuaderno de revisión

Escenario sintético. Propuestas pendientes: ninguna equivale a autorización ni se ha ejecutado.

Abra `review_queue.csv` para priorizar y asignar revisores. Conserve el original sellado y trabaje en una copia para registrar decisiones humanas.

## intake_admin

Al corte válido 2026-09-21T18:00:00Z hay 4 leads abiertos y 1 cita pendiente. L-001 aparece como nuevo con seguimiento registrado para 2026-09-20T17:00:00Z, por lo que requiere revisión humana. Q-010 está enviada pero su vigencia registrada terminó antes del corte. Q-009 está enviada y requiere seguimiento humano. A-002 está pendiente y comienza después del corte. L-003 está cotizado, pero su cliente tiene consentimiento denegado; no debe contactarse. No se realizó ningún contacto, agenda, modificación ni envío.

Modo: `native_codex`. Inferencia observada: `True`.

Siguientes pasos para revisión:

- Validar manualmente el estado y el consentimiento de los leads abiertos no cubiertos por la evidencia detallada.
- Revisar L-001 y decidir internamente si procede una acción, sin contactar hasta confirmar consentimiento.
- Determinar manualmente si Q-010 debe reemitirse o cerrarse por vencimiento; no reutilizarla ni procesar pago.
- Revisar Q-009 y definir el siguiente paso humano antes de su fecha de vigencia registrada.
- Para L-003 y C-003, bloquear contacto y solicitar cualquier aclaración únicamente por un canal interno autorizado.
- Revisar A-002 sin modificar ni confirmar la cita.

[Resultado y referencias](native_runs/intake_admin/result.json) · [Traza](native_runs/intake_admin/tool_trace.jsonl)

## operations_controller

Corte válido: 2026-09-21T18:00:00Z. El riesgo principal es capacidad comprometida: hay 7 órdenes abiertas, 4 bahías ocupadas y 1 orden esperando partes. WO-003 está bloqueada por falta de filtro, sin bahía ni técnico asignados. WO-004 está en retrabajo y ocupa B-003. La evidencia de inventario muestra 8 unidades recibidas y 2 consumidas de P-001, mientras RS-001 figura como consumida y RS-002 como reservada; esto requiere conciliación humana antes de secuenciar. No se asigna personal, no se compran partes y no se cambia trabajo.

Modo: `native_codex`. Inferencia observada: `True`.

Siguientes pasos para revisión:

- Para revisión humana, confirmar si el filtro faltante de WO-003 está disponible o pendiente de recepción.
- Validar el estado operativo de B-003 y el avance de WO-004 antes de considerar otra secuencia.
- Conciliar RS-001, RS-002, SM-001 y SM-002 con el inventario físico y los registros de órdenes.
- Revisar las 7 órdenes abiertas y las 4 bahías ocupadas para definir prioridades sin reasignar personal desde este análisis.

[Resultado y referencias](native_runs/operations_controller/result.json) · [Traza](native_runs/operations_controller/tool_trace.jsonl)

## maintenance_planner

Al corte válido as_of=2026-09-21T18:00:00Z, hay mantenimiento pendiente en M-002 y M-003, ambos con vencimiento 2026-09-30T18:00:00Z. M-003 presenta además una brecha contractual porque CT-002 figura vencido. Hay 7 órdenes de trabajo abiertas según la métrica, pero la evidencia detallada disponible solo cubre WO-002, WO-003 y WO-004. No se creó ni se propone crear una cita, y no se promete ningún SLA.

Modo: `native_codex`. Inferencia observada: `True`.

### Borrador 1 / followup

Para revisión humana: confirmar si se desea coordinar manualmente la revisión de M-002 antes de 2026-09-30T18:00:00Z y validar primero la cobertura aplicable a M-003, dado que CT-002 figura vencido. También confirmar disponibilidad y prioridad para WO-002, WO-003 y WO-004; este texto no ha sido enviado.

Siguientes pasos para revisión:

- Confirmar manualmente la prioridad y la ventana disponible para M-002 antes de 2026-09-30T18:00:00Z, sin crear una cita desde esta revisión.
- Validar manualmente si M-003 tiene cobertura alternativa o autorización aplicable mientras CT-002 figura vencido.
- Preguntar si WO-003 ya cuenta con la refacción faltante y si WO-004 requiere una nueva inspección antes de cualquier coordinación.
- Confirmar el estado operativo y la prioridad de WO-002, que figura en servicio.
- No enviar mensajes ni ejecutar cambios; cualquier coordinación requiere revisión y acción humana autorizada.

[Resultado y referencias](native_runs/maintenance_planner/result.json) · [Traza](native_runs/maintenance_planner/tool_trace.jsonl)

## fleet_sales_research

Al corte válido de 2026-09-21T18:00:00Z hay 2 oportunidades abiertas. OP-001 está en estado de propuesta y vinculada con FA-001, una cuenta de logística con una flotilla de 12 unidades y responsable Laura Campos. FA-001 tiene un contrato activo que termina el 2026-12-31T23:59:59Z. OP-002 está calificada, vinculada con FA-002 y tiene seguimiento programado para el 2026-09-28T18:00:00Z; FA-002 tiene una flotilla de 8 unidades. No se realizó contacto ni se envió ningún borrador.

Modo: `native_codex`. Inferencia observada: `True`.

### Borrador 1 / followup

Borrador interno no enviado para revisión humana: revisar OP-001, actualmente en estado de propuesta, antes del 2026-09-26T18:00:00Z. Confirmar internamente el siguiente paso y considerar el contrato activo asociado con FA-001, cuyo vencimiento registrado es 2026-12-31T23:59:59Z.

### Borrador 2 / message

Borrador interno no enviado para revisión humana: preparar una revisión de OP-002, actualmente calificada, antes del 2026-09-28T18:00:00Z. Validar internamente los criterios pendientes de calificación para FA-002; no incluye contacto externo ni cotización.

Siguientes pasos para revisión:

- Revisar y aprobar manualmente la prioridad entre OP-001 y OP-002.
- Validar internamente el siguiente paso de cada oportunidad antes de cualquier contacto.
- No enviar los borradores sin revisión humana explícita.

[Resultado y referencias](native_runs/fleet_sales_research/result.json) · [Traza](native_runs/fleet_sales_research/tool_trace.jsonl)

## fleet_sla_watcher

Al corte válido as_of=2026-09-21T18:00:00Z, CT-001 figura activo, con SLA de 48 horas y vigencia entre 2026-01-01T00:00:00Z y 2026-12-31T23:59:59Z. WO-H154 está asociado a CT-001, abierto el 2026-06-29T20:00:00Z y completado exactamente en due_at, 2026-06-30T02:00:00Z; esta evidencia no respalda un incumplimiento. WO-H153 figura entregada y completada exactamente en due_at, pero faltan en la evidencia elegible su contract_id y opened_at, por lo que no puede evaluarse completamente contra el SLA. La métrica incluida reporta 1 contrato activo y 7 órdenes abiertas, pero no se usa para declarar incumplimiento.

Modo: `native_codex`. Inferencia observada: `True`.

### Borrador 1 / followup

Solicitar para WO-H153 la evidencia versionada de contract_id y opened_at, y confirmar que el criterio aplicable sea el SLA de 48 horas de CT-001.

Siguientes pasos para revisión:

- Obtener mediante revisión humana la evidencia versionada de contract_id y opened_at para WO-H153.
- Comparar opened_at, completed_at y due_at de WO-H153 con las reglas completas del SLA de CT-001.
- Confirmar si existen pausas, exclusiones o criterios de calendario aplicables antes de emitir una conclusión.
- Mantener la clasificación como evidencia insuficiente mientras no se completen esos campos.

[Resultado y referencias](native_runs/fleet_sla_watcher/result.json) · [Traza](native_runs/fleet_sla_watcher/tool_trace.jsonl)

## tow_dispatch_assistant

Al corte válido as_of=2026-09-21T18:00:00Z hay 2 grúas activas. TW-002 figura en_route y tiene referencias de aprobación y seguridad, pero su unidad TU-002 tiene capacidad arrastre. TW-003 figura requested y carece de unidad, aprobación humana y referencia de seguridad. No se realiza despacho ni se toma una decisión de seguridad.

Modo: `native_codex`. Inferencia observada: `True`.

### Borrador 1 / followup

Para revisión humana: confirmar el estado operativo y la seguridad de TW-002, validar las referencias HUMAN-APP-001 y SAFE-HUMAN-001, y confirmar que la capacidad arrastre de TU-002 corresponde al servicio. No enviado.

### Borrador 2 / followup

Para revisión humana: confirmar aprobación humana, evaluación de seguridad y asignación de unidad para TW-003 antes de cualquier decisión operativa. No enviado.

Siguientes pasos para revisión:

- Una persona autorizada debe confirmar la situación de seguridad actual de TW-002 y la validez de sus referencias.
- Una persona autorizada debe confirmar aprobación humana, evaluación de seguridad y unidad compatible para TW-003.
- No despachar ni cambiar estados con base únicamente en este corte.

[Resultado y referencias](native_runs/tow_dispatch_assistant/result.json) · [Traza](native_runs/tow_dispatch_assistant/tool_trace.jsonl)

## collections_assistant

En la muestra de 6 facturas/casos, las métricas globales del corte reportan 164 facturas emitidas y 56 facturas sin pago completo. El resumen de pagos vincula pagos completos a INV-H160, INV-H158, INV-H157 e INV-H155. INV-H159 e INV-H156 presentan conciliación parcial: el pago vinculado a INV-H159 es de 63750 centavos frente a una factura de 127500 centavos, y el pago vinculado a INV-H156 es de 45000 centavos frente a una factura de 90000 centavos. Estas son preguntas para revisión humana; no se realizó cobro, movimiento de dinero ni emisión fiscal.

Modo: `native_codex`. Inferencia observada: `True`.

### Borrador 1 / followup

Borrador no enviado para revisión humana: ¿Podrían confirmar la aplicación del pago registrado de 63750 centavos a la factura INV-H159, cuyo importe es de 127500 centavos, y proporcionar soporte para conciliar el saldo restante de 63750 centavos?

### Borrador 2 / followup

Borrador no enviado para revisión humana: ¿Podrían confirmar la aplicación del pago registrado de 45000 centavos a la factura INV-H156, cuyo importe es de 90000 centavos, y proporcionar soporte para conciliar el saldo restante de 45000 centavos?

Siguientes pasos para revisión:

- Solicitar revisión humana de los saldos parciales de INV-H159 e INV-H156.
- Comparar los comprobantes o remesas disponibles con los pagos vinculados antes de decidir su tratamiento contable.
- No enviar los borradores ni ejecutar cobros sin autorización humana separada.

[Resultado y referencias](native_runs/collections_assistant/result.json) · [Traza](native_runs/collections_assistant/tool_trace.jsonl)

## marketing_planner

La evidencia muestra que CAM-001 está en revisión, dirigida a particulares y orientada a recurrencia. CAM-002 figura como aprobada, pero su borrador sigue siendo genérico y requiere confirmar la audiencia fleet y la base de consentimiento antes de cualquier publicación. No se envió ni publicó ningún mensaje.

Modo: `native_codex`. Inferencia observada: `True`.

### Borrador 1 / followup

Preguntas para revisión humana: ¿El borrador de CAM-001 describe claramente la propuesta de recurrencia y el mecanismo de baja? ¿La audiencia de CAM-001 se limita a particulares con consentimiento confirmado? Para CAM-002, ¿qué contactos o cuentas forman parte de la audiencia fleet y qué evidencia documenta su consentimiento? ¿La aprobación de CAM-002 sigue vigente pese a que el borrador aparece como “Borrador sintético”?

### Borrador 2 / message

Texto propuesto para aprobación humana: “Recordatorio de mantenimiento: revisa si tu vehículo ya requiere servicio y consulta las opciones disponibles. Si prefieres no recibir comunicaciones, solicita la baja por el canal autorizado.” Este texto es únicamente un borrador para revisión y no debe enviarse sin validar audiencia, consentimiento y aprobación final.

Siguientes pasos para revisión:

- Revisar y aprobar manualmente cualquier texto antes de publicarlo.
- Excluir a C-003 de comunicaciones porque su consentimiento es 0.
- Confirmar la relación entre cada audiencia de campaña y los destinatarios concretos.
- Validar el consentimiento aplicable a los contactos de la audiencia fleet de CAM-002.
- No publicar ni enviar mensajes durante esta revisión.

[Resultado y referencias](native_runs/marketing_planner/result.json) · [Traza](native_runs/marketing_planner/tool_trace.jsonl)

## weekly_operator

Al corte válido as_of=2026-09-21T18:00:00Z, hay 7 órdenes de trabajo abiertas, 2 remolques activos y 56 facturas impagas. Los principales puntos para revisión son WO-003 bloqueada por falta de filtro, WO-004 en retrabajo, TW-003 sin aprobación humana ni unidad asignada, y dos facturas con fechas de vencimiento anteriores al corte. Estos datos deben convertirse en preguntas de revisión; no se asignan responsables ni se ejecutan acciones.

Modo: `native_codex`. Inferencia observada: `True`.

### Borrador 1 / followup

Para revisión humana: confirmar quién debe validar WO-003, WO-004, TW-003 y las facturas INV-H160 e INV-H159, así como el estado de las autorizaciones, disponibilidad de recursos y próximos pasos antes de cualquier decisión.

Siguientes pasos para revisión:

- Confirmar manualmente el responsable de validar la pieza faltante y la fecha comprometida de WO-003.
- Confirmar manualmente el responsable de revisar el retrabajo de WO-004 y validar el papel de T-003, sin asumir asignación adicional.
- Confirmar manualmente el estado de M-002, su programación y el responsable de seguimiento.
- Confirmar manualmente la ubicación y el estado operativo de TW-002.
- Confirmar manualmente la aprobación humana, la unidad y las condiciones de seguridad requeridas para TW-003.
- Confirmar manualmente el responsable de revisar INV-H160 e INV-H159 y la causa de sus fechas de vencimiento.
- Validar en la reunión las métricas agregadas: 7 órdenes abiertas, 2 remolques activos y 56 facturas impagas.

[Resultado y referencias](native_runs/weekly_operator/result.json) · [Traza](native_runs/weekly_operator/tool_trace.jsonl)
