# Taller Milenio desde el celular

La dirección prevista es **taller.autoserviciomilenio.com**. Desde Safari o Chrome, cada persona inicia sesión con su cuenta y puede guardar la dirección en la pantalla de inicio. La PC de recepción puede estar apagada. Ante un corte del Wi-Fi se puede usar la red móvil. Registrar órdenes requiere conexión al servicio.

**Para Gerencia.** Reutilizar un VPS de Milenio si reúne los requisitos. Como primera compra, elegir InterServer Linux KVM de un slice, con facturación mensual sin compromiso, y una copia cifrada en Backblaze B2. El presupuesto autorizado es USD 7/mes en total. [Presupuesto, cálculo y alternativas](COSTOS.md)

| Si necesitas… | Abre esta guía |
|---|---|
| Decidir si confiarle los datos a este proveedor | [Evaluación de InterServer y verificaciones antes del alta](SEGURIDAD-PROVEEDOR.md) |
| Tomar una foto en el celular y verla en recepción | [Fotos de inspección y reintentos](FOTOS.md) |
| Dar a un agente acceso a un indicador o a una orden | [Permisos, ejemplos y revocación](AGENTES.md) |
| Saber si la copia, el disco y los servicios están bien | [Diagnóstico del servidor](OPERACION.md) |

## 1. Preparar el servidor

1. En la cuenta de la empresa, activa MFA y guarda sus códigos de recuperación en el gestor de contraseñas de Gerencia. Elige Ubuntu Server 24.04 LTS, disco persistente, IPv4 pública y acceso administrativo por llave SSH individual. Para el plan propuesto se esperan 2 GB de RAM y 40 GB de disco. Revisa moneda, impuestos, renovación y total mensual antes de confirmar el pedido.
2. Restringe SSH TCP 22 a la IP o VPN de administración. Abre TCP 80 y 443 a los usuarios para el certificado y la aplicación. Revisa IPv4 e IPv6 en el firewall del proveedor. Conserva acceso por consola de recuperación y prueba la llave en una segunda sesión antes de deshabilitar el acceso SSH por contraseña. Docker puede gestionar sus propias reglas de puertos. [Red de Docker y firewalls](https://docs.docker.com/engine/network/packet-filtering-firewalls/)
3. En Ubuntu Server instala Git con `sudo apt-get update && sudo apt-get install -y git`. El script del paso siguiente instala Docker y Compose desde Ubuntu, restic, las herramientas de verificación y las actualizaciones de seguridad. Si Docker ya existe, usa su complemento Compose v2. Programa los reinicios fuera de la jornada. [Docker Engine](https://docs.docker.com/engine/install/ubuntu/) · [Actualizaciones de Ubuntu](https://ubuntu.com/server/docs/how-to/software/automatic-updates/)

4. Clona el código en **/opt/milenio**, de propiedad de root. La rama de la entrega está en el registro de verificación. Fija el commit revisado antes de instalar. El instalador comprueba que el checkout está limpio y que la imagen pertenece a esa revisión. La configuración privada queda en **/etc/milenio**, los datos en **/var/lib/milenio-cloud**. GitHub contiene el software y los procedimientos.

```bash
sudo git clone https://github.com/erickinorganico/taller-milenio-operations-analytics.git /opt/milenio
cd /opt/milenio
sudo git switch --detach origin/codex/nube-economica-taller-20261124
sudo git rev-parse HEAD
sudo bash infra/nube/preparar-host.sh
```

## 2. Preparar el subdominio

El 24/nov/2026 el DNS público señaló a Cloudflare como autoridad. El nombre **taller** devolvió cero direcciones A, AAAA y CNAME en la consulta. Repite la lectura al abrir el panel y comprueba que ese nombre no pertenezca a otro servicio.

En la zona **autoserviciomilenio.com**, crea un registro **A**, nombre **taller**, con la IPv4 asignada al VPS, **Sólo DNS** y TTL automático. La web principal, www y el correo tienen sus propios registros. Crea un AAAA para taller únicamente si el VPS sirve correctamente por IPv6. Caddy solicita y renueva el certificado del subdominio. Este perfil toma la IP directa del cliente para limitar intentos de acceso; activar el proxy de Cloudflare requiere configurar y probar esa cadena de confianza. [Crear un registro en Cloudflare](https://developers.cloudflare.com/dns/manage-dns-records/how-to/create-dns-records/) · [HTTPS automático en Caddy](https://caddyserver.com/docs/automatic-https)

## 3. Elegir el punto de partida

**Instalación vacía.** Desde el checkout revisado:

```bash
cd /opt/milenio
sudo bash infra/nube/deploy.sh init taller.autoserviciomilenio.com
sudo bash infra/nube/deploy.sh apply
sudo bash infra/nube/deploy.sh manager gerencia
sudo bash infra/nube/deploy.sh status
sudo bash infra/nube/deploy.sh verify-url
```

El alta inicial de Gerencia pide una contraseña en la consola privada. La URL pública de alta está cerrada incluso con la base vacía. En **Equipo y acceso**, crea cuentas individuales con el rol de Recepción, Técnico, Refacciones o Administración. El acceso web usa contraseña personal y limita intentos repetidos. El segundo factor de los paneles de alojamiento, DNS y respaldos se configura en esos paneles.

Las cookies de esta versión están limitadas al dominio HTTPS exacto del taller. Al actualizar una instalación anterior de nube, el equipo debe iniciar sesión de nuevo. Si se pierde un celular del personal, Gerencia puede desactivar su cuenta desde **Equipo y acceso**. Para recuperarla, cambia la contraseña, vuelve a activar el usuario y emite sólo las credenciales de agente que todavía necesite.

**Taller que ya opera en Windows.** Agenda el cambio fuera de turno. Obtén una copia portable verificada y anota una orden con foto, el número de órdenes y el saldo antes del corte. Acuerda la hora a partir de la que la instalación anterior deja de recibir escrituras. Importa la copia a un destino nuevo mediante el [procedimiento de traslado](TRASLADO.md) antes de abrir la URL al personal. Las sesiones deben renovarse. Mantén el origen disponible para consulta privada y conserva una copia que permita volver atrás.

## 4. Preparar el respaldo y probar el servicio

Sigue la [guía de respaldo y recuperación](backup/README.md). Prepara una cuenta independiente, un bucket B2 privado y una contraseña de restic guardada fuera del VPS. Antes de empezar a capturar datos reales, ejecuta un primer respaldo, restaura a un directorio separado y verifica una foto y el folio de su orden. Activa el timer diario y los avisos de fallo. El respaldo automático del proveedor ayuda ante una falla reciente; el externo permite recuperar el taller si se pierde el servidor o su cuenta.

Para aceptar el servicio en destino:

- Con las PC del taller apagadas, Recepción abre el subdominio desde un teléfono por datos móviles, crea una orden de prueba y adjunta una foto en la etapa de inspección.
- Gerencia inicia sesión desde otro dispositivo y confirma el mismo folio, foto y permisos. Un visitante sin sesión debe llegar al acceso al intentar abrir la foto.
- Reinicia el VPS en la ventana acordada. Verifica la URL, la orden, la foto y el último respaldo completado. Comprueba una vez la recuperación en un destino limpio. Anota revisión del código, fecha, resultado y duración en el expediente **privado** del taller.

## 5. Operación y actualización

La base SQLite y las fotos pertenecen a una sola instalación activa. Caddy expone HTTPS. La aplicación web y los procesos de documentos y analítica usan almacenamiento local persistente y carecen de red propia. La lectura de fotos usa OCR local en español cuando está disponible. El correo comercial y las funciones de IA externa están deshabilitados en este perfil. El CRM de trabajo local conserva cuentas, notas y borradores. Un fallo del VPS interrumpe la operación hasta que se recupere; con un respaldo diario el riesgo ordinario es perder lo capturado después de la última copia exitosa.

Revisa cada día el último respaldo y el espacio libre. Deja sitio para las fotos, su copia temporal de respaldo, las imágenes de aplicación y los registros. Al actualizar, selecciona el commit revisado en la ventana acordada y ejecuta `sudo bash infra/nube/deploy.sh apply`. El instalador comparte un bloqueo con las copias, respalda antes de migrar y conserva la versión anterior si falla ese respaldo. Una migración interrumpida requiere retomar la misma versión o restaurar código y datos compatibles. [Recuperación y ensayo](backup/README.md) · [Pruebas reproducibles y alcance](VERIFICACION.md)
