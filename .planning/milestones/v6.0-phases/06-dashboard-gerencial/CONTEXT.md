# Fase 6 — Dashboard gerencial

Objetivo: entrada gerencial basada exclusivamente en cortes persistentes de fase 5. Requisitos ANA-01 y ANA-07.

Decisiones: roles con `intelligence_read` llegan al dashboard; recepción conserva `/today/` y los demás roles su vista de trabajo. Toda ruta de consulta y CSV exige permiso servidor. La pantalla muestra fecha del corte, rango inclusivo, segmento, cantidad de días y periodo anterior de igual duración. Los gráficos de piezas y servicios muestran unidades/órdenes y estado correcto; comparaciones sin cobertura suficiente dicen no comparable. La exploración de filas incluye referencias navegables a fuentes solo cuando el rol puede verlas. No recalcular totales desde tablas operativas en la vista ni presentar demo como real.

Gate: recorrido con manager, viewer y rol sin `intelligence_read`; filtros cambiados, periodo previo, descarga CSV, enlace fuente y URL directa. Cotejar al menos una tarjeta y una serie con filas del corte y confirmar escape de contenido de usuario en gráficos, HTML y CSV.
