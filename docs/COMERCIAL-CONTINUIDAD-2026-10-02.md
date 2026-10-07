# CRM Milenio: correcciones integradas y activas

El módulo comercial está actualizado en la instancia local **http://127.0.0.1:8770/**. Se integraron diez archivos a las **06:19:49 UTC del 2 de octubre de 2026**, se aplicó `commercial.0002_acceptance_branch_recurrence` a las **06:19:56 UTC** y se verificó el arranque a las **06:20:19 UTC**.

**Acceso pendiente de configuración inicial de Gerencia:** `/commercial/` redirige a `/setup/`, que responde HTTP 200. El respaldo anterior confirma que tampoco había una cuenta de Gerencia activa antes de esta intervención. No se crearon ni modificaron credenciales; el usuario debe completar esa configuración para utilizar el CRM con sesión autenticada.

## Comportamiento corregido

| Requisito del sistema comercial | Comportamiento integrado |
|---|---|
| Diferenciar sucursal/base | Cuentas distintas pueden compartir dominio. Las coincidencias ambiguas del CSV se conservan para revisión, sin fusión automática. Se admite el CSV anterior. |
| Necesidad y siguiente paso antes de oportunidad | Exige necesidad confirmada con evidencia revisada, responsable y próxima acción/fecha; conserva referencias en auditoría. |
| Aceptación determina resultado comercial | La aceptación documentada de la revisión vigente marca la oportunidad ganada; no acredita entrega ni cobro. |
| Revisiones y autorización trazables | Una revisión nueva queda pendiente sin borrar la aceptación histórica. El vínculo operativo identifica la propuesta aceptada que lo respalda. |
| Recurrencia sustentada | Segunda orden real o plan vigente se declaran como modalidades distintas y requieren evidencia revisada. Una recepción por sí sola no acredita recurrencia. No se añadieron umbrales económicos ni plazos inventados. |

Fuentes: `planeacion-comercial/SISTEMA-COMERCIAL-MILENIO.md`, líneas 104, 109–110, 116, 122 y 128–130; `PLAN-FLOTILLAS-MILENIO-2026-10-01.md`, líneas 108–110. Matriz y casos de trazabilidad: `MATRIZ-Y-CASOS.md` en la carpeta local de revisión.

Se preservan los borradores del productor por segmento, límite de tres contactos, intervalos orientativos y detención tras respuesta, reunión, rebote o baja. También sus correcciones de contactos existentes, prefijos de formularios y compatibilidad al enlazar servicios.

## Validación realizada

- **197/197 pruebas de aplicación aprobadas**, 58.527 segundos; **5/5 del extractor aprobadas**. Se ejecutaron en una copia de 377 archivos idénticos al código integrado, con datos de prueba aislados. No se instalaron paquetes ni se descargaron prospectos.
- `makemigrations --check --dry-run`: sin cambios pendientes de generar. `manage.py check`: sin incidencias.
- Base real: migraciones comerciales 0001 y 0002 aplicadas; columnas nuevas presentes; índice de dominio ya no es único; integridad SQLite correcta y sin referencias inválidas. Cero registros comerciales/operativos de clientes al corte.
- HTTP real: `/health/` 200 y estado OK, CSS comercial 200, `/commercial/` y `/login/` redirigen a la configuración inicial, `/setup/` 200. No se probó un flujo autenticado con clientes reales ni se escribieron datos comerciales en la instancia.
- Los 11 entregables de web/materiales del manifiesto del coordinador conservan sus hashes. No se intervino Paperclip ni el sitio web. Los 30 candidatos permanecen sin importar; no se enviaron contactos.

Las pruebas acreditan controles y trazabilidad con datos sintéticos. No acreditan ventas, resultados comerciales reales ni elegibilidad automática de recurrencia.

## Respaldo y recuperación

Respaldo privado verificado: `<perfil-local>/AppData/Local/Milenio/backups/commercial-0002-20261002T061925Z/`. Incluye base completa anterior, directorio de medios y siete archivos de código previos; las otras tres rutas eran nuevas. Había cero archivos de medios. `.secret_key` quedó excluida y no se exportaron base ni credenciales a la carpeta compartible de entregables.

El respaldo real pasó validación de hashes, esquema e integridad. Por separado, se ensayó con datos exclusivamente sintéticos: respaldo de 0001 → migración 0002 → restauración de esquema, etiquetas, aceptación y medios, conservando una copia del estado anterior a restaurar.

No usar solo una migración inversa como recuperación completa. La reversa de la reclasificación no reconstruye etiquetas; eliminaría campos nuevos y recuperar `domain UNIQUE` puede fallar si después se crean sucursales con dominio compartido. La recuperación exacta requiere respaldo de base/medios y código compatible, conciliando antes cualquier operación posterior. Conservar la clave existente. El lanzador ejecuta migraciones al iniciar, por lo que código y esquema deben coordinarse.

## Evidencia y siguiente operación

Carpeta de revisión: `<perfil-local>/Documents/Codex/2026-10-01/task-5/revision-milenio-2026-10-02/`.

Consultar `resultado-suite-integrada.txt`, `resultado-extractor-integrado.txt`, `resultado-esquema-integrado.txt`, `migracion-activa-verificada.json`, `crm-activado-salud.json`, `verificacion-despliegue-crm.json`, `respaldo-privado-verificado.json` y el diff final `commercial-integrado.patch`.

Este documento sustituye el estado pendiente descrito en informes anteriores. No volver a ejecutar scripts de parada con PID o cierres históricos. Para cambios futuros, reservar rutas del CRM, verificar sus huellas durante la preparación y justo antes de intervenir, y distinguir actividad independiente de web/documentos de escrituras relacionadas con el CRM.

Siguiente paso de uso: completar Gerencia en `/setup/`; después validar fuentes y datos reales antes de operar oportunidades o cotizaciones. Confirmar condiciones por caso sin convertir borradores o candidatos en ventas ni importar prospectos automáticamente.
