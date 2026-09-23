# Registro ejecutable de métricas

`contracts/metric_registry.json` define las 31 métricas `M-*` de
`specs/analytics.md`: ID, fórmula en lenguaje de negocio, grain, unidad,
tablas/campos fuente, procesos, responsable y limitación. La ejecución está en
`milenio.metric_registry.build_metric_registry(database, as_of=None)`. Acepta
una ruta SQLite o una conexión existente; la ruta se abre en modo de solo
lectura y la conexión del llamador se conserva. Las consultas SQL son fijas en
el código. Un agente puede elegir un ID, pero no aportar SQL.

Cada definición conserva el texto original en inglés y agrega seis campos para
la lectura del cliente: `definition_es`, `limitations_es`, `formula_es`,
`population_es`, `null_policy_es` y `decision_use_es`. La fórmula en español
describe el SQL que realmente se ejecuta. En las dos medianas,
`numerator` cuenta casos con duración observable y `denominator` cuenta la
población de cierres/entregas; `value` es la mediana de horas, no el cociente de
esos conteos. En sumas y conteos, el denominador documenta la población fuente
que hizo posible interpretar un cero.

Cada resultado contiene `numerator`, `denominator`, `value`, `status`, `reason`,
`query`, `source_tables`, `source_counts`, `evidence_rows` y `evidence_total`,
además de las definiciones. `evidence_rows` conserva ID, versión disponible y
valores exactos de campos fuente; su muestra se limita a 12 filas entre las
tablas implicadas. `evidence_total` suma filas fuente y `source_counts` muestra
los conteos por tabla. La muestra permite inspección rápida, pero el SQL y la
base sellada son la prueba reproducible completa. No se interpreta una muestra
como la población que cumple el filtro de la métrica.

El único corte soportado por este almacén sintético es `DEMO_NOW`. Una razón
sin denominador es `unknown`, con valor `null`, nunca cero medido. Un conteo de
cero es medido únicamente cuando existe población fuente. Sin vínculos
`journey_links` no se atribuye lead a cotización. Sin historial validado no se
publica ciclo entregado ni tiempo por estado. La métrica semanal de excepciones
queda `unknown` porque este almacén no tiene una tabla versionada de
excepciones; la salida de excepciones de otro pipeline no se mezcla por su
nombre. Las propuestas pendientes se cuentan desde `proposals` y no equivalen
a acciones aprobadas o terminadas.

`M-SERVICE-CYCLE` usa la mediana de órdenes entregadas con eventos completos;
el denominador informa todas las entregadas para mostrar cobertura. `M-TOW-CLOSE-HOURS`
usa solicitud a cierre y no mide respuesta ni llegada. `M-PROCESS-WAIT` suma
intervalos entre eventos consecutivos y el mart separa entidad y estado;
tiempos abiertos sin evento de salida no se inventan. Las cifras financieras
permanecen en centavos MXN y distinguen cotización, factura, pago, saldo,
gasto y flujo de efectivo.

El registro y sus verificaciones prueban comportamiento sobre fixtures
sintéticos. No constituyen métricas observadas de Taller Milenio, metas
acordadas, prueba de adopción ni impacto operativo.

Para añadir una métrica: (1) registrar ID y seis campos de lectura en
`contracts/metric_registry.json` junto con grain, fuentes, campos y procesos;
(2) agregar SQL fijo y modo de cálculo en `milenio/metric_registry.py`;
(3) autorizar el ID en los perfiles de agentes que realmente lo necesiten, sin
aceptar SQL aportado por un agente; (4) añadir una prueba con un caso medido y
uno sin población o evidencia; (5) comprobar que catálogo, informe y libro la
muestren desde el registro, con el mismo estado y limitación. Ningún paso
supone que una nueva fuente sea real o que su propietario haya sido validado.
