# Fase 8 — Integración y entrega

Objetivo: V6 se instala, migra, respalda, restaura y empaqueta con los mismos límites operativos y permisos que el producto. Requisito DEL-05.

Decisiones: la SQLite de instancia contiene operaciones, cortes y cola, por lo que el respaldo debe ser consistente y completo. La restauración se hace con servidor detenido, verifica integridad y esquema, y preserva media y datos fuente. V5→V6 exige migraciones sin reinicializar usuarios ni inyectar demo. El paquete incluye dependencias, estáticos y nuevos módulos. La CLI Codex sigue opcional y una instalación sin CLI funciona con reglas. La validación distingue pruebas locales y demo sintética de adopción o impacto real.

Gate: base V5 de fixture con usuarios y transacciones → migrar y cotejar conteos/PK; crear corte y trabajo V6 → respaldo → restauración en instalación desechable → cotejar huellas, filas, políticas, trabajos, medios y permisos. Abrir paquete como manager, recepción y lector sin permisos; confirmar dashboard, trabajo en segundo plano y acceso denegado. Revisar que el manual refleje comandos, pantallas, apagado y fallos reales.
