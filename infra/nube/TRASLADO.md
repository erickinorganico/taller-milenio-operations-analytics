# Trasladar una central Windows que ya tiene órdenes

Gerencia acuerda el corte con Recepción y Administración. Antes de mover archivos, registra en privado la revisión instalada, el número de órdenes/clientes, totales de facturación y saldo, un folio reciente y una foto que se pueda cotejar. Programa una pausa y conserva el sistema anterior en modo consulta o apagado después de la última copia. Abrir las dos centrales a capturas produciría dos historiales diferentes.

1. Detén el supervisor de Windows antes de ejecutar la copia definitiva. El script de respaldo reanuda una central que encontró en marcha. Usa el [procedimiento de respaldo](../DESPLIEGUE-Y-RECUPERACION.md) para generar la copia portable con su manifiesto, base y evidencias. Asegura que no entren nuevas operaciones después del corte. Verifica que ese respaldo corresponde a la central y contiene los archivos esperados.
2. Anota el SHA-256 de **manifest.json** obtenido en la PC de origen con PowerShell y el valor de 64 caracteres **release_id** de **private/infra.local.json**. Transfiere el directorio completo del respaldo por SSH/SFTP al almacenamiento privado del VPS. Confirma el SHA recibido por separado. Reserva espacio temporal para la operación; el importador comprueba espacio antes de escribir. Si el respaldo de origen es grande, estima el espacio adicional y su costo antes de contratarlo. Los datos deben quedar fuera del repositorio y de las carpetas web.

```powershell
Get-FileHash -Algorithm SHA256 -LiteralPath 'RUTA-DEL-RESPALDO\manifest.json'
```

3. En un destino nuevo, antes de la instalación vacía, ejecuta la importación. Sustituye los tres valores en mayúsculas por el directorio privado, SHA-256 y la release del origen. El importador usa una copia temporal y protege el destino ocupado.

```bash
cd /opt/milenio
sudo bash infra/nube/deploy.sh init taller.autoserviciomilenio.com
sudo bash infra/nube/deploy.sh import-windows /RUTA/PRIVADA/RESPALDO SHA256_MANIFIESTO RELEASE_WINDOWS
sudo bash infra/nube/deploy.sh activate-restored
sudo bash infra/nube/deploy.sh status
sudo bash infra/nube/deploy.sh verify-url
```

4. Accede con la cuenta de Gerencia recuperada y compara los totales, folio, fotos y permisos que registraste en origen. Prueba una orden nueva entre dos dispositivos. Verifica el primer respaldo cifrado de la nube y recupera una muestra. Mantén la constancia y la copia Windows bajo custodia privada.

**Vuelta atrás.** Si falla la validación antes de reabrir al personal, aísla el VPS y reanuda únicamente la central Windows en el punto del corte. Si el VPS ya recibió operaciones, congela ambas vías de escritura, respalda el VPS y concilia los folios, fotos y cobros posteriores antes de cambiar el acceso. Restaurar la copia anterior por sí sola perdería esas operaciones. Los snapshots de restic generados ya en nube se recuperan con [restore-new](backup/README.md).
