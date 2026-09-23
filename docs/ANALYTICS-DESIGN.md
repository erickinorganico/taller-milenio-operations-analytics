# Analytics: especificación de la interfaz

## Resultado esperado

Gerencia puede entender actividad, demanda y pendientes desde una vista compacta; pasar de un indicador a sus registros y de una propuesta a su seguimiento. La referencia visual solicitada es [Vestra](https://vestra-dashboard01.vercel.app/analytics): navegación clara, indicadores comparables, gráfico principal y tablas densas. Sus importes y métricas financieras no forman parte de Milenio.

Las guías Emil Design Engineering, frontend-design y better-interface orientan jerarquía, interacción y accesibilidad. La composición de shadcn sirve como referencia; se mantiene Django y HTML semántico, sin introducir React ni servicios externos para dibujar datos locales.

## Contrato de datos

- Los cuatro indicadores y sus minigráficos usan exactamente los días del periodo del corte seleccionado. La comparación conserva el periodo previo de igual duración.
- El gráfico representa movimientos diarios de facturación administrativa y cobros; incluye escala desde cero, importes exactos por fecha y tabla alternativa. No representa saldo acumulado ni utilidad.
- Los servicios cuentan órdenes con autorización y muestran valores cotizados. Un valor vinculado a factura no es una asignación del importe real de esa factura.
- Las refacciones conservan cantidad, unidad, costo neto y fuentes. No se suman unidades incompatibles. La búsqueda examina todas las filas del ranking del periodo, no solamente diez resultados.
- La distribución por estado, órdenes abiertas, atraso y saldo describen el corte seleccionado, independientemente del periodo. El segmento sí filtra las órdenes.
- El seguimiento de agentes muestra actividad actual registrada. Sus cifras no atribuyen impacto de negocio ni se confunden con datos congelados del corte.
- Los accesos rápidos de 7, 30 y 90 días conservan segmento y corte; se anclan a la fecha local de ese corte. Los permisos de consulta, exportación y revisión siguen vigentes.

## Interacciones

Resumen, Demanda y Seguimiento tienen enlaces profundos y navegación por teclado. Sin JavaScript, todas las secciones permanecen disponibles. Los controles de búsqueda y ordenación operan sobre las tablas renderizadas. El gráfico permite seleccionar días con flechas y Home/End; la tabla contiene los mismos importes.

La búsqueda de la cabecera consulta órdenes reales. En móvil, un botón despliega la navegación y Escape la cierra devolviendo el foco. Los estados vacíos explican qué falta y dan una salida útil. La política CSP conserva scripts y estilos locales, sin código inline ejecutable.

## Aceptación

1. Corte, segmento y totales concilian con las tablas analíticas; modificar una orden posterior al corte no altera el desglose histórico.
2. Búsqueda, ordenación, cambio de sección, rangos y selección del gráfico funcionan.
3. A 320 px, el documento no desborda horizontalmente; las tablas conservan su propio desplazamiento.
4. Teclado, foco visible, estados vacíos, errores y movimiento reducido tienen soporte; no se depende exclusivamente del color.
5. Suite de regresión y revisión independiente separan evidencia automatizada de observación visual. La aprobación del cliente permanece fuera de la verificación sintética.
