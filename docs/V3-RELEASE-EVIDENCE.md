# Evidencia de entrega V3

V3 agrega el recorrido mínimo para un cliente: entrada Excel/CSV, reglas
explicables, informe gerencial, seguimiento humano, comparación de cortes y
acuerdo de entrega. V2 conserva su estudio de procesos y agentes sintéticos.

## Comprobación local

- `python -m milenio verify --output artifacts/client-verification.json`:
  133 pruebas, cero fallas, cero errores; una omitida en Windows por enlaces
  simbólicos. El recibo contiene el manifiesto de fuente y dependencias.
- Recorrido probado: fuente válida → análisis → editar responsable/fecha →
  importar revisión → segundo pago → comparar corte. El saldo del ejemplo
  cambia de $1,000 a $600 y la variación de pagos es $400, sin atribuir impacto.
- Controles negativos: duplicados, referencias inexistentes, importes inválidos,
  fechas futuras, pago de factura anulada, pérdida de precisión, fórmula en
  anotaciones, origen alterado, carpetas públicas en modo cliente, recibo
  inconsistente y archivo inmutable añadido o cambiado.
- Reimportar una revisión antigua es idempotente y no revierte la revisión más
  reciente mostrada en HTML. El historial es local y autodeclarado, no firmado.
- Chrome: navegación desde CLIENTE.html al informe; búsqueda INV-001 devuelve
  un caso. Informe a 390 px: scrollWidth 390. Revisión visual de escritorio y
  móvil. Sólo se observó un 404 del favicon del servidor temporal; sin fallo del
  informe o de su búsqueda.
- Excel instalado abrió en sólo lectura Entrada, Gerencia, Seguimiento y Acuerdo.
  Seguimiento se exportó a PDF y se revisó visualmente: caso/prioridad y cinco
  columnas editables visibles; evidencia de origen preservada en columnas ocultas.

## Artefactos reproducibles

- `scripts/build_client_demo.py --output <nueva-carpeta>` produce ambas entradas
  ficticias, sus informes y la comparación.
- `scripts/build_client_acceptance.py --output <nuevo-archivo.xlsx>` produce el
  acuerdo con campos humanos vacíos y controles Pendiente.
- `client-verify` verifica el recibo inmutable, separado de los tres archivos
  mutables declarados. Los hashes comprueban integridad, no verdad ni autoría.
- `scripts/package_release.py` empaqueta fuentes rastreadas y rechaza ejemplos
  de cliente marcados no sintéticos. `private/` queda fuera de Git y del ZIP.
- `scripts/package_client_kit.py` entrega una copia de lectura con ejemplos,
  plantillas, documentación y estudio V2; generar nuevas corridas usa el paquete
  completo y Python 3.12+.

## Límites de aceptación

La verificación usa datos ficticios, incluso en pruebas de modo privado. No se
ha obtenido un extracto real, entrevistado a responsables, validado adopción ni
medido impacto comercial. El libro de acuerdo no contiene firmas, nombres,
fechas de aceptación ni aprobaciones fabricadas. El cliente debe validar el
alcance y las fuentes de su propio piloto.
