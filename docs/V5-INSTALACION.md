# Milenio V5: instalación local y recuperación

Esta edición ejecuta una instancia de un solo taller en Windows. Los registros reales se guardan en SQLite y en `media/`; la demostración usa otra base. El servidor Waitress escucha únicamente en `127.0.0.1`. No configure acceso desde otros equipos sin un despliegue HTTPS y una revisión de seguridad separados.

## Antes de empezar

- Windows con Python 3.12 o posterior y espacio para la base, fotos y respaldos.
- Extraiga el paquete completo en una carpeta de trabajo. Conserve juntos `manage.py`, `workshop/`, `milenio_web/`, `requirements-web.txt`, `Setup-Web.ps1` e `Iniciar-Milenio.cmd`.
- De forma predeterminada, los datos se guardan fuera del paquete en `%LOCALAPPDATA%\Milenio\operational\live` o `%LOCALAPPDATA%\Milenio\operational\demo` (si falta `LOCALAPPDATA`, en `AppData\Local` del usuario). La consola muestra la ruta activa al iniciar. En PowerShell puede elegir otra ubicación antes de iniciar con `$env:MILENIO_DATA_DIR = 'C:\MilenioDatos\live'`; para demo use otra carpeta cuyo nombre final sea `demo`. Proteja la carpeta de datos con permisos de Windows y respaldos adecuados. No coloque datos de clientes en una carpeta sincronizada si puede evitarlo.
- `Setup-Web.ps1` crea `.venv` e instala las versiones exactas de `requirements-web.txt` cuando faltan. Para una instalación sin red, coloque las ruedas compatibles en `.runtime/wheels` y ejecute `powershell -NoProfile -ExecutionPolicy Bypass -File .\Setup-Web.ps1 -Offline`. No reutilice ruedas de otra versión de Python.

## Primera apertura real

1. Ejecute `Iniciar-Milenio.cmd`. Se revisan Python y las dependencias, se aplican migraciones y se abre `http://127.0.0.1:8765/`.
2. En una base nueva, `/setup/` solicita crear el primer usuario administrador y su contraseña. No hay contraseña fija. Conserve esa contraseña mediante el procedimiento del taller; la aplicación guarda un hash, no una copia legible.
3. Inicie sesión y cree las cuentas del equipo en **Equipo y acceso** (`/team/`). Asigne solo los roles que cada persona necesita. Desde `/team/<id>/edit/` gerencia puede cambiar roles o contraseñas y desactivar cuentas; cada persona cambia la suya en `/account/`.
4. Confirme que clientes, órdenes y métricas están vacíos antes de capturar datos reales. Una instalación `live` nunca recibe la semilla demo.

`Iniciar-Demo.cmd` usa `127.0.0.1:8766` y un directorio `demo` separado. Si la base demo no contiene datos operativos, el lanzador aplica una semilla ficticia una sola vez. La primera apertura conduce a `/setup/` para que el usuario cree su propio administrador y contraseña; la semilla no publica una credencial. No copie clientes reales a demo ni utilice su contraseña para `live`.

Si usó una edición anterior con datos en `private/operational/live` o `private/operational/demo`, el lanzador detiene el inicio cuando encuentra esa base y la nueva ubicación aún está vacía. No mueve ni borra la base anterior. Para seguir usándola de forma temporal, establezca `MILENIO_DATA_DIR` en su carpeta actual, terminada en `live` o `demo`. Para trasladarla, haga un `backup_workshop` desde esa instancia, inicie una instalación separada en la nueva ubicación y ejecute `restore_workshop --confirm-restore` con el servidor detenido. Conserve la base anterior y el respaldo hasta verificar registros, archivos y acceso en la nueva ubicación. El respaldo incluye base y `media/`; la restauración conserva la clave privada de la instalación de destino y cierra todas las sesiones anteriores. No copie solo `workshop.sqlite3`.

Los lanzadores aceptan `--no-browser` al final para comprobaciones supervisadas. `Ctrl+C` detiene el servidor y conserva la base. Si el puerto está ocupado, el inicio falla con un mensaje; no cierra otro proceso. El acceso al navegador depende de que esa consola permanezca abierta.

## Respaldo

Detenga la captura y evite cambios en archivos de evidencia durante un respaldo. Desde la raíz del proyecto, con la misma variable `MILENIO_DATA_DIR` y el modo correcto:

```powershell
$env:MILENIO_MODE = 'live'
.\.venv\Scripts\python.exe manage.py backup_workshop --output 'D:\RespaldosMilenio\2026-09-22'
```

El destino debe ser una carpeta nueva. El comando usa la API de respaldo de SQLite, copia `media/` y escribe `manifest.json` con hashes e inventario de migraciones. Comprueba integridad antes de terminar. La clave privada `.secret_key` se excluye: se conserva en la instalación, no en el respaldo. Proteja el respaldo porque **sí contiene datos de clientes y evidencia**. Pruebe periódicamente la restauración en una instalación separada con el mismo modo y versión de código.

## Restauración

Detenga el servidor con `Ctrl+C` y confirme que el puerto ya no responde. Use la misma instalación, modo y versión de código que generó el respaldo. El comando no acepta una carpeta alterada ni mezcla `demo` con `live`:

```powershell
$env:MILENIO_MODE = 'live'
.\.venv\Scripts\python.exe manage.py restore_workshop --input 'D:\RespaldosMilenio\2026-09-22' --confirm-restore
```

Primero se verifican rutas, hashes, `PRAGMA integrity_check` y migraciones en una copia temporal. Después se cierran conexiones, se sustituyen la base y `media/`, y se eliminan sesiones para que todos vuelvan a iniciar sesión. La base y los archivos anteriores permanecen en `recovery-before-*` dentro del directorio de datos. Revise la aplicación y sus registros antes de retirar esa copia. La clave de la instalación no se sustituye. Si falla una validación, la base activa no se toca.

No restaure un ZIP de entrega como si fuera un respaldo de clientes: solo una carpeta creada por `backup_workshop` cumple este contrato. No use Git ni los artefactos analíticos V4 como almacenamiento operativo.

## Comprobación del primer día

Confirme por separado: inicio y cierre de sesión; roles con acceso esperado; alta de cliente y vehículo; orden con autorización humana documentada; movimiento de refacciones; control de calidad; entrega; comprobante administrativo y pago parcial; saldo y métrica correspondientes; respaldo íntegro; restauración ensayada en otra instalación. Registre incidencias y decisiones del taller. Esta comprobación local no acredita adopción, exactitud fiscal ni impacto financiero.
