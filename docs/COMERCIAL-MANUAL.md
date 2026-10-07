# Comercial Milenio · manual de la primera versión

Implementación local, 1 de octubre de 2026. Un solo Django y una sola base por instalación: las tablas comerciales se separan de órdenes, vehículos y cobros. Gerencia y recepción acceden a `/commercial/`; otros roles no pueden leer ni exportar esta información.

## Instalación y apertura

1. `powershell -NoProfile -ExecutionPolicy Bypass -File Setup-Commercial.ps1 -Mode live`. Si ya existe base, crea un respaldo verificado antes de migrar. Respeta la carpeta guardada por el lanzador.
2. Abrir `Abrir-Comercial.cmd`. El servidor escucha solo en `127.0.0.1:8770` (el puerto 8765 ya estaba ocupado por otra aplicación). Crear gerencia en `/setup/` si es una instalación nueva; no existe contraseña predeterminada.
3. Investigación: `powershell -NoProfile -ExecutionPolicy Bypass -File Setup-Research.ps1`. Entorno independiente `.venv-research`; versiones fijadas en `requirements-research.txt`.
4. La demo se abre con `Abrir-Demo.cmd`, puerto 8766. Para agregar ejemplos: usar `MILENIO_MODE=demo`, su propia carpeta `MILENIO_DATA_DIR` y `manage.py seed_commercial_demo`. El comando rechaza live.

Los datos nuevos de trabajo se guardan por defecto en `%LOCALAPPDATA%/Milenio/operational/live`, fuera de OneDrive. No copie datos reales a demo. La instalación heredada de demo tiene su propia ruta guardada; no se mueve automáticamente.

## Recorrido diario

1. **Abrir pendientes.** Filtrar seguimientos para hoy/vencidos. Toda empresa activa necesita una persona responsable, acción concreta y fecha. Revisar también el indicador sin próxima acción.
2. **Encontrar una empresa.** Abrir Investigar y una consulta. Confirmar su identidad; guardar canal de descubrimiento, URL, segmento y notas. Google/Maps, CANACINTRA, Facebook/Instagram y LinkedIn son interfaces gratuitas de investigación, no conectores automáticos.
3. **Guardar evidencia.** Registrar hechos con URL o referencia de conversación y fecha. Marcar como revisada solo tras leerla. Tipo identidad para confirmar empresa; vehículos para combustible/modelos; necesidad para el problema; cobertura para despacho.
4. **Registrar contacto.** Correo/teléfono empresarial publicado o proporcionado directamente y su procedencia. Un correo publicado empieza sin verificar; una respuesta o confirmación directa permite marcarlo confirmado. No se incluye un verificador de entregabilidad ni se adivinan direcciones.
5. **Calificar.** Confirmar tipo de unidades, combustible, total conocido y subconjunto compatible. Unidades desconocidas son nulas, no cero. Para mecánica: identidad revisada, Tijuana, necesidad confirmada y unidades ligeras a gasolina con evidencia. Para grúa: identidad, necesidad y capacidad/cobertura confirmadas por despacho, separadas del combustible.
6. **Explorar.** Con identidad y canal empresarial revisados se puede preparar un borrador exploratorio aun sin confirmar vehículos. Revisarlo y enviarlo manualmente solo cuando Erick haya instruido el contacto. Registrar lo que ocurrió; el sistema no envía correos, mensajes ni WhatsApp.
7. **Proponer.** Abrir una oportunidad de mecánica o grúa. Registrar alcance, unidades, precio acordado, condiciones y vigencia. Cada cambio es una nueva revisión; solo se acepta la última, vigente, con compatibilidad actual. Guardar quién aceptó y la referencia.
8. **Traspasar.** Seleccionar cliente operativo existente o crear uno después de la aceptación. El enlace es idempotente; si detecta coincidencias de nombre/correo exige revisar el cliente existente. No crea una orden, factura ni cargo automáticamente.
9. **Servicio.** Registrar vehículos y orden/grúa en Operación. Volver y vincular el servicio de ese mismo cliente a la oportunidad. Ganada significa servicio vinculado, no pagado. Facturas, importes cobrados y saldos se consultan en Operación.
10. **Retener.** Registrar resultado de atención y próxima revisión/mantenimiento cuando corresponda. No marcar recurrencia por una sola consulta. Revisar la cartera semanalmente con operación.

## Seguimiento y bajas

Actualización: el botón de borrador elige primer contacto, primer seguimiento o cierre según la cantidad de eventos «Contacto realizado». Exige correo empresarial con fuente, identidad revisada y etapa Investigación/Listo para explorar. Tres contactos, cualquier respuesta/reunión/rebote/baja o una etapa posterior detienen los borradores en frío. Una corrección de correo tras un rebote no reinicia esa secuencia: corresponde una gestión individual. La fecha orientativa cuenta lunes a viernes y requiere ajuste manual de festivos. No hay envío ni escritura de agenda al abrir el borrador.

Cadencia propuesta: primer contacto y dos seguimientos los días hábiles 4 y 8 desde el inicio, ajustados manualmente al contexto. No hay cron ni secuencia de envíos. Una respuesta, reunión, rebote o baja limpia la acción pendiente para replantearla. Una baja crea exclusiones de cuenta, dominio y correos conocidos, bloquea borradores/propuestas y no se revierte importando el candidato de nuevo. Las bajas no se reabren en esta interfaz; requiere revisar una solicitud explícita de la empresa antes de diseñar ese flujo.

Un rebote sin destinatario específico suspende los correos de la ficha conservadoramente. Registrar una corrección confirmada del contacto antes de reanudar. Una nota interna no equivale a contacto enviado.

## Importación y extracción

Descargar plantilla desde Importar. CSV UTF-8 de hasta 500 filas/1 MB. `external_id` se deja vacío para nuevas empresas; no controla el ID generado. Mismo archivo: no duplica; mismo dominio: omite; empresas sin dominio: compara nombre/ciudad. Toda la importación se revierte si una fila falla. Importaciones no sobrescriben etapas, contactos, hechos confirmados o bajas. La exportación de candidatos sirve para investigación, no es un respaldo integral del CRM. Las fórmulas potenciales se neutralizan para hojas de cálculo.

Para un sitio empresarial ya elegido:

```powershell
& .venv-research/Scripts/python.exe scripts/research_company.py https://empresa.example
# Plan sin red. Para descargar:
& .venv-research/Scripts/python.exe scripts/research_company.py https://empresa.example --fetch
```

Sustituir la URL ilustrativa por el sitio real. Máximo cuatro páginas, mismo dominio, robots.txt, pausas y timeout, caché 24 h, sin eludir login o bloqueos. No lee redes sociales ni direcciones privadas/locales. Los errores no se convierten en evidencia. El JSON queda en `%LOCALAPPDATA%/Milenio/research/last-report.json`; cargarlo desde la ficha. El texto entra sin revisar, sin crear contactos ni inferir combustible. Para conservar varios reportes, especificar `--output` con un nombre distinto. No subir reportes al repo.

## Control semanal y responsables

| Función | Rutina | Evidencia de terminado |
|---|---|---|
| Dirección | Confirmar cupos, servicios, condiciones y responsable | Matriz de oferta vigente |
| Investigación | Lote de candidatos y fuentes | Registro con hechos/preguntas, sin duplicados |
| Comercial | Revisar agenda, conversar y dar seguimiento | Interacción + siguiente paso con fecha |
| Operación/despacho | Validar compatibilidad y atención | Alcance confirmado; orden en Operación |
| Administración | Revisar facturación/cobro en operación | Saldo conciliado, sin duplicarlo en CRM |
| Analítica | Comparar fuentes y resultados | Candidatos únicos, conversaciones, propuestas, servicios y recurrencia |

## Respaldo y recuperación

`manage.py backup_workshop --output RUTA_NUEVA` incluye todas las tablas comerciales al copiar SQLite y conserva medios/migraciones. Hacerlo con el modo y carpeta de datos correctos. Restaurar únicamente con el servidor detenido, una copia verificada y código de migraciones compatible según `docs/V5-INSTALACION.md`. La exportación CSV no conserva contactos, evidencias, propuestas o bajas y nunca sustituye ese respaldo.

## Alcance actual y siguientes ampliaciones

Funciona: empresas, evidencia, perfiles de flotilla, contactos, oportunidades, revisiones/aceptación, bitácora, bajas, importación/exportación, borradores, biblioteca de búsquedas y enlace operativo.

No se conectaron correo, redes, captura automática de formularios, Paperclip ni JEV. Se reutilizan los roles y permisos del taller; los perfiles documentados de investigación son instrucciones para trabajo supervisado, no agentes ejecutándose. La prioridad siguiente es usar el lote de investigación y ajustar con personas reales antes de agregar conectores.

Pendientes de negocio: correo comercial, domicilio/horarios publicados, capacidad libre, responsable de ventas y alcance exacto de grúa federal. WhatsApp y teléfono confirmados: 664 820 1966.
