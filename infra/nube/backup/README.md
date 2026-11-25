# Recuperar órdenes y fotos si se pierde el VPS

La copia diaria contiene la base SQLite y los archivos de evidencia. La aplicación registra la huella SHA-256 de cada archivo en un manifiesto y restic cifra los datos antes de enviarlos al bucket privado en Backblaze B2. El identificador completo del snapshot y el commit del código permiten reconstruir la pareja correcta en otro VPS. La primera copia y su simulacro en B2 forman parte de la aceptación en destino.

## Preparar el almacenamiento y las llaves

1. En la cuenta del taller, activa MFA en B2 y crea un **bucket privado** dedicado. Anota en el gestor de contraseñas de Gerencia la región, el endpoint S3, el nombre del bucket y el prefijo `taller`. Usa otro proveedor o cuenta que la del VPS.
2. Crea una **application key** limitada a ese bucket y a los objetos del repositorio. Restic requiere listar, leer, escribir y quitar objetos, incluidos sus bloqueos. Usa credenciales de aplicación compatibles con S3 y la región del endpoint. La cuenta administradora y la llave maestra quedan en Gerencia. Quien controle la llave operativa y el VPS podría eliminar snapshots. Para cubrir ese escenario, Gerencia puede guardar periódicamente otra copia cifrada fuera del alcance de esa llave. La política de retención de restic necesita poder quitar bloqueos y paquetes vencidos. [Llaves S3 de B2](https://www.backblaze.com/docs/cloud-storage-s3-compatible-app-keys) · [Repositorios de restic](https://restic.readthedocs.io/en/stable/030_preparing_a_new_repo.html).
3. En Linux instala `restic`, `openssl`, Python 3 y `flock` (paquete `util-linux`). En Ubuntu/Debian se puede usar `sudo apt-get install restic openssl python3 util-linux`. Desde `/opt/milenio`, crea la configuración privada. Ejecuta el bloque una sola vez, con los valores reales editados en el servidor. El comando de generación se detiene si la contraseña ya existe.

```bash
sudo install -d -m 700 /etc/milenio
sudo bash -c 'set -C; umask 077; openssl rand -hex 32 > /etc/milenio/restic-password'
sudo bash -c 'set -C; umask 077; cat infra/nube/backup/backup.env.example > /etc/milenio/backup.env'
sudoedit /etc/milenio/backup.env
```

4. Guarda una copia de la **contraseña de restic** en el gestor de Gerencia fuera del VPS, junto con la recuperación MFA de B2 y el acceso al repositorio Git. En una emergencia, la cuenta administradora puede emitir otra llave S3. Para descifrar el repositorio se requiere la contraseña original o una segunda llave restic preparada previamente. La clave Django y los secretos de B2 se excluyen del snapshot. En una recuperación se genera una clave Django nueva. [Gestión de llaves de restic](https://restic.readthedocs.io/en/stable/070_encryption.html).
5. Inicializa un repositorio **nuevo** una sola vez. Para conectar un repo que ya contiene copias usa `list`. Con el taller instalado, crea la primera copia y ensaya su restauración antes de iniciar la rutina.

```bash
sudo bash infra/nube/backup/backup.sh init
sudo bash infra/nube/backup/backup.sh run
sudo bash infra/nube/backup/backup.sh list
sudo bash infra/nube/backup/backup.sh restore-test
```

## Operación diaria y costo

El servicio suspende durante la copia local los procesos con escritura (web, captura y analítica). Valida SQLite y los hashes de las fotos. Vuelve a iniciar exactamente los procesos que estaban en marcha y después sube la copia cifrada. La pausa depende del tamaño de los datos. El bloqueo único de mantenimiento impide actualizar o restaurar mientras se genera el respaldo. Antes de actualizar una instalación existente, el instalador llama a `pre-upgrade` con todos los escritores detenidos y bloqueo heredado. Sólo continúa después de confirmar el ID remoto.

```bash
sudo install -m 644 infra/nube/backup/milenio-nube-backup.{service,timer} /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now milenio-nube-backup.timer
systemctl list-timers milenio-nube-backup.timer
sudo journalctl -u milenio-nube-backup.service -n 30 --no-pager
```

La tarea está configurada para las 03:15 de Tijuana, con hasta cinco minutos de variación. Si el servidor estaba apagado, systemd la ejecuta al volver. Con un respaldo diario exitoso pueden perderse hasta aproximadamente 24 horas de operaciones. Después de cada carga se actualiza `ultimo-respaldo.json` en `/var/lib/milenio-cloud` (o en el directorio de estado configurado). La fecha anterior permanece visible cuando un intento falla. Gerencia debe revisar el estado fuera del servidor o conectar el monitor existente a una alerta por recibo con más de **26 horas**. El temporizador escribe su resultado en el journal. Anotar quién recibe avisos y comprobar una alerta antes de considerar cubierta la vigilancia.

Deja espacio en el disco del VPS para staging de una copia completa. Un simulacro descarga el snapshot y prepara otra copia para restaurarlo; reserva espacio para **dos juegos adicionales** además del estado activo y contempla el caché de restic. Programa `check` fuera de hora pico: lee todo el repositorio y puede consumir descargas. La retención propuesta conserva las últimas tres copias, siete diarias, cuatro semanales y seis mensuales. Una vez al mes, verifica el simulacro y revisa los snapshots que vencerán antes de ejecutar `prune`. Si quedan versiones antiguas ocultas en B2 seguirán consumiendo almacenamiento. En el prefijo del repositorio, las reglas de B2 deben afectar **sólo versiones antiguas u ocultas**. Borrar objetos vigentes por edad dañaría copias que todavía dependen de ellos. [Retención de restic](https://restic.readthedocs.io/en/stable/060_forget.html) · [Reglas de B2](https://www.backblaze.com/docs/cloud-storage-lifecycle-rules).

```bash
sudo bash infra/nube/backup/backup.sh restore-test
sudo bash infra/nube/backup/backup.sh check
sudo bash infra/nube/backup/backup.sh retention
# Al aceptar la previsualización de retención:
sudo bash infra/nube/backup/backup.sh prune
```

## Recuperación en otro VPS

1. Confirma que el servidor anterior está apagado o aislado. Conserva sus discos y usa un VPS de reemplazo. Instala Docker con Compose, Python 3 y restic. Recupera la configuración de B2 y su contraseña en `/etc/milenio/` con permisos `0600`.
2. Clona el repositorio en `/opt/milenio`. Usa `sudo bash infra/nube/backup/backup.sh list` y registra el ID completo y el commit `git-…` de la copia elegida. Prepara el archivo privado de la nube y los directorios según la [guía de la nube](../README.md). Crea el directorio persistente padre (por defecto `/var/lib/milenio-cloud`). El subdirectorio `app` puede faltar o estar completamente vacío.
3. Selecciona esa revisión de Git en el reemplazo y construye su imagen, sin iniciar la web. Pasa el commit a Docker y al comando de recuperación si todavía no figura en el archivo privado.

```bash
cd /opt/milenio
revision=$(git rev-parse HEAD)
sudo env MILENIO_BUILD_REVISION="$revision" docker compose --env-file /etc/milenio/nube.env -f infra/nube/compose.yaml build app
sudo env MILENIO_BUILD_REVISION="$revision" bash infra/nube/backup/backup.sh restore-new ID_COMPLETO_DE_LA_COPIA
```

Si se interrumpe la promoción al directorio definitivo, repite `restore-new` con el mismo ID y revisión. El recibo privado permite reconocer el directorio exacto que ya se restauró y completar la operación sin reemplazar sus datos.

4. El proceso confirma la revisión, los archivos, hashes y esquema. Restaura primero a un directorio temporal y lo instala en el destino vacío. Las sesiones caducan, las credenciales de agentes se revocan y el correo queda retenido. El comando rechaza destinos ocupados. Revisa el recibo `ultima-restauracion.json` y ejecuta `sudo bash infra/nube/deploy.sh activate-restored` en el reemplazo. El instalador valida que el recibo identifica la revisión del checkout y que el esquema está completo. Coordina el cambio de DNS y comprueba el enlace con `sudo bash infra/nube/deploy.sh verify-url`. Confirma en privado con una persona del taller un folio y su foto, la cronología de órdenes y cobros, el acceso de los roles, analítica y captura. Comprueba el siguiente respaldo en el VPS nuevo.

## Ensayo reproducible

En un **runner Linux desechable** con Docker Compose, Python 3, git, restic, OpenSSL y flock, el siguiente comando crea una instancia aislada con datos ficticios. Usa un repositorio restic cifrado local, simula una actualización y recupera a una instancia vacía. Verifica la conservación de la evidencia, el cierre de sesiones, el rechazo de un destino ocupado y el respeto de los procesos que estaban parados. La cuenta B2, el ancho de banda, la alerta externa y la restauración con las credenciales reales se comprueban en destino.

```bash
sudo env MILENIO_DISPOSABLE_LINUX_RUNNER=1 bash infra/nube/backup/test-roundtrip.sh
```
