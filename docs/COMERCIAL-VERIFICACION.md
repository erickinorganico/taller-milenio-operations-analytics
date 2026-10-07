# Verificación de la primera versión comercial

1 de octubre de 2026, Tijuana. Pruebas ejecutadas en Windows con Python 3.12.14 y Django 5.2.17. Ninguna prueba usa la base real de clientes; se crean bases temporales.

| Comprobación | Resultado observado |
|---|---|
| `manage.py test workshop commercial --noinput` | **168 pruebas aprobadas**, 46.638 s en la corrida final |
| `python -m unittest tests.test_commercial_research -v` en `.venv-research` | **5 pruebas aprobadas** |
| `manage.py makemigrations --check --dry-run` | Sin cambios de modelos pendientes |
| `manage.py check` | Sin errores |
| `pip check` en los dos entornos | Sin dependencias incompatibles |
| Navegador Chrome, escritorio 1440×1000 y móvil 390×844 | Flujo y presentación comprobados; capturas locales |
| Extractor contra `https://example.com` | Una página obtenida, reporte guardado; sin contactos reales |
| Publicación Sites | Estado `succeeded`; sitio privado accesible en el enlace de entrega |
| Instalación de trabajo | Migraciones aplicadas, servidor en loopback 8770, health identifica `milenio-operations` / `live` |
| Respaldo posterior de trabajo | Creado y verificado por `backup_workshop` fuera de OneDrive |

## Qué cubren las pruebas comerciales

- Combustible desconocido, exclusiones, flotilla mixta y conteos coherentes.
- Evidencia revisada de la propia cuenta; identidad no se confirma solo con una casilla.
- Compatibilidad de grúa separada de mecánica.
- Edición simultánea: una versión anterior no sobrescribe cambios recientes.
- Baja de cuenta/correo, bloqueo de borradores y cancelación del seguimiento.
- Respuesta y rebote, corrección de contactos con fuente.
- Propuestas, revisiones, aceptación de la más reciente y traspaso idempotente.
- Servicio operativo del mismo cliente y prohibición de enlazar uno ajeno.
- CSV repetido, duplicados de dominio, importación atómica y fórmulas neutralizadas al exportar.
- Permisos por rol, CSRF y consultas GET sin mutaciones.
- Reportes de extracción repetidos, dominio equivocado y ausencia de inferencias automáticas.
- Demo rechazada en live y paquete sin bases de datos privadas.

## Comprobación del navegador

`scripts/check_commercial_ui.py` crea una base temporal sintética, inicia servidores exclusivos de prueba, usa una sesión temporal y los detiene al terminar. Requiere Playwright y Chrome disponibles en el equipo de desarrollo. No instala credenciales ni inicia sesión en la base real.

Comprueba guardado de una respuesta desde formulario con CSRF, cancelación de fecha pendiente, identificadores de campos únicos, carga de estilos, ausencia de errores de recursos/JavaScript y de desbordamiento horizontal. En el sitio comprueba el teléfono de destino y la codificación de acentos y `&` en WhatsApp. No envía el mensaje.

Capturas y resultado: `private/commercial-qa/` (excluido de Git). Se detectaron y corrigieron la hoja de estilos comercial no servida por la ruta WSGI y los IDs duplicados entre formularios. En regresión se actualizó la prueba del paquete para exigir también el nuevo módulo y su migración.

## Límites de esta verificación

No se evaluó una campaña real ni entregabilidad de correos. No se probaron inferencias de Jev, envío de mensajes, navegación automática por redes, publicación pública del sitio ni sincronización de prospectos con Paperclip. No se ejecutó una comparación funcional de Frappe: la decisión de esta versión fue aprovechar el Django existente. Se preservaron las modificaciones previas del proyecto; el resultado es una integración local, no un release publicado en GitHub.

Las restauraciones se cubren con las pruebas temporales de recuperación del taller. No se sobrescribió una instalación de trabajo para ensayar restauración. Las condiciones comerciales y la capacidad real requieren validación de operación antes del piloto.
