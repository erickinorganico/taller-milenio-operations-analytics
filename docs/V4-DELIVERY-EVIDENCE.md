# Evidencia de entrega V4

Entrada: `artifacts/operating-model-v4/INICIO.html`. Los datos del estudio son sintéticos y tienen corte `2026-09-21T18:00:00Z`.

| Superficie | Resultado comprobado |
|---|---|
| Fuentes | 27 tablas, 2,902 filas; seis marts adicionales. Catálogo con filas completas, claves, relaciones, nulos y consumidores de métricas. |
| Métricas | 31 IDs del alcance, definiciones en español, SQL, numerador/población, estado y muestras de fuente. La falta de evidencia conserva `unknown`. |
| Operación | 61 señales OPS de revisión sobre la población de fuentes; importes sólo donde existe saldo de factura vinculado. |
| Agentes | Nueve roles y nueve propuestas AGT correspondientes a borradores realmente emitidos. Las nueve corridas actuales son `rules`, sin inferencia de modelo. |
| Procesos | Seis definiciones, mapas SVG, roles, controles y evidencia requerida. Son hipótesis pendientes de validación con el taller. |
| Seguimiento | 70 filas de revisión inicial pendientes. Copia editable externa; importación verifica origen y conserva el estudio sellado. |
| Libros | Datos y análisis en 36 hojas; catálogo adicional de métricas/fuentes/campos; libro de seguimiento humano. |
| Instalación | Paquete de código extraído en carpeta nueva; entorno Python 3.12 nuevo; instalación de las 14 dependencias fijadas desde wheels locales, sin descargas. |
| Pruebas del código extraído | 162 ejecutadas, cero fallos, cero errores; dos pruebas de enlaces simbólicos omitidas por restricciones de Windows. |
| Navegación sin navegador | 191 comprobaciones de rutas/controladores, búsqueda, paginación y vínculos; 814 rutas internas y 87 archivos locales verificados. |
| Paquete ZIP | Manifiesto validado contra cada miembro extraído; `verify_studio` pasa sobre `studio/` y la copia del estudio dentro de `source/`. |

El recibo del estudio verifica 156 archivos y el hash de contenido
`bb627a72e44d03339a898ae75859d6bd4c9ce368a91a15dd9e2d4bfc014d5e78`.
Los hashes de los ZIP se entregan en `dist/SHA256SUMS-v4.0.0.txt`.
La evidencia de las pruebas se conserva en `artifacts/v4-verification.json` y `.xml`.

## Correcciones verificadas durante esta entrega

- Una recomendación de agente no se multiplica por cada registro citado. Los borradores sin atribución explícita permanecen como propuestas de corrida.
- La carga de un resultado guardado vuelve a comprobar campo, valor y versión contra SQLite; evidencia inventada bloquea su incorporación.
- Métricas, prioridades y agentes usan el hash del archivo SQLite. El hash lógico de filas queda identificado por separado.
- Sin historial validado no se publica tiempo de ciclo; la antigüedad de órdenes abiertas es otra medida.
- Los tiempos por estado distinguen tipo de entidad. Los IDs de instancia del historial no enlazan a definiciones de proceso equivocadas.
- Los seis marts existen con tipos estables incluso cuando no tienen filas.
- Los archivos auxiliares del ZIP quedan fuera de la carpeta sellada para conservar verificable su recibo original.

## Límites de la evidencia

La política del navegador bloqueó la apertura del archivo local. La comprobación de interfaz fue de lógica/rutas en Node, sin navegador: no acredita apariencia, viewport móvil ni accesibilidad visual.

La publicación remota quedó bloqueada porque la revisión automática de aprobación no pudo completarse por límite de uso. V4 es una entrega local; no se afirma commit, CI remoto o release publicado de esta versión. Las pruebas anteriores de CI pertenecen a V3.

No se ejecutaron nuevas corridas nativas sobre la base V4. Las corridas nativas históricas de V2 pertenecen a otra identidad de fuente. La importación privada real sigue limitada al contrato separado de órdenes, facturas, pagos e inventario; no hay datos reales, piloto ni aceptación del cliente en este estudio.
