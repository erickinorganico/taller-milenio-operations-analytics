# Qué cuesta operar el taller en la nube

Consulta del 24 de noviembre de 2026. Importes publicados en USD. La elección propuesta es **InterServer Linux KVM de un slice y Backblaze B2**, con el dominio que Milenio ya mantiene. El plan inicial permite probar órdenes y OCR con 2 GB de RAM. Medir memoria, espacio y respuesta con el volumen habitual del taller antes de pasar todos los datos. La región, disponibilidad, IPv4 pública, impuestos, plazo y precio de renovación se confirman en el carrito de la cuenta de Milenio antes de pagar.

| Opción | Costo mensual de servidor | Cuándo elegirla |
|---|---:|---|
| VPS que Milenio ya pague | USD 0 adicionales si hay capacidad y respaldo disponible | Primera opción si permite administrar Linux y Docker, tiene disco persistente, al menos 2 GB de RAM y espacio para fotos y una copia temporal. Tener un dominio acredita el nombre. El plan de alojamiento que lo acompaña se comprueba por separado. |
| InterServer Linux KVM, 1 slice | **USD 3.00 mensuales** | 1 CPU, 2 GB de RAM, 40 GB SSD, 2 TB de transferencia, una IP y acceso root. Sin plazo anual, prueba gratuita ni devolución. Los Ángeles es preferible si está disponible en el pedido. Se administra desde Milenio. El flujo de compra permitió seleccionar un slice y pidió iniciar sesión. [Plan Ubuntu](https://www.interserver.net/vps/ubuntu-vps.html) · [Facturación y cancelación](https://www.interserver.net/vps/faq.html) |
| OVHcloud VPS-1 | USD 5.35 sin plazo mínimo | 2 vCores, 4 GB RAM y 40 GB. Incluye respaldo del proveedor. El configurador LATAM mostró el VPS-1 sin disponibilidad. La publicidad desde USD 4.54 corresponde a 12 meses prepagados. [Catálogo oficial en USD](https://ca.api.ovh.com/v1/order/catalog/public/vps?ovhSubsidiary=WE) · [Ficha de OVHcloud](https://www.ovhcloud.com/es/vps/) |
| Hetzner CX23 en Alemania o Finlandia | USD 7.09 con IPv4 | USD 6.49 de servidor más USD 0.60 de IPv4. Medir la carga de fotos desde Tijuana antes de elegir Europa. La tarifa de EE. UU. es distinta. [Precio por región](https://docs.hetzner.com/general/infrastructure-and-availability/price-adjustment/) · [IPv4](https://docs.hetzner.com/cloud/servers/primary-ips/overview/) |
| Amazon Lightsail Linux de 2 GB con IPv4 | USD 12 | 60 GB de disco y 3 TB de transferencia en el plan de referencia. Alternativa si Milenio ya administra AWS o necesita una región más cercana. El plan de USD 7 tiene 1 GB. Habría que medir memoria bajo carga de fotos antes de usarlo. [Tarifas de los planes](https://docs.aws.amazon.com/lightsail/latest/userguide/amazon-lightsail-bundles.html) |
| Oracle Always Free | USD 0 dentro de la cuota | Para demostraciones. La capacidad disponible varía y Oracle puede recuperar instancias ociosas. El taller necesitaría poder recuperar el servicio en otra máquina. [Condiciones de capacidad y recuperación](https://docs.oracle.com/en-us/iaas/Content/FreeTier/freetier_topic-Always_Free_Resources.htm) |

### Total de referencia

Ejemplos con el plan de USD 3 de InterServer y B2 de pago por uso; meses de 30 días, antes de impuestos. B2 publica USD 6.95 por TB, con los primeros 10 GB gratuitos. El cálculo usa los GB medios **del repositorio de respaldos** incluida su historia. [Precios de Backblaze B2](https://www.backblaze.com/cloud-storage/pricing)

| Respaldo medio retenido | B2 aproximado | Servidor y respaldo |
|---:|---:|---:|
| Hasta 10 GB | USD 0.00 | USD 3.00/mes |
| 50 GB | USD 0.28 | USD 3.28/mes |
| 100 GB | USD 0.63 | USD 3.63/mes |

Los escenarios suponen un subdominio del dominio existente, certificado automático, transferencia dentro de las franquicias y administración a cargo del equipo. La renovación del dominio, el tiempo de soporte, los impuestos, las peticiones facturables y la transferencia excedente se presupuestan según la cuenta. La salida estándar de B2 incluye hasta tres veces el almacenamiento medio al mes; el exceso generalmente cuesta USD 0.01/GB. Un límite de gasto demasiado bajo también puede interrumpir respaldos. Configurar avisos en ambas cuentas y revisar la primera factura. [Costos y límites de B2](https://www.backblaze.com/cloud-storage/pricing)

### Por qué un solo servidor

El sistema existente usa SQLite, almacena fotos privadas y ya tiene herramientas que verifican y restauran ambas cosas juntas. Mantener una sola copia activa en disco local evita una segunda factura y reduce el trabajo de migración. Para un solo taller esta es una propuesta inicial. El servidor requiere mantenimiento y un fallo interrumpe el servicio hasta su recuperación. Si aparecen esperas de escritura frecuentes, se necesita operar en varias sedes con alta concurrencia o el tiempo de recuperación resulta inaceptable, conviene evaluar PostgreSQL administrado, almacenamiento de objetos para las fotos y redundancia. [Despliegue Django con PostgreSQL administrado](https://render.com/docs/deploy-django)

### Límite de gasto aprobado por Erick

El 24 de noviembre de 2026 Erick autorizó hasta **USD 7 al mes en total, sin compromiso anual**. Se propone InterServer facturado mes a mes. Las opciones de panel, copias del proveedor y otros complementos se cotizan por separado. La primera compra y las renovaciones, con impuestos y respaldo, deben caber en el límite total. El catálogo público americano de OVHcloud, filial WE y moneda USD, identifica el producto como `vps-2027-model1`. La fila recurrente `mode=default`, `intervalUnit=month`, `commitment=0` marca USD 5.35. La fila `upfront12` marca USD 4.54 y exige 12 meses. [Consultar catálogo](https://ca.api.ovh.com/v1/order/catalog/public/vps?ovhSubsidiary=WE)

Antes del pedido, sumar el total final con impuestos, cargos por alta y opciones. Restar ese total de USD 7 para obtener el margen real de B2. Empezar con la franquicia gratuita y configurar los límites y alertas de almacenamiento y descargas de la cuenta. Supervisar los avisos de capacidad para que alcanzar el límite no deje el taller sin respaldo. Para un mes de 31 días, el límite diario combinado de cargos variables debe caber en el saldo mensual después de impuestos. Ante un total superior al autorizado o un periodo obligatorio, conservar la cotización y suspender el pedido. Revisar uso, versiones históricas y factura mensualmente. [Límites y avisos de B2](https://help.backblaze.com/hc/en-us/articles/217931138-How-to-use-B2-data-caps-alerts)
