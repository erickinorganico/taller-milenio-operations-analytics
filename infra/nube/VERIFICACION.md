# Qué se prueba y dónde

La rama de esta entrega es `codex/nube-economica-taller-20261124`. El SHA completo de cada revisión se consulta en Git y en el registro de su ejecución. Antes de un cambio en producción, registra ese SHA exacto en el expediente privado y selecciona esa revisión en un checkout limpio.

| Prueba | Criterio comprobable | Dónde repetirla |
|---|---|---|
| HTTPS | Caddy presenta certificado cuyo emisor confía el cliente de ensayo. Recepción crea cliente, vehículo, orden e inspección con foto. Gerencia consulta esa foto desde una sesión independiente. Después del reinicio coinciden el folio y los bytes de la foto. Alta pública y lecturas de fotos sin sesión están cerradas. | `python scripts/verify_cloud_https.py` con Docker local; usa CA de prueba, puertos en loopback y datos ficticios. |
| Primera instalación y actualización | Repetir instalación conserva versión y base. Fallar el respaldo evita migrar. Fallar la migración deja la instalación en mantenimiento y permite reintentar. | Ensayo de operador en [.github/workflows/nube.yml](../../.github/workflows/nube.yml), con un contenedor desechable y un simulador de Docker. |
| Respaldo y recuperación | Restic cifra el repositorio. La recuperación en otro directorio conserva la evidencia, invalida sesiones y rechaza sobrescribir un destino ocupado. | [Ensayo Linux de recuperación](backup/README.md), con SQLite, Docker y un repositorio restic temporal. |
| Traslado de Windows | Una copia portable del esquema anterior conserva cliente, vehículo, orden, factura, pago y foto. Las sesiones anteriores caducan. Un SHA incorrecto y un destino ocupado impiden la importación. | [Ensayo reproducible del traslado](tests/portable-roundtrip.sh). |
| Aplicación y compatibilidad | Ejercita permisos, recepción, protección de fotos, bloqueo de proveedores externos y actualizaciones del paquete Windows. | [Pruebas de nube](../../workshop/tests/test_cloud.py) y [verificación de operaciones](../../.github/workflows/verify.yml). |
| Puesta en servicio | Certificado público, acceso desde un teléfono físico por datos móviles, restauración con B2 real, reinicio del VPS, fondos disponibles, alertas y respaldo posterior al traslado. | [Aceptación en destino](README.md#4-preparar-el-respaldo-y-probar-el-servicio), en la cuenta privada de Milenio. |

Las pruebas locales emplean sesiones HTTP independientes con identificación de móvil y escritorio. El certificado de producción, la resolución DNS pública del destino, el funcionamiento en Safari o Chrome físicos y la capacidad del plan se acreditan en el VPS contratado. Guarda sólo métricas y estados en GitHub. Los teléfonos, credenciales, fotografías, facturas y datos de clientes se conservan en el expediente privado.
