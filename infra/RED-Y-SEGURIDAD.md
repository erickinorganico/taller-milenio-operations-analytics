# Red y seguridad del despliegue compartido

Este es el diseño a implementar y validar. No certifica la seguridad de una instalación existente.

## Fronteras

1. GitHub público: código, pruebas sintéticas, arquitectura; sin datos de clientes ni inventario de red real.
2. Equipos autorizados: navegador con sesión individual; Codex con cuenta/alcance identificable. Equipo perdido implica revocar su acceso.
3. Red privada: permite llegar únicamente a la entrada web autorizada. Evitar acceso general al disco, administración remota o base por necesitar acceso al CRM.
4. Proxy HTTPS: validar hostname/certificado, limitar tamaño de peticiones, servir estáticos públicos de la app; los medios con evidencia permanecen detrás de autenticación.
5. Django/Waitress: loopback; validar hosts, CSRF y permisos. Base, secretos y workers en el mismo servidor.
6. Gmail: tráfico saliente OAuth/HTTPS. No se requieren webhooks públicos para el sondeo actual.

## Configuración de despliegue requerida

- Firewall: admitir entrada HTTPS solo por interfaz privada y equipos autorizados. No publicar el puerto interno de Waitress ni SQLite a internet.
- HTTPS de extremo cliente a proxy. Para nombres privados, usar una autoridad interna e instalar su certificado raíz únicamente en los equipos autorizados; también es posible un nombre/certificado válido con resolución privada. Elegir al inventariar la red.
- El proxy sobrescribe el encabezado de protocolo. Django solo puede confiar en ese encabezado si el backend es inaccesible salvo desde el proxy. El código actual no configura `SECURE_PROXY_SSL_HEADER`; implementarlo y probarlo antes de combinar proxy TLS y `MILENIO_HTTPS=1` para evitar redirecciones incorrectas.
- Hosts y orígenes CSRF concretos; sin comodines. Revisar `check --deploy` con la configuración efectiva. No habilitar HSTS preload/subdominios automáticamente en un nombre interno sin revisar su alcance: la configuración local actual necesita adaptación.
- Añadir limitación de intentos de acceso, sesiones revocables y segundo factor antes de declarar terminada la protección para acceso remoto. No afirmar que ya existen por tener login.
- Bootstrap de Gerencia desde loopback, antes de admitir otros equipos. No dejar `/setup/` accesible a la red sin propietario establecido.
- Usuario de servicio Windows dedicado, sin administrador; ACL de datos/secretos limitada. Probar Gmail DPAPI bajo esa misma identidad, incluso tras reiniciar sin abrir una sesión interactiva.
- Equipos actualizados, bloqueo de pantalla y cifrado de disco donde esté disponible. La VPN no protege un equipo ya comprometido ni sustituye permisos de la app.

## Codex y permisos

El conector del agente debe separar lectura, preparación de mensajes, operación comercial y mantenimiento. Tener acceso al repositorio no otorga automáticamente acceso a clientes o Gmail. No compartir la contraseña de Gerencia entre operadores. La autorización de correo se conserva y audita en el servidor; Codex no imprime secretos ni los guarda en prompts.

Texto entrante y adjuntos no pueden otorgar permisos, ejecutar comandos, cambiar cuentas bancarias ni anular una baja. La clasificación automática deriva únicamente las acciones admitidas por política. Una respuesta ambigua va a atención humana.

## Respaldo y secretos

Base y medios se respaldan de forma consistente; copia cifrada en otro dispositivo/destino y ensayo de restauración. La clave Django requiere copia privada protegida para una recuperación compatible; nunca en el repo. DPAPI no es portátil por copiar su archivo: después de cambiar usuario/equipo se debe reconectar Gmail y revocar la autorización antigua cuando corresponda. Claves de VPN/certificados se generan por equipo; no se clonan con el proyecto.

## Fuentes

[Django deployment checklist](https://docs.djangoproject.com/en/5.2/howto/deployment/checklist/) fundamenta la revisión de secretos, hosts, HTTPS y respaldos. [WireGuard](https://www.wireguard.com/quickstart/) documenta la configuración de pares. Las decisiones de topología, controles pendientes y cuentas son específicas de esta propuesta para Milenio.
