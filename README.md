# Milenio · Operación, datos y agentes para el taller

V6 conecta un dashboard gerencial, cortes analíticos persistentes y automatizaciones con la aplicación web local en español para registrar el trabajo diario: recepción, inspección, autorización, refacciones, ejecución, calidad, entrega y cobranza. Los datos quedan en SQLite; las métricas y propuestas se calculan desde esos mismos registros. Incluye contratos de flotilla, mantenimiento y seguimiento de grúas.

## Abrir la aplicación

En Windows x64 con Python 3.12 instalado:

```powershell
powershell -ExecutionPolicy Bypass -File .\Setup-Web.ps1
.\Iniciar-Demo.cmd
```

La demo abre en **http://127.0.0.1:8766/** con datos ficticios. Para una instalación vacía use **Iniciar-Milenio.cmd**, puerto 8765. El primer inicio solicita crear una cuenta propia. Las bases están separadas y se conservan al cerrar. La ubicación predeterminada es `%LOCALAPPDATA%/Milenio/operational/<modo>`, fuera de la carpeta sincronizada del código. El lanzador detecta instalaciones antiguas y pide migrarlas explícitamente, sin borrar datos.

El ZIP V6 con wheels permite instalar las dependencias sin internet en Windows x64/Python 3.12. Python y una sesión personal de Codex, si se desea usar el modelo, son requisitos externos. El servidor escucha sólo en el equipo local; abrirlo a otros equipos requiere un despliegue con HTTPS y configuración específica.

## Dashboard, analytics y automatizaciones

El inicio gerencial muestra piezas más utilizadas por órdenes con consumo neto, servicios más solicitados, facturación, cobros, entregas y comparación contra un periodo anterior de igual duración. Permite filtrar fechas y particulares/flotillas. Cada corte conserva seis tablas derivadas, huella y acceso a fuentes; CSV y JSON se exportan según rol.

Un trabajador se inicia con el servidor y ejecuta actualizaciones por intervalo y cambios de negocio. Gerencia puede pausar la cola, elegir frecuencia y activar Codex nativo opcional. Reglas es el modo predeterminado; errores, intentos, cortes y corridas son visibles. El trabajador funciona mientras Milenio está abierto. Las propuestas requieren revisión humana y no envían mensajes ni realizan compras o cobros externos.

- [Dashboard y significado de las métricas](docs/V6-ANALYTICS.md)
- [Automatizaciones, recuperación y agentes](docs/V6-AUTOMATIZACIONES.md)
- [Contrato y flujo de operación a analytics y agentes](specs/v6-analytics-automation.md)
- [Alcance del hito V6](.planning/milestones/v6.0-REQUIREMENTS.md)

## Recorrido entregado

| Trabajo | Pantalla y resultado persistente |
| --- | --- |
| Recepción | Clientes, vehículos, agenda, orden, técnico y fecha prometida; importación CSV con revisión previa |
| Técnico | Órdenes asignadas, inspección con fotografías, tiempos, etapas y control de calidad |
| Refacciones | Proveedores, compra en borrador, confirmación, recepción parcial, reservas, consumo y devoluciones |
| Administración | Comprobante administrativo, pagos parciales sin duplicados/sobrepago y saldos |
| Flotillas y grúas | Contratos, planes por fecha/km, solicitud, operador, hitos y evidencia humana |
| Gerencia | Dashboard por periodo y segmento, seis tablas analíticas persistentes, 24 fuentes operativas, 18 indicadores de catálogo y seguimiento de propuestas |
| Equipo | Cuentas por rol, cambios de contraseña, desactivación conservando historial y bitácora |

Tres agentes de revisión —operación, cobranza y calidad de datos— guardan hallazgos, evidencia y propuestas. Aceptar una propuesta vigente crea una tarea interna; se asigna responsable y plazo, se registra el resultado y se vuelve a comprobar el disparador. Los pagos nuevos invalidan evidencia antigua y repetir una revisión no duplica pendientes.

El modo **reglas** funciona sin IA ni internet. El modo **nativo Codex** requiere activar la opción y autenticar la CLI oficial. En V6, una ejecución real de la cola completó los tres revisores con GPT-6 Luna sobre datos ficticios y produjo 14 propuestas internas (`artifacts/v6-native-verification.json`). Un intento previo rechazó una salida inválida y quedó registrado como fallido; no se repite inferencia automáticamente. No se usan APIs de pago como alternativa. Esta prueba local no sustituye el piloto del taller.

## Documentación y evidencia

- [Instalación, respaldo y recuperación](docs/V5-INSTALACION.md)
- [Manual por rol](docs/V5-MANUAL.md)
- [Procesos y arquitectura](docs/V5-PROCESOS.md)
- [Diccionario de las fuentes persistentes](docs/V5-DATOS.md)
- [Catálogo de métricas](docs/V5-METRICAS.md)
- [Contrato transaccional](specs/v5-domain-api.md) y [contrato de agentes](specs/v5-intelligence.md)
- [Verificación V6 y pendientes de aceptación](docs/V6-VERIFICACION.md)
- [Requisitos GSD](.planning/milestones/v5.0-REQUIREMENTS.md), [hoja de ruta](.planning/ROADMAP.md) y [estado](.planning/STATE.md)

## Comprobar el código

```powershell
$env:MILENIO_MODE='test'
$env:MILENIO_DATA_DIR=Join-Path $PWD 'private/test'
.\.venv\Scripts\python.exe manage.py test workshop.tests
.\.venv\Scripts\python.exe manage.py makemigrations --check --dry-run
```

La suite V6 ejecutó 115 pruebas: 113 pasaron, dos omitieron el arranque porque los puertos estaban ocupados y no hubo fallos. El paquete extraído se verificó por separado con dependencias offline, servidor autenticado en puerto temporal, trabajador, migración y restauración. Los ensayos usan bases temporales y datos ficticios. No acreditan adopción, rendimiento con la carga del cliente ni impacto comercial. La entrega sirve como aplicación local para un piloto controlado. CFDI, cobros bancarios, mensajería, telemetría, diagnóstico mecánico automático y servicio alojado multiempresa quedan fuera de esta versión.

## Versiones anteriores

El [estudio V4](README-V4.md) y las herramientas analíticas V1–V4 permanecen disponibles para snapshots, Excel, procesos históricos y consultoría. Sus tablas, métricas y recibos pertenecen a contratos separados: no se suman a las 24 fuentes/18 métricas de V5 ni prueban operación nativa de esta versión. Licencia MIT.
