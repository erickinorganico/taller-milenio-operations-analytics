# Conexión y límites de IA para fotos

El nuevo panel **Conexión y uso de IA** está en `/capture/ai/`, junto a
Documentos y excepciones. Gerencia configura; Recepción consulta. No solicita
contraseña de ChatGPT, archivos de credenciales o claves API.

## Conectar el equipo lector

1. Inicia sesión con ChatGPT en Codex en el equipo y bajo el usuario que ejecuta
   el lector. El inicio oficial puede abrirse desde `codex login` en su terminal.
2. Pulsa **Verificar sesión** en el panel. Solo ejecuta `codex login status`;
   no envía una foto, no inicia modelos ni activa las lecturas.
3. Gerencia elige modelo/límites y marca **Permitir lectura de fotos con ChatGPT**.
   La imagen saldrá del equipo hacia el modelo al seleccionar ese lector.

El panel rechaza una sesión API o desconocida. Las lecturas usan el ejecutable
existente, `forced_login_method="chatgpt"`, `model_reasoning_effort="low"`,
un turno efímero de solo lectura, herramientas desactivadas y el esquema de datos
existente. No hay cambio automático de proveedor/modelo o reintento pagado.
Se eliminan las variables de API de ese subproceso. Las credenciales se conservan
en el mecanismo de Codex; no se copian a la base o al navegador de Milenio.

Una sesión comprobada no demuestra acceso a cada modelo. El catálogo local y
las fichas oficiales incluyen imagen para **GPT-6 Luna** y **GPT-6.1 Sol**, ambos
con `low`; una lectura completada confirma el acceso de esa solicitud. Comenzar
con Luna y comparar resultados de hojas autorizadas antes de preferir Sol.
No se ejecutaron inferencias reales para acreditar esta nueva integración.

Las cuentas/condiciones del plan existente conservan sus límites. Usar ChatGPT
por Codex no equivale a consumo ilimitado ni acredita costo cero del plan.
No se habilitó facturación por claves API, se compraron créditos o se crearon
cuentas/servicios. El OCR local de Windows sigue siendo el lector por defecto.

Fuentes oficiales: [autenticación](https://learn.chatgpt.com/docs/auth),
[restricción de método de inicio](https://learn.chatgpt.com/docs/config-file/config-reference),
[GPT-6 Luna](https://developers.openai.com/api/docs/models/gpt-6-luna) y
[GPT-6.1 Sol](https://developers.openai.com/api/docs/models/gpt-6.1-sol).
Existe también [Sign in with ChatGPT para apps locales abiertas](https://developers.openai.com/siwc/token-sharing-open-source);
añadir su OAuth propio implicaría otro cliente y consentimiento, por lo que esta
entrega conserva el inicio oficial de Codex ya disponible.

## Qué controlan los límites

La migración `workshop.0007_photo_ai_controls` agrega configuración e historial
dentro de la misma base. La configuración nueva comienza **pausada**: diez intentos
diarios, dos por documento y 25,000 tokens observados por día. Son valores iniciales
editables por Gerencia, no límites del proveedor ni autorización automática.

- Un intento se admite y registra antes del subproceso. El tope diario es
  persistente y cuenta intentos fallidos/reintentos, sin reembolso al reiniciar.
- El límite por documento conserva el historial aunque cambie el modelo o se
  reintente. Duplicar la misma foto conserva la protección de huella existente.
- El día usa la zona configurada del taller, Tijuana por defecto. No borra
  históricos al cambiar el día o los límites.
- Solo se admite una lectura con IA en curso. Cambios de configuración requieren
  versión vigente y se auditan; guardar no interpreta una imagen.
- Los tokens de entrada/salida se registran si el CLI los informa. Una salida
  inválida mantiene el consumo conocido sin aceptar sus datos. Un timeout o
  interrupción sin métricas conserva consumo desconocido, nunca cero supuesto.
- Si hay consumo desconocido/pendiente hoy o el presupuesto observado se alcanza,
  se bloquea la siguiente lectura. **La última lectura puede superar ese
  presupuesto**; no se ofrece un tope exacto de tokens, dinero o crédito por llamada.
- Pausar impide iniciar lecturas nuevas; una iniciada puede terminar. Se comprueba
  de nuevo antes de ejecutar el modelo. Captura manual y OCR local siguen disponibles.
- Restaurar una base pausa las lecturas con IA y conserva los contadores presentes
  en ese respaldo. Gerencia revisa la recuperación antes de habilitar de nuevo;
  el respaldo puede ser anterior a uso consumido posteriormente.

Estos límites cubren exclusivamente lecturas de documentos admitidas por Milenio.
No limitan ChatGPT web, otras apps, llamadas directas al CLI ni los agentes de
análisis del taller. No se presenta su cuenta global como un saldo local. La
ampliación a otros usos queda como trabajo posterior.

## Seguridad, verificación e instalación

Roles y CSRF permanecen vigentes. Las imágenes y datos leídos no son instrucciones
para el sistema: el contrato impide herramientas y toda aplicación sigue la
revisión/vista previa existente. Habilitar IA no autoriza movimientos financieros,
correo, confirmaciones de servicio o escritura automática de registros.

328 pruebas de aplicación sin fallos/errores, con una omitida por catálogo privado.
Veinte pruebas nuevas de controles, una de protocolo Sol low y una de restauración; auth de API
rechazada, cuotas persistentes, consumo desconocido, pausa, roles/versiones y
consulta sin efectos comprobados con ejecución de modelos simulada. Una prueba
preexistente de heartbeat tuvo interferencia de escritura en OneDrive; aislada
pasó y la suite completa se revalidó con temporales fuera de esa sincronización.
Navegador con registros/consumos ficticios y usuario existente; `login status`
confirmó sesión local ChatGPT sin ejecutar una lectura. Acceso efectivo a Sol
o nueva ejecución Luna permanece pendiente del piloto autorizado.

No desplegado en demo 8766 ni central. Los equipos siguen su rol y el procedimiento
de `infra/DESPLIEGUE-Y-RECUPERACION.md`; aplicar migración con respaldo en la
instalación autorizada. La central sigue aplazada. Sin cambios de correo, cuentas
globales de Codex, catálogo comercial, Sheet, Site o producción de contenido.
