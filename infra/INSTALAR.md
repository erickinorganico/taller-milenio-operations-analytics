# Instalación guiada para Codex

## 1. Preparación

Leer AGENTS.md; consultar estado Git y modificaciones antes de actuar. Usar la versión descargada que contiene este documento, no una release antigua. No copiar `.venv`, `private`, bases, tokens ni sesiones de otra computadora. Revisar si existe una instalación anterior en LocalAppData/MilenioServer o una instancia antigua del taller: no migrar ni reemplazarla silenciosamente.

PowerShell, desde la descarga:

```powershell
.\Setup-Server.ps1
```

Predeterminado: LocalAppData/MilenioServer, puerto 8770. `-InstallRoot`, `-BackupDir`, `-Port` y `-PythonPath` permiten ajustar sin editar código. `-Offline` requiere Python 3.12 ya instalado y `.runtime/wheels` en el paquete. El ZIP de código requiere conexión para descargar dependencias. Python se instala con winget si falta y está disponible; si Windows no ofrece winget, instalar Python 3.12 desde python.org. No se descarga un ejecutable de una fuente no verificada.

Estructura: `releases/<hash>/` código + entorno; `data/live/` base/medios/DPAPI; `private/` configuración, release seleccionada y logs; `backups/` copias. La carpeta entera está limitada al usuario instalador y SYSTEM. Usar esa misma identidad al registrar arranque y conectar Gmail.

## 2. Gerencia y datos

Abrir `http://127.0.0.1:8770/setup/`, crear Gerencia y usuarios individuales. Codex puede guiar por navegador; la contraseña no se guarda en el repositorio. El acceso remoto rechaza instalación sin Gerencia.

Para operaciones desde PowerShell:

```powershell
$install = Join-Path $env:LOCALAPPDATA 'MilenioServer'
$current = Get-Content (Join-Path $install 'private/current.json') -Raw | ConvertFrom-Json
$env:MILENIO_DEPLOYMENT_CONFIG = Join-Path $install 'private/infra.local.json'
$python = Join-Path $current.release_dir '.venv/Scripts/python.exe'
$deploy = Join-Path $current.release_dir 'scripts/deploy.py'
& $python $deploy status
```

Para importar el catálogo privado vigente, transferir su JSON por un canal privado y usar `deploy.py manage import_commercial_catalog --input <archivo> --owner <gerencia>`. Conserva IDs y evidencia; no habilita campañas. También puede colocarse en `data/live/imports/catalog.json` para el botón del panel. GitHub no distribuye las 485 fichas ni contiene una copia de datos del taller.

## 3. Arranque continuo y respaldo

Desde la release instalada, ejecutar `Register-ServerStartup.ps1 -InstallRoot <instalación>` con elevación cuando Windows la requiera. Pide la credencial Windows del mismo usuario; se entrega al Programador de tareas, nunca a Codex ni a GitHub. Registra supervisor al arrancar y respaldo diario a las 03:00. Alternativa sin almacenar contraseña: `-AtLogon`; en ese caso depende de iniciar sesión y las tareas solo corren con sesión disponible.

Comprobar reinicio real, workers, identidad, acceso DPAPI y respaldo. No declarar 24/7 por registrar una tarea. Elegir un destino separado del disco principal para recuperación ante avería; la copia local predeterminada solo protege ante errores lógicos. Los archivos de respaldo deben estar en almacenamiento privado/cifrado; el formato de backup no agrega cifrado propio ni borra copias automáticamente.

## 4. Acceso de los clientes

En cada cliente generar una llave Ed25519 mediante `ssh-keygen -t ed25519`, con frase de protección cuando sea viable. Entregar al servidor solamente su `.pub`. En el servidor, después de crear Gerencia, ejecutar PowerShell elevado:

```powershell
.\Setup-RemoteAccess.ps1 -InstallRoot <instalación> -AllowedAddresses <IP-privada-cliente-A>,<IP-privada-cliente-B> -ClientPublicKeyFiles <A.pub>,<B.pub>
```

Crea una cuenta Windows dedicada al túnel, un proceso OpenSSH separado en 2222, y firewall para esas IP privadas individuales. No cambia el servicio SSH existente. `MaxSessions 0` impide shell; solo se permite reenviar al puerto web de loopback. No usar una cuenta de administrador como TunnelUser. Si ese nombre ya pertenece a otro uso, se rechaza.

Compartir la llave pública del host por un canal confiable y comparar su huella. En cada cliente, desde su descarga:

```powershell
.\Setup-Client.ps1 -InstanceId <UUID-del-central> -ReleaseId <hash-release> -ServerAddress <IP-privada-servidor> -SshUser milenio_tunnel -PublicHostKey 'ssh-ed25519 <llave-publica-verificada>' -IdentityFile <llave-privada-local>
.\Connect-Server.ps1
```

No introducir esos placeholders literalmente. Consultar UUID/hash en `deploy.py status`; los datos concretos se guardan privados. Con el túnel abierto, usar `http://127.0.0.1:8770`. No ejecutar Setup-Server ni Abrir-Taller en el cliente. Cambios de IP requieren actualizar la regla explícita. Fuera de la misma red hace falta ruta privada/VPN ya funcional; no publicar el puerto web a Internet.

## 5. Codex y Gmail

Emitir una credencial por agente mediante `deploy.py manage agent_access --owner <gerencia> --label <equipo> --output <carpeta-private/agente.json>`. Predeterminado: lectura/preparación. `--allow-send` agrega permiso de encolar, sujeto a autorización comercial concreta; `--read-only` limita a consulta. Transferirla por canal privado. Nunca imprimir el token. Vence en 90 días y se revoca con `--revoke <id>`.

OAuth: `deploy.py manage connect_gmail --client <OAuth-desktop.json> --owner <gerencia>`, bajo el usuario Windows instalado. Después de revisar una prueba controlada, habilitar transporte con `deploy.py manage deployment_mail --enable --authorization <referencia>`. Activar la campaña por separado desde Comercial → Correo. Nada de esto se hace durante la instalación de software ni constituye permiso para contactar todo el catálogo.

Cerrar usando [ACEPTACION.md](ACEPTACION.md). Guardar resultados y configuración de equipos en `private`, nunca en GitHub. Las acciones que precisan credenciales o presencia del segundo equipo quedan identificadas; completar antes todo lo demás.
