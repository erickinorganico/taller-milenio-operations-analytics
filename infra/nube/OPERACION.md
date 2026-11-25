# Comprobar el servidor del taller

En el VPS Ubuntu, después del primer respaldo y del primer simulacro, ejecuta desde `/opt/milenio`:

```bash
sudo bash infra/nube/deploy.sh status
sudo bash infra/nube/deploy.sh verify-url
sudo python3 -B infra/nube/operacion.py
```

El primer comando comprueba la aplicación local. El segundo abre por HTTPS el acceso a la cuenta y comprueba el bloqueo del alta inicial. El tercero comprueba el servidor en modo lectura. Devuelve código **0** cuando pasan todos sus controles o **1** con las líneas **REVISAR** que necesitan atención. Un monitor existente puede recoger ese código. Gerencia conserva los resultados en su expediente privado y comprueba que recibe avisos también cuando se apaga el VPS.

| Control | Si aparece REVISAR |
|---|---|
| SSH | Verifica que la consola de recuperación del proveedor funciona y prueba una segunda sesión por llave. Revisa el acceso global por contraseña y teclado interactivo. Si usas reglas SSH por usuario o red, valida también la configuración efectiva de esa cuenta con `sshd -T -C`. Conserva el acceso actual mientras verificas cualquier cambio. |
| Puertos | Comprueba los listeners TCP y los puertos que Docker publica por TCP o UDP, incluidos los que Docker reenvía mediante NAT. Se esperan 80 y 443 TCP y los puertos SSH configurados. Revisa los servicios adicionales y su necesidad. En el firewall del proveedor, limita SSH al origen administrativo cuando cuentes con uno estable. Comprueba sus reglas IPv4 e IPv6 y los servicios UDP del host. |
| Actualizaciones | Comprueba `apt-daily-upgrade.timer` y los valores periódicos de APT. Revisa el origen de las actualizaciones permitidas, el resultado de la última ejecución y `/var/run/reboot-required`. Acuerda reinicios fuera del horario de atención. Las imágenes de contenedor se actualizan mediante una revisión del repo, pruebas y `deploy.sh apply`. |
| Respaldo y simulacro | Comprueba que el timer está activo, el recibo de la última copia tiene menos de 26 horas y el simulacro menos de 35 días. Ante un fallo consulta `sudo journalctl -u milenio-nube-backup.service -n 30 --no-pager` y verifica que B2 conserva el ID. Un recibo acredita un éxito anterior. Comprueba la restauración de una foto y una orden en la revisión mensual. |
| Disco | Antes de la copia se estima el tamaño de SQLite, del journal y de las evidencias. La copia diaria rechaza espacio insuficiente antes de pausar el servicio. El simulacro consulta el tamaño sin comprimir del snapshot y reserva espacio para la descarga y la copia validada. El margen operativo es el mayor de 512 MiB o el 5 % del volumen. Si el margen se agota, revisa el crecimiento de fotos y los archivos temporales con Gerencia. Conserva las evidencias y la última copia confirmada. |

Una actualización interrumpida deja la marca `.pending-release`. Mientras exista, la tarea de respaldo rechaza crear un snapshot de esa instalación. Retoma la revisión exacta con `deploy.sh apply` o sigue la guía de recuperación para volver a la copia previa. Con el taller recuperado, ejecuta una copia y un simulacro.

Al actualizar después de `docker compose down`, el respaldo sigue usando la imagen del commit instalado que figura en `/etc/milenio/nube.env`. Si falta esa imagen o su etiqueta interna corresponde a otro commit, se detiene antes de migrar o registrar una nueva copia. Recupera la imagen de la revisión instalada y vuelve a ejecutar la actualización.

La verificación local mide el estado del VPS en ese momento. Comprueba también el certificado y el folio desde el celular por datos móviles, la configuración de red en el panel del proveedor y una recuperación con credenciales de B2 guardadas fuera del VPS. [Recuperación del taller](backup/README.md) · [Acceso SSH en Ubuntu](https://ubuntu.com/server/docs/how-to/security/openssh-server/) · [Actualizaciones automáticas de Ubuntu](https://ubuntu.com/server/docs/how-to/software/automatic-updates/)
