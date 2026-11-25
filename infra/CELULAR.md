# Usar el taller desde el celular

## Para el equipo del taller

1. Conéctate al Wi-Fi del taller. Si trabajas desde otra red, usa la conexión privada que te haya configurado Gerencia.
2. En la app de conexión abre el perfil **Taller Milenio** y activa el túnel. Déjalo conectado al cambiar de app.
3. Abre el favorito **Taller Milenio** en Safari o Chrome e inicia sesión con tu usuario habitual. El favorito apunta a [la aplicación en este teléfono](http://127.0.0.1:8770/). Si Gerencia eligió otro puerto local, usa el enlace que te entregó.

Si ves «No se puede acceder» después de bloquear la pantalla o cambiar de red, vuelve a la app de conexión, reconecta el perfil y abre el favorito de nuevo. Si estabas guardando algo, vuelve a abrir la orden y revisa qué quedó registrado antes de repetirlo. Si aparece un cambio de huella del servidor, cierra la conexión y avisa a Gerencia para que compruebe la identidad.

## Para Gerencia · preparar el teléfono una sola vez

Necesitas el servidor instalado con una cuenta de Gerencia, una cuenta del taller para la persona que usará el celular y un cliente SSH móvil con reenvío **local** y conexión **sin shell**. El operador podrá usar el navegador con su cuenta y el perfil guardado.

1. Consulta la IPv4 privada del teléfono en los detalles del Wi-Fi. Reserva esa dirección en la red del taller si es posible. Crea una llave **Ed25519** en el teléfono. Guarda la llave privada en el dispositivo y entrega al administrador del servidor sólo el archivo público `.pub`.
2. En el servidor, abre PowerShell como administrador desde la carpeta de la versión. Si este es el primer dispositivo, sigue [la instalación inicial](INSTALAR.md#4-acceso-de-los-clientes). Para agregarlo a una instalación que ya recibe conexiones, usa este comando. Si los puertos, usuario o carpeta se personalizaron, indica también los valores de esa instalación.

   ```powershell
   $ipCelular = Read-Host 'IPv4 privada del celular'
   $llaveCelular = Read-Host 'Ruta completa del archivo publico .pub'
   .\Setup-RemoteAccess.ps1 -AddClients -AllowedAddresses $ipCelular -ClientPublicKeyFiles $llaveCelular
   ```

3. En el teléfono guarda un perfil llamado **Taller Milenio** con los valores siguientes. Obtén la IP privada del servidor de quien lo administra. Compara la huella **SHA256** mostrada en el teléfono con la que muestra el servidor, por una vía de confianza, antes de aceptar la conexión.

   | Campo del perfil | Valor |
   | --- | --- |
   | Servidor SSH | IP privada del servidor del taller |
   | Puerto SSH | El de la instalación. Por defecto, `2222` |
   | Usuario y llave | `milenio_tunnel` por defecto y la llave creada en este teléfono |
   | Tipo de conexión | Túnel local sin shell ni terminal |
   | Dirección y puerto de escucha en el teléfono | `127.0.0.1` y `8770` |
   | Dirección y puerto de destino vistos desde el servidor | `127.0.0.1` y el puerto web indicado por el servidor, normalmente `8770` |

   **Android.** En un cliente con perfiles y reenvíos, guarda el equipo por SSH con la llave del teléfono, desactiva la sesión de shell y añade el reenvío de tipo *Local*. Confirma que la escucha sea local al dispositivo. [Guía de reenvíos de ConnectBot](https://connectbot.org/guides/port-forwarding/).

   **iPhone.** En un cliente como Blink Shell puedes guardar el host, su usuario, puerto y llave con el alias `milenio`. Para los puertos predeterminados, abre el túnel con `ssh -N -L 127.0.0.1:8770:127.0.0.1:8770 milenio`. Deja la conexión abierta mientras usas Safari. [Perfiles de Blink](https://docs.blink.sh/basics/hosts) · [Túneles de Blink](https://docs.blink.sh/advanced/advanced-ssh).

4. Abre la aplicación en el navegador del teléfono. Guarda la página inicial como favorito **Taller Milenio**. Inicia sesión, abre una orden de prueba autorizada y confirma el mismo folio y estado desde una computadora. Bloquea y desbloquea la pantalla, prueba la reconexión y vuelve a abrir el folio. Registra dispositivo, navegador y resultado en la [aceptación del servidor](ACEPTACION.md).

**Cambio o pérdida del celular.** Gerencia retira la llave y la IP anteriores aplicando `Setup-RemoteAccess.ps1` con la lista completa de dispositivos que conservan acceso. Si se perdió, cambia la contraseña del operador en **Equipo y acceso** para invalidar sus sesiones anteriores. Para el reemplazo, crea una llave individual en el nuevo teléfono.
