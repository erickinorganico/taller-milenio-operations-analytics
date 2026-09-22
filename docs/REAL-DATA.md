# Copias locales autorizadas del cliente

## Estado

V3 implementa un adaptador separado de Excel/CSV para copias locales autorizadas, con corte explícito, validación y salida privada. El contrato completo V1/V2 sigue siendo sintético. Publicar el repositorio no autoriza a obtener datos reales, conexiones, mensajes ni acciones del negocio. Esta guía no activa un piloto: no se han recibido datos reales del cliente.

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

## Controles implementados y trabajo de adopción

Implementado: contrato mínimo separado, synthetic=false declarado, salida restringida a private/, exclusión de Git/empaquetado, corte explícito, validación de referencias/fechas/importes y comparación entre cortes. No hay conectores, llamadas de modelos ni ejecución de macros. Consulte CLIENT-DATA-CONTRACT.md y CLIENT-PLAYBOOK.md.

El responsable del piloto todavía debe acordar acceso, cifrado si aplica, retención, eliminación, respaldos, cobertura y control totals con la fuente. El adaptador conserva las referencias aportadas: no redacciona automáticamente. No se autoriza una integración saliente ni se certifica operación fiscal, contable o vial.

## Principios

Ausencia no significa cero. Cotización, orden, factura, pago y efectivo son independientes. Oportunidad, contrato y servicio cumplido son independientes. Orden de compra no prueba stock. Solicitud/asignación de grúa no prueba seguridad o despacho. Un hash no prueba verdad o causalidad. Una corrida verde no valida el proceso real.

Importar datos reales, contactar personas, publicar información del negocio, conectar fiscal/pagos, comprometer precio/ETA o intervenir en despacho exige autorización nueva.
