# Milenio V5 · Especificación de producto

## Problema y resultado

El taller necesita capturar su operación y conocer qué vehículo espera autorización o piezas, quién debe trabajar, qué se entregó, cuánto se cobró y qué decisión sigue. Un informe estático no resuelve la captura compartida ni conserva las decisiones. V5 incorpora una aplicación local con roles, transacciones, métricas calculadas desde sus registros y propuestas sujetas a revisión humana.

## Usuarios y autorización

Gerencia configura cuentas, fuentes y proceso. Recepción registra clientes, citas, órdenes y autorización. Técnicos consultan sus órdenes y capturan inspección, tiempos y calidad; no acceden a cartera ni exportaciones generales. Refacciones maneja compras y existencias. Administración registra comprobantes y pagos. Consulta gerencial permite lectura amplia, incluida información financiera, sin modificaciones. Una persona puede tener responsabilidades adicionales mediante la configuración de gerencia; cada cuenta creada en la interfaz recibe un rol.

## Alcance verificable

Los 22 criterios de aceptación están en [.planning/milestones/v5.0-REQUIREMENTS.md](../.planning/milestones/v5.0-REQUIREMENTS.md), cada uno con fase y evidencia. El [manual](V5-MANUAL.md) describe pantallas y el [contrato de dominio](../specs/v5-domain-api.md) define invariantes. El [contrato de inteligencia](../specs/v5-intelligence.md) distingue reglas, inferencia real, evidencia, propuestas y tareas.

Datos persistentes: 24 entidades del dominio con claves foráneas, migración inicial y bitácora. Tres catálogos admiten importación CSV con previsualización sin escritura y confirmación transaccional. Las 18 métricas conservan definición, grano, fuentes, cobertura y detalle. No hay estimación de utilidad/capacidad/SLA sin sus insumos.

## Arquitectura y operación

Servidor local Waitress, Django 5.2 LTS y SQLite. Interfaz sin CDN ni framework JavaScript externo. Sesiones y CSRF, contraseñas hash, permisos de servidor, fotos privadas, backups consistentes y restauración validada. Los datos por defecto viven en LocalAppData, separados de demo, código y paquetes. La instalación validada es una estación Windows; acceso de red, operación multiempresa y alojamiento son una fase de despliegue adicional.

## Criterio de entrega y limitaciones

Entrega local: código ejecutable, dependencias offline, manuales y prueba del ciclo recepción→saldo, pruebas negativas y recuperación. El adaptador nativo se verificó mediante una corrida real de Codex CLI sobre datos demo sintéticos (`artifacts/v5-native-verification.json`), además de pruebas con dobles. Cada instalación requiere su propia sesión autenticada para usarlo. La aceptación comercial requiere observar el trabajo del taller, cargar datos autorizados, conciliar fuentes y acordar soporte.

No se emiten CFDI ni se contacta clientes, se realizan pagos, se compran piezas o se despachan grúas automáticamente. Las facturas administrativas y referencias humanas registran acciones del equipo; no prueban transacciones externas. Los costos capturados sustentan margen directo estimado, no contabilidad ni utilidad neta. Los recibos V2–V4 se mantienen como evidencia histórica de sus respectivas versiones.
