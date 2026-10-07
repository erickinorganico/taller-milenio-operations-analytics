# Prospección y respuestas por Gmail

Implementación local del 6 de octubre de 2026 en el CRM existente. No requiere otra plataforma, una API de IA ni suscripciones nuevas. No se enviaron correos durante la implementación. El catálogo de investigación permanece sin cambios.

## Lo que ya hace

Comercial → **Correo · cola y respuestas** reúne empresas del piloto, mensajes pendientes, contenido, fecha de intento, fecha confirmada por Gmail, identificador del mensaje y del hilo, respuestas y asuntos que necesita atender una persona. “Aceptado por Gmail” no significa entrega ni lectura. No hay píxeles de apertura.

- Carga idempotente del catálogo investigado: conserva IDs mediante UUID estable y la ficha completa como evidencia, incluidas redes, WhatsApp y alertas de identidad. La importación no confirma flotillas ni activa envíos.
- Incorporación de hasta 20 empresas revisadas; una secuencia por empresa/buzón. Rechaza buzones compartidos entre fichas hasta conciliar su identidad.
- Máximo 5 primeros contactos y 10 envíos totales por día, contando respuestas automáticas y manuales. Un envío por ciclo de un minuto. Ventana lunes–viernes, 9–16 h, zona Tijuana; permite excluir fechas.
- Primer correo y hasta dos seguimientos, separados por al menos cuatro días laborables desde el envío anterior. El envío pendiente no cuenta como enviado.
- Sincroniza antes de enviar. Reconoce conversación en el mismo hilo, respuestas en otro hilo e intervención manual en Gmail. Antes del primer contacto también consulta los últimos 30 días de correspondencia con ese buzón. No inspecciona contactos ajenos al piloto deliberadamente; Google otorga un permiso de lectura del buzón más amplio que este filtro del programa.
- Cualquier mensaje entrante cancela seguimientos en cola. Una llamada/conversación registrada manualmente en CRM también detiene la secuencia.
- Bajas: bloquea el contacto y su empresa sin mandar confirmación automática. Rebotes: detiene y marca el canal para revisión. Ausencias y mensajes automáticos: pausa y no responde.
- Preguntas sencillas de ubicación u horario: respuesta factual. Interés expresado claramente: pregunta por unidades a gasolina, cantidad y necesidad. Máximo dos respuestas automáticas por conversación; cada una indica que es automática.
- Precios, citas, disponibilidad, urgencias, quejas, condiciones especiales y texto ambiguo: revisión humana. Desde el panel se puede redactar y poner una respuesta revisada en cola. No cotiza ni compromete servicios por su cuenta.
- Respuestas y contenido entrante se muestran como texto escapado; no se ejecutan instrucciones recibidas por email.
- Si un envío queda sin confirmación por interrupción, no lo repite. Busca su Message-ID en Enviados. Mientras no pueda resolverlo, detiene los envíos y muestra la incidencia. La ausencia en una búsqueda no se interpreta como prueba de que no se envió.

Las respuestas automáticas son intencionalmente limitadas a frases claras completas. Un clasificador determinista no entiende cualquier redacción; los casos que no reconoce pasan a revisión y no se pierden.

## Conectar y activar

1. Abrir `Abrir-Comercial.cmd`. Si es la primera instalación, crear el usuario y contraseña de Gerencia en `/setup/`. Esa credencial local es distinta de la cuenta de Google; no se ha inventado una contraseña para el usuario.
2. Entrar a Comercial → Correo. **Cargar catálogo investigado al CRM**, revisar las fichas que se usarán y preparar una tanda pequeña. La carga es segura de repetir: no duplica ni sobrescribe fichas existentes. Las relaciones dudosas del catálogo requieren revisión de identidad.
3. En Google Cloud, habilitar Gmail API, configurar la pantalla de consentimiento OAuth, agregar el Gmail como usuario de prueba si corresponde y crear un cliente de tipo **Aplicación de escritorio**. Descargar su JSON. No pegar contraseña, tokens ni el archivo de credenciales en el chat o en Git.
4. Ejecutar `Conectar-Gmail.cmd`. Seleccionar el JSON, indicar el usuario local de Gerencia y autorizar el Gmail comercial en la ventana de Google. El correo remitente se toma de la cuenta autorizada; firma predeterminada: Equipo Milenio. El JSON no se copia al repositorio. El token de renovación y el secreto del cliente se cifran con Windows DPAPI en la carpeta de datos de la instalación, ligados al usuario de Windows.
5. Revisar los mensajes en la cola y pulsar **Activar flujo preparado**. La conexión por sí sola deja los envíos pausados. Se puede detener todo desde el mismo panel.

El alcance OAuth es `gmail.send` + `gmail.readonly`; no se pide borrar correo ni modificar etiquetas. Google clasifica lectura como alcance restringido. La publicación/verificación de la aplicación depende del uso de la cuenta y del proyecto Google. En un proyecto externo en estado Testing, el token de renovación normalmente expira a los siete días para estos permisos: reconectar o completar la configuración aplicable de Google antes de una operación sostenida. No se promete conexión perpetua ni se eluden controles de Google.

Fuentes oficiales: [OAuth para aplicaciones instaladas](https://developers.google.com/identity/protocols/oauth2/native-app), [permisos Gmail](https://developers.google.com/workspace/gmail/api/auth/scopes), [caducidad de tokens](https://developers.google.com/identity/protocols/oauth2#expiration), [envío MIME](https://developers.google.com/workspace/gmail/api/guides/sending).

## Sitio, video y presentación del correo

El correo se prepara como MIME con una versión de texto y otra HTML: blanco, acento naranja y texto azul. No hace falta copiar HTML a Gmail. En el panel se pueden registrar enlaces HTTPS y confirmar que abren sin iniciar sesión. Se incorporan a mensajes preparados después de guardar la configuración; no se modifican silenciosamente mensajes ya revisados. El video abre en un enlace; no se adjunta un MP4 ni se presupone reproducción dentro del correo.

Con los enlaces vacíos o sin confirmar, la campaña puede funcionar solo con el mensaje, dirección y WhatsApp 664 820 1966. El Site actualmente privado y la locución pendiente del video no impiden probar el flujo básico. No se cambió la audiencia del Site.

## Operación cotidiana y recuperación

El worker se inicia junto al servidor existente de Milenio. La computadora debe estar encendida, conectada y con Milenio abierto; no es un servicio alojado 24/7. Si se cierra, la cola permanece en SQLite y se retoma al abrir. No se recuperan todos los envíos atrasados de golpe: siguen vigentes ventana y topes diarios.

Al empezar el día: revisar última sincronización, incidencias y respuestas pendientes, atender primero las urgencias y después las oportunidades. Los mensajes urgentes aparecen para atención humana, pero el email no es un canal de despacho inmediato; no se confirma disponibilidad de grúa por este flujo. Una respuesta negativa cierra la secuencia. Un mensaje de vacaciones no reactiva automáticamente la campaña al regreso.

Una baja o pausa no cancela un mensaje que Gmail ya haya aceptado. La recepción se comprueba por sondeo, aproximadamente cada minuto; no es instantánea y puede tardar más si falla la red. Los filtros de contacto no son una garantía de identidad del remitente y nunca autorizan cotizaciones, pagos ni cambios de datos sensibles.

No volver a enviar manualmente un mensaje marcado `unknown`. Revisar Enviados y conservar su identificador; el sistema concilia si lo encuentra. Si no se encuentra, requiere investigación antes de liberar nuevos envíos. Los logs guardan tipos de error, no tokens ni cuerpos de respuestas de Google. Si Google revoca permisos, el panel muestra error de sincronización y el envío queda detenido hasta reconectar.

Respaldo: usar el mecanismo existente de SQLite y medios. El token DPAPI no forma parte del respaldo operativo estándar; una restauración en otro usuario/equipo requiere reconectar Gmail. No ejecutar dos copias restauradas con el mismo buzón: cada instalación debe tener una única cola activa. Esta versión es para una instalación local de Milenio.

## Validación y límites de entrega

Las pruebas automáticas usan empresas y Gmail simulados: idempotencia, sincronización, bajas, rebotes, citas/precios sin automatizar, límites, permisos, CSRF, HTML escapado, MIME e interrupciones. El circuito OAuth y la entrega/respuesta real en Gmail requieren la cuenta del usuario y no se declaran probados hasta conectarla. El render en clientes reales Gmail/Outlook también queda para esa prueba con destinatario controlado.

La integración técnica está implementada; la activación comercial conserva pasos operativos: crear Gerencia si aún no existe, revisar las empresas iniciales y activar la tanda. No se importan fuentes como si fueran contactos ya autorizados ni se inventa calificación para saltar esa revisión.
