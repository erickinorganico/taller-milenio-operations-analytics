# Decisiones del hito V6

- Dirección y autonomía confirmadas por el usuario: resolver siguientes pasos y agregar dashboard principal útil. Se emplean GSD new-milestone/autonomous en modo auto; no se repiten confirmaciones ya autorizadas.
- Nueva investigación de mercado no necesaria: se reutiliza la investigación anterior; análisis focalizado de integración sobre modelos reales y contratos V5.
- Conservar Django, SQLite y dependencias fijadas. No introducir infraestructura externa para un taller local.
- Materializar cortes y marts dentro de la misma base para que respaldo/restauración cubran todo el sistema. Nunca alimentar V6 con el warehouse sintético histórico.
- Trabajador local subordinado al ciclo de vida del servidor, con cola persistente, intervalos, cambios de AuditEvent, leases y fallos visibles. Funciona mientras Milenio está abierto; no se presenta como servicio 24/7.
- Reglas exactas automáticas por defecto. Inferencia nativa opcional y visible, sin proveedores de pago nuevos. La ambigüedad tras interrupción de inferencia no autoriza repetirla silenciosamente.
- Servicios agrupados por texto normalizado exacto, tipo y estado autorizado/facturado; consumo de refacciones por movimientos firmados. No convertir cantidad de presupuestos en servicios ejecutados.
- El dashboard gerencial es la entrada de roles con intelligence_read; recepción operativa se conserva en /today/ y el resto de roles conserva su vista de trabajo.
- Controles de aprobación humana de acciones y aislamiento de roles V5 se conservan. Datos faltantes y periodos no observados quedan explícitos.
