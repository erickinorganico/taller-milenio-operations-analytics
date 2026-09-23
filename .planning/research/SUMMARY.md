# Investigación reutilizada — 2026-09-22

Investigación documental realizada por root, GPT-6 Sol y GPT-6 Luna, seguida de autorización del usuario. No hubo instalación ni ensayo de los productos comparados.

## Hallazgos
- [Tekmetric](https://support.tekmetric.com/hc/en-us/articles/360043239813-Repair-Order-Workflow-Overview-for-Service-Writers): recepción, inspección, compra de partes autorizadas, ejecución y entrega forman un recorrido conectado.
- [Shopmonkey](https://www.shopmonkey.io/product/reporting): reportes de cierre, pagos, cartera, compras y rentabilidad dependen del registro operativo.
- [AutoLeap AIR](https://autoleap.com/air/): IA aplicada a captura y solicitudes de cita con contexto y resultados, según su documentación comercial. No se toma su marketing como impacto comprobado.
- [OCA/repair](https://github.com/OCA/repair): módulos Odoo de reparaciones, inventario, tiempos y calidad; requiere adaptación automotriz y análisis de licencias por addon.
- [ERPNext](https://github.com/frappe/erpnext): ERP configurable con finanzas, stock, usuarios y API; no es módulo automotriz listo.
- [InvenTree](https://github.com/inventree/InvenTree): referente de inventario y trazabilidad, no aplicación completa de taller.
- [OpenAutoCore](https://github.com/winterautollc/OpenAutoCore): referencia directa; madurez de despliegue/API no acreditada en la revisión.

## Arquitectura recomendada
Producto acotado de taller sobre Django LTS, con datos transaccionales como fuente de métricas. Auth, ORM, migraciones, sesiones y CSRF provistos por el framework. [Documentación](https://docs.djangoproject.com/en/5.2/topics/auth/default/), [despliegue](https://docs.djangoproject.com/en/5.2/howto/deployment/checklist/). Su portabilidad a Windows y la base Python existente evitan imponer un ERP y su carga de configuración sin procesos reales validados.

No replicar todas las funciones de proveedores comerciales. Priorizar recorridos completos y verificables y conservar las integraciones externas como adaptadores explícitos. No usar SQLite para prometer SaaS multiempresa o alta concurrencia.

## Riesgos concretos
No confundir tablas sintéticas con fuentes del taller; no cotizar sobre inventario incoherente; no alterar trabajos ya autorizados; no sumar pagos como ingresos; no mostrar márgenes sin costos/tiempos; no etiquetar reglas como inferencia; no duplicar tareas por reintentos de agentes; no prometer operación pública segura con un servidor de desarrollo.

## Experiencia profesional aplicada
Definiciones y denominadores, calidad/frescura, relaciones fuente-métrica, revisión humana, trazas, decisiones y resultados. Reutilización conceptual; ninguna copia de datos ni código privados de Torre.
