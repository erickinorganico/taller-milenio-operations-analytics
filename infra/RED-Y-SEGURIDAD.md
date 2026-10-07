# Seguridad del despliegue descargable

La implementación elige **OpenSSH con túnel a loopback**. Sustituye el proxy HTTPS/VPN de la propuesta inicial. HTTP solo se usa entre navegador local y túnel local y entre SSH/Waitress en el servidor; el tránsito entre PCs está cifrado y autentica la llave pública del host. No usar un túnel cuya llave se haya aceptado sin verificar ni publicar Waitress.

Setup-RemoteAccess crea una instancia SSH separada: puerto 2222, cuenta estándar dedicada, solo llaves Ed25519, contraseñas SSH deshabilitadas, shell/PTY deshabilitados, reenvío permitido únicamente a 127.0.0.1:puerto-Milenio. El firewall acepta IP privadas individuales indicadas, en perfiles Private/Domain. No abre rangos completos ni cambia el router. Un administrador debe verificar la política efectiva y otras reglas existentes en destino.

Crear Gerencia local antes de ejecutar acceso remoto; el script lo comprueba. Cada operador tiene usuario propio del CRM; cada agente token propio revocable, con permisos mínimos. Llave SSH y usuario/token del CRM son controles separados. Perder un equipo exige retirar su llave y revocar su token/sesión. Windows/SSH deben estar actualizados; el instalador no certifica la seguridad global de la máquina.

Setup-Server limita ACL de su carpeta al instalador y SYSTEM; el proceso corre bajo el mismo usuario Windows que protege OAuth con DPAPI. El arranque con contraseña usa el Programador de tareas; no guarda contraseña en un JSON ni en GitHub. El modo al iniciar sesión tiene menor disponibilidad. DPAPI no se vuelve portátil por copiar el archivo; sustituir equipo requiere reconectar Google y deshabilitar el anterior.

Datos y backups no se suben al repo público. El backup es un formato verificable con hashes, no cifrado propio. Elegir disco/almacenamiento cifrado y privado; el destino local por defecto no protege ante pérdida del disco. Se conservan copias anteriores sin borrado automático. Secrets Django/Gmail se excluyen del backup normal; sesiones se invalidan y Google se reconecta al recuperar. Los tokens de agentes restaurados se revocan.

La aplicación no debe configurarse con MILENIO_HTTPS para el transporte SSH/loopback; no hay proxy de encabezados que confiar. Un despliegue HTTPS alternativo requiere su configuración y pruebas propias. Los controles de clave SSH limitan llegada al login; no se afirma que el login web tenga segundo factor integrado.

Referencias: [OpenSSH en Windows](https://learn.microsoft.com/en-us/windows-server/administration/OpenSSH/openssh-server-configuration), [Programador de tareas](https://learn.microsoft.com/en-us/powershell/module/scheduledtasks/register-scheduledtask), [SQLite sobre red](https://www.sqlite.org/useovernet.html). La base siempre se abre localmente en el servidor, nunca por una unidad compartida.
