# Phase 4 context — Verificación y entrega local

## Outcome and scope

Un operador puede instalar y recuperar el sistema; las pruebas demuestran el recorrido completo y los rechazos; los manuales corresponden a lo construido. Requisitos: RUN-02, QA-01, QA-02 y DOC-01.

## Decisiones vigentes

- Ensayo sobre instalación vacía y demo separada en Windows, usando Waitress y configuración segura. No afirmar aptitud para servicio público de alta concurrencia.
- Copias consistentes de SQLite, verificación de integridad y restauración ensayada en directorio desechable antes de tocar una instalación existente.
- Manuales por rol y soporte describen las rutas y comandos reales, catálogo de métricas, diccionario de datos y contrato de agentes.
- Pruebas funcionales y negativas comprueban estado y eventos posteriores a errores; una respuesta HTTP de rechazo por sí sola no demuestra consistencia.

## Límite de entrega

La verificación local del producto no acredita uso, ahorro ni impacto en el taller. Piloto con usuarios y datos reales será un hito separado sujeto a evidencia y autorización concreta.
