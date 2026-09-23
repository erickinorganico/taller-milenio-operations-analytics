# Phase 1 context — Operación persistente y acceso

## Outcome and scope

Usuarios con permisos registran y recuperan clientes, vehículos, citas, órdenes, inspecciones, cotizaciones, inventario, cobros, flotillas y grúas. El servidor impide transiciones inválidas y deja eventos auditables. Requisitos: AUTH-01, AUTH-02, RUN-01, OPS-01 a OPS-04, STK-01, FIN-01, FLT-01 y TOW-01.

## Decisiones vigentes

- Django 5.2 LTS con auth, sesión y CSRF; permisos revisados en vistas y servicios, nunca solo ocultando botones.
- SQLite local para un taller. Los cambios conjuntos de estado, stock y pago son atómicos; las entradas duplicadas usan claves estables e idempotencia.
- Montos en Decimal, fechas con zona horaria y unidades de stock explícitas. Conservar versiones y eventos; una corrección no borra historia.
- Instancia real vacía; demo con datos sintéticos creada por comando distinto. Sin credenciales fijas de producción.
- Comprobante administrativo, no fiscal. Flotilla y grúa son captura y seguimiento local, sin telemetría ni decisión de seguridad automática.

## Límites y evidencia

No afirmar que las etapas, precios o umbrales reflejan procesos reales del taller. Ejecutar pruebas con base temporal desechable y registrar comandos/resultados en SUMMARY de cada plan. Una fase está terminada solo tras verificar sus criterios; archivos creados o migraciones aplicadas no bastan.
