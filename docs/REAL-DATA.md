# Ruta futura hacia exports reales

## Estado

La primera versión procesa fixtures sintéticos. Publicar el repositorio no autoriza datos reales, conexiones, mensajes ni acciones del negocio. Esta guía no activa un piloto.

## Checklist previo

1. Resolver el ledger de `PROCESS.md` mediante entrevistas/observación autorizadas.
2. Definir propósito, fuente autoritativa, minimización, acceso, retención, respaldo y eliminación.
3. Aprobar un extracto pequeño anonimizado/seudonimizado.
4. Fijar diccionario, grain, IDs, estados, zona horaria, centavos MXN y deduplicación.
5. Separar contacto, ubicación, vehículo, seguridad, contrato y dinero.
6. Preparar control totals y rollback antes de materializar.
7. Confirmar que ningún artefacto sensible se publicará.

## Migración por etapas

**Inventario:** registre propietario, sistema, cutoff, actualización, sensibilidad, calidad y consumidores sin copiar datos.

**Mapeo:** lleve cada columna a un contrato o `unmapped/review`. Nunca infiera consentimiento, autorización, seguridad, disponibilidad, pago o efectivo desde blancos/notas.

**Extracto mínimo:** sustituya IDs directos y excluya texto/documentos innecesarios. Registre hash, autorización, ubicación y fecha de eliminación. Información pública de prospectos no autoriza contacto.

**Preview:** valide esquema, referencias, duplicados, fechas, importes, estados, fórmulas y reconciliaciones sin escritura.

**Piloto aislado:** con autorización separada, ejecute en un directorio/base nuevos, sin conectores. Compare conteos y muestras aprobadas con la fuente.

**Aceptación/rollback:** obtenga aceptación por módulo y conserve fuente, mapping, errores, hashes y respaldo. Un control fallido retira artefactos derivados; no se corrigen outputs finales a mano.

## Cambios técnicos requeridos

- configuración real separada y deshabilitada por defecto;
- política de acceso/cifrado y redacción;
- adapters por fuente con pruebas contractuales;
- reloj/cutoff real separado de demo;
- retención/eliminación y backups;
- calidad/drift/volumen/recuperación;
- revisión fiscal, contable y vial competente;
- aprobación explícita para integraciones salientes.

## Principios

Ausencia no significa cero. Cotización, orden, factura, pago y efectivo son independientes. Oportunidad, contrato y servicio cumplido son independientes. Orden de compra no prueba stock. Solicitud/asignación de grúa no prueba seguridad o despacho. Un hash no prueba verdad o causalidad. Una corrida verde no valida el proceso real.

Importar datos reales, contactar personas, publicar información del negocio, conectar fiscal/pagos, comprometer precio/ETA o intervenir en despacho exige autorización nueva.
