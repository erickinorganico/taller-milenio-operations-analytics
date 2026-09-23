# Taller Milenio · Modelo operativo V4

Abra **[la mesa de trabajo V4](artifacts/operating-model-v4/INICIO.html)**. Permite buscar las filas de las 27 tablas fuente, navegar sus relaciones, reproducir 31 métricas y revisar prioridades con evidencia. Se consulta sin servidor, internet ni instalación de Python.

La entrega incluye seis tablas derivadas, seis procesos, nueve roles de agente, un libro de datos de 36 hojas, un catálogo Excel de métricas y un libro de seguimiento humano. La guía práctica está en [CLIENT-OPERATING-GUIDE.md](docs/CLIENT-OPERATING-GUIDE.md). Los registros públicos son ficticios; las corridas actuales de V4 usan reglas deterministas. Las corridas nativas históricas de V2 se conservan como evidencia de otra base.

## Recorrido conectado

1. **Prioridades:** abrir `WO-003`, leer el bloqueo y su siguiente paso sugerido.
2. **Fuentes:** navegar orden → vehículo/cliente/cotización/reservas y revisar campos exactos.
3. **Métricas:** abrir `M-WIP-WAITING-PARTS`, verificar numerador, denominador, fórmula y SQL.
4. **Agentes:** leer objetivo, herramientas, métricas permitidas, traza y propuesta realmente producida.
5. **Seguimiento:** copiar `Seguimiento.xlsx` fuera del estudio, anotar responsable y evidencia e importar la revisión.

```powershell
.\.venv\Scripts\python.exe -m milenio studio --output artifacts/nuevo-estudio
.\.venv\Scripts\python.exe -m milenio verify-studio --input artifacts/nuevo-estudio
.\.venv\Scripts\python.exe -m milenio studio-review --report artifacts/nuevo-estudio --input private/Seguimiento_revisado.xlsx --reviewer "Nombre del revisor" --output private/revision-nueva
```

El modelo completo admite snapshots sintéticos de 25 CSV más eventos y vínculos explícitos, con corte fijo. La entrada privada de datos reales conserva un contrato mínimo distinto de cuatro fuentes, descrito a continuación. No se inventan flotillas, contratos, grúas ni historial a partir de esas cuatro fuentes.

## Entrada privada y continuidad con cuatro fuentes

| Necesidad | Archivo o recorrido |
|---|---|
| Saber qué revisar hoy | [Informe de la primera semana](examples/client_delivery/semana_01/INICIO.html): caso, motivo, siguiente paso, rol sugerido y evidencia |
| Conciliar saldos y servicios | [Gerencia.xlsx](examples/client_delivery/semana_01/Gerencia.xlsx): siete hojas curadas, filtros, importes MXN y faltantes |
| Acordar responsables y fechas | [Seguimiento.xlsx](examples/client_delivery/semana_01/Seguimiento.xlsx): revisión editable, origen verificable y evidencia de cierre |
| Preparar sus propios datos | [Plantilla vacía](examples/client_data/client_input_blank.xlsx): Config, Instrucciones, Ordenes, Facturas, Pagos e Inventario |
| Revisar la siguiente semana | [Comparación](examples/client_delivery/comparacion/COMPARACION.html): saldos, estados, señales persistentes y cobertura |
| Acordar una entrega profesional | [Playbook](docs/CLIENT-PLAYBOOK.md), [aceptación](docs/CLIENT-ACCEPTANCE.md) y [alcance comercial](docs/OFERTA-CONSULTORIA.md) |

La práctica usa seis órdenes, dos facturas y sus pagos, y dos partes. INV-001 tiene importe $1,500 y pago $500: saldo $1,000. En la segunda semana ficticia aparece otro pago de $400: saldo $600. El cambio se reconcilia; no se presenta como recuperación atribuible a la consultoría.

## Preparar una corrida local

En Windows, ejecute `Setup.ps1` una vez (Python 3.12+). El paquete offline incluye dependencias para Windows 3.12; Python debe estar instalado. Después arrastre el Excel a **Run-Cliente.cmd**: genera una carpeta nueva en `private/clients/` y abre el informe. Con doble clic sin archivo abre la guía.

También puede usar los comandos explícitos:

```powershell
.\.venv\Scripts\python.exe -m milenio client-template --output private/clients/Entrada.xlsx
.\.venv\Scripts\python.exe -m milenio client-analyze --input private/clients/Entrada.xlsx
```

Antes de analizar complete Config: negocio, corte ISO con zona horaria, identificador y modo de datos. Para una copia autorizada del cliente marque `synthetic=false`; su salida queda restringida a `private/`. Se admiten los CSV del [contrato mínimo](docs/CLIENT-DATA-CONTRACT.md).

En Linux use un entorno virtual, `pip install -r requirements.txt` y los mismos comandos con su intérprete. No requiere servicio, base remota ni llamada de modelo.

## Revisión y continuidad

```powershell
.\.venv\Scripts\python.exe -m milenio client-review `
  --input private/clients/corte-01/Seguimiento.xlsx `
  --report private/clients/corte-01 --reviewer "Nombre y rol declarados"
.\.venv\Scripts\python.exe -m milenio client-compare `
  --before private/clients/corte-01 --after private/clients/corte-02 `
  --output private/clients/comparacion-01-02
.\.venv\Scripts\python.exe -m milenio client-verify --input private/clients/corte-01
```

Cada corrida conserva datos normalizados, tablas SQLite, análisis y hashes. El seguimiento y el historial de revisión son mutables y están excluidos explícitamente del recibo inmutable. Una revisión importada es una declaración humana: no acredita identidad ni ejecución. Un registro ausente en el corte siguiente no se considera resuelto. Los errores impiden generar un reporte parcial.

## Estudio profundo y agentes V2

El [dossier V2](artifacts/workbench-v2/DOSSIER.html) conserva 33 tablas físicas, 36 hojas Excel, seis procesos y nueve agentes. Los nueve perfiles completaron dos etapas con la CLI oficial Codex sobre datos sintéticos; los recibos verifican ejecución y evidencia, no eficacia del negocio.

Consulte el [recorrido V2](docs/V2-WALKTHROUGH.md), el [runtime de agentes](docs/AGENT-RUNTIME.md) y las [especificaciones](specs/). `Run-Studio.cmd`, `studio`, `agents`, `agent` y los comandos V1 siguen disponibles. V2 mantiene su contrato completo sintético y fecha fija; V3 tiene contrato separado y corte declarado. No envía datos del cliente a agentes en segundo plano.

## Alcance de esta entrega

Las prioridades ayudan a revisar cartera, taller, conciliación y partes. No calculan utilidad, capacidad disponible ni SLA contractual con datos insuficientes. Los totales no presumen cobertura de todo el negocio ni suman colas superpuestas. Pagos omitidos pueden sobrestimar saldos.

Use alias: no hay anonimización automática. `private/` está excluido de Git y del paquete; no equivale a cifrado ni control de acceso empresarial. Un piloto real requiere una fuente autorizada y acuerdo de acceso/retención. Esta versión se verificó con datos ficticios; la adopción y el impacto real están pendientes.

El producto no contacta, agenda, despacha, compra, emite facturas, mueve dinero ni cambia estados de negocio. Las personas conservan esas decisiones.

Verificación: `python -m milenio verify --output artifacts/client-verification.json`. El [contrato V3](specs/client-delivery.md) y el [recibo de pruebas](artifacts/client-verification.json) describen el alcance comprobado. Repositorio público autorizado, licencia MIT.
