# Eficiencia del proyecto V2

## Qué se optimiza

La eficiencia aquí significa que una revisión puede pasar de una pregunta a la evidencia sin reconstruir manualmente el dataset. No se hacen afirmaciones de ahorro de horas, tokens, dinero o personal porque no existe un piloto real que las mida.

## Una sola construcción, varias lecturas

`python -m milenio studio` produce en una corrida atómica:

1. escenario sintético reproducible de 90 días;
2. warehouse SQLite con 27 fuentes físicas;
3. seis marts materializados;
4. CSV de las 33 tablas;
5. análisis, replay y charts;
6. 36 hojas de Excel;
7. mapas generados desde seis procesos JSON;
8. cinco especificaciones y 18 requisitos copiados al paquete;
9. nueve ejecuciones base de agentes `rules`;
10. dossier y recibo con hashes.

La carpeta final del estudio no se sobrescribe. El builder trabaja en staging y no publica un paquete de estudio incompleto, lo que reduce la posibilidad de revisar una entrega mezclada. Los runs de agentes nativos tienen otro contrato: un fallo se conserva como `blocked` con la evidencia disponible y sin recibo de éxito, para que pueda diagnosticarse y no parezca una corrida inexistente.

La suite integrada actual pasa sin fallas ni errores; el conteo exacto queda en el recibo de verificación del mismo estado fuente. Excel COM abrió las 36 hojas, recalculó seis fórmulas con cero errores y confirmó su conciliación con SQL.

## Reutilización de contratos

| Contrato | Productores | Consumidores | Evita |
|---|---|---|---|
| `FIELDS`/`FLOWS` | contratos de dominio | warehouse, validación, procesos, pruebas | nombres y estados divergentes |
| `warehouse.sqlite` | constructor físico | marts, Excel, agentes, SQL humano | copias con lógica distinta |
| procesos JSON | especificación | SVG, dossier, pruebas de grafo | diagramas desalineados del proceso formal |
| métricas permitidas | runtime | agentes `rules` y `native_codex` | SQL arbitrario generado por prompts |
| `requirements.json` | especificación | dossier y tests de trazabilidad | requisitos sin dueño o aceptación |
| `receipt.json` | estudio | revisión/publicación | paquete sin inventario de integridad |

## Separación de trabajo determinista e inferencia

Validaciones, conciliaciones, conteos, hashes, fórmulas, estados y alcance se resuelven con código determinista. La inferencia nativa se reserva para comparar alternativas, formular preguntas y redactar material de revisión cuando el usuario la solicita.

El camino `native_codex` reduce el contexto en dos etapas:

1. el modelo ve casos acotados y selecciona 1–12 lecturas exactas más métricas permitidas;
2. el runtime valida la selección y envía solo esa evidencia a la salida final.

Esta estructura limita datos, evita SQL libre y deja un recibo de qué se seleccionó. No demuestra por sí sola mejor calidad o menor costo; esas propiedades requieren evaluación separada.

Las nueve ejecuciones observadas completaron las dos etapas mediante la CLI oficial `0.155.1` y conservaron 18 eventos `turn.completed`, sin herramientas de acción externa. Esa evidencia confirma el mecanismo. No confirma efectividad: la revisión detectó selección irrelevante en cobranza y una solicitud de conciliación innecesaria; la corrección y el rerun están pendientes.

No existe hoy una decisión repetida de clasificación o ranking, acotada y validada, que convenga sustituir con Laya. Por ello no se ejecutó Laya y no se atribuyen ahorros de inferencia, tokens o costo.

## Instalación y operación

- `Setup.ps1` instala el entorno analítico Python.
- `Setup-Agents.ps1` es opt-in y prepara la CLI oficial Codex fijada en `0.155.1` para la terminal actual.
- El análisis local funciona sin la CLI nativa.
- Los agentes base `rules` funcionan sin inferencia.
- El modo nativo usa la cuenta Codex autenticada del usuario, no una API externa de pago.
- Un fallo nativo queda `blocked`, conserva sus artefactos parciales y carece de recibo de éxito; no se oculta con fallback automático.

Esta separación permite revisar el workbench completo aun cuando la autenticación o la inferencia nativa no estén disponibles.

## Ciclo semanal propuesto

| Momento | Entrada | Acción | Salida revisable |
|---|---|---|---|
| preparar | snapshot aprobado | construir workbench y verificar recibo | paquete versionado |
| analizar | marts y excepciones | identificar WIP, esperas, cartera, SLA e inventario | lista de preguntas con evidencia |
| asistir | perfil de agente elegido | ejecutar `rules` o `native_codex` opt-in | diagnóstico, alternativas y faltantes |
| decidir | paquete y responsables | revisar, rechazar o pedir información | anotación local, sin ejecución externa |
| aprender | resultado real posterior | comparar decisión con evidencia y definición | cambio propuesto a regla, proceso o métrica |

El último paso aún no existe con datos reales. Hasta realizar un piloto gobernado, el aprendizaje mostrado es únicamente sobre escenarios sintéticos.

## Controles que evitan retrabajo y falsas conclusiones

- corte temporal fijo y timestamps previos al corte;
- campos monetarios en centavos y fórmula financiera reconciliada;
- enlaces de journey explícitos en lugar de coincidencia inferida;
- historial ausente marcado `unknown`;
- ordered stock excluido hasta recepción;
- SLA calculado solo con evidencia elegible;
- fórmulas CSV neutralizadas para evitar ejecución al abrir hojas;
- conexión fuente de agentes con SQLite `query_only=ON`; no se presenta como modo `immutable`;
- IDs, campos, versiones y hash de fuente revalidados al completar;
- propuestas siempre con revisión humana y ejecución externa deshabilitada.

## Cómo medir eficiencia en un piloto real

Defina una línea base antes de adoptar el toolkit y mida por ciclo:

- minutos para localizar evidencia de una excepción;
- porcentaje de agenda con referencias verificables;
- reconciliaciones que pasan al primer intento;
- decisiones devueltas por información faltante;
- propuestas aceptadas, rechazadas o modificadas;
- tiempo entre revisión y actualización de la fuente;
- incidentes de alcance, privacidad o acción no autorizada.

Registre también el costo de preparación, corrección y supervisión. Solo esa evidencia permitiría afirmar una mejora. El escenario sintético valida estructura, reproducibilidad y controles; no cuantifica eficiencia real.
