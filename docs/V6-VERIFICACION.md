# Verificación de entrega V6

La verificación de esta versión separa código, instalación, datos y operación observada. El ZIP es un **candidato local de revisión** hasta que se apruebe una entrega concreta; una prueba sintética no demuestra adopción ni impacto con un taller real.

## Pruebas reproducibles

Desde el repositorio de V6, `python scripts/verify_web.py` ejecuta la suite sobre una base de prueba desechable, comprueba Django y migraciones, compara versiones instaladas con `requirements-web.txt` y registra SHA-256 de todas las fuentes que `package_web.py` permite empaquetar. Produce `artifacts/v6-verification.json` y `artifacts/v6-verification.xml`. Un resultado anterior sólo cubre los hashes y pruebas registrados en su propio recibo.

`python scripts/verify_v6_delivery.py` crea otra instancia **MILENIO_MODE=test** en una carpeta temporal. Migra hasta `workshop.0001`, crea registros V5 ficticios, aplica las migraciones V6, comprueba que órdenes, factura y saldo sobreviven, materializa un corte, procesa una ejecución de reglas en cola y respalda/restaura la base. Comprueba que el corte, filas, política, trabajo y saldo vuelven intactos y que las sesiones se purgan. Su recibo es `artifacts/v6-delivery-verification.json`. Usa los comandos normales de respaldo y restauración, con sus comprobaciones de modo, esquema, bloqueo y puerto intactas; nunca apunta a la instancia live o demo del operador.

Con `--package <ZIP>`, el mismo verificador revisa todos los hashes del manifiesto `milenio-web-v6`. Si el ZIP incluye ruedas offline, extrae el archivo en otra carpeta temporal, instala una `.venv` nueva sin índice de red, aplica migraciones y ejecuta el sembrado inicial demo. Comprueba que los 36 registros V6 y el primer corte ya están presentes, y que el actor temporal no puede iniciar sesión. Luego arranca **el servidor extraído** en un puerto local efímero, inicia sesión con un superusuario temporal sólo en esa demo desechable, obtiene `/analytics/` y `/automations/` con HTTP 200, observa un latido y un trabajo de reglas completado, y cierra el servidor por su canal de supervisión. La contraseña temporal no entra al recibo ni al ZIP.

El candidato `dist/Milenio-V6-review-candidate2.zip` es una salida de revisión; su SHA-256 y los resultados exactos corresponden al recibo generado contra ese archivo. Después de cualquier cambio de fuente se debe generar otro candidato y volver a comprobar su hash, instalación y servidor. Los documentos y resultados V5 conservan procedencia histórica y no sustituyen esta comprobación.

## Evidencia técnica local registrada

- `artifacts/v6-verification.json`: versión 6.0; 115 pruebas ejecutadas, 0 fallos, 0 errores y 2 omisiones de pruebas antiguas cuyos puertos demo/live estaban ocupados. Las 113 restantes pasaron. El recibo registra hashes de fuentes; no se traslada a fuentes posteriores.
- `artifacts/v6-delivery-verification.json`: `status=pass` para un candidato extraído de SHA-256 `a0845d2f2a418f863e86d06a0da2a42999849018146c0b92081a4cf916e8fa1f`; 157 archivos del manifiesto comprobados, instalación offline en entorno nuevo, demo inicial de 36 órdenes y un corte, páginas autenticadas analytics/automatizaciones HTTP 200, trabajo de reglas y latido, migración V5→V6, respaldo/restauración y cierre supervisado. Es el **candidato 2 verificado**, no el recibo del ZIP final publicado.
- `artifacts/v6-browser-verification.json`: filtros, comparación, ranking, seis enlaces de tablas, pausa/reanudación, fallo nativo visible, sesión tras reinicio y vista móvil sin desbordamiento (`clientWidth=scrollWidth=375`). El aislamiento entre roles se probó automáticamente; no se ensayó un login manual por cada rol.
- `artifacts/v6-worker-restart.json`: al terminar el servidor, el proceso trabajador hijo no quedó vivo.
- `artifacts/v6-native-verification.json`: trabajo local real #5 completado con los tres revisores y `model_invoked=true` en GPT-6 Luna; 14 propuestas sobre demo sintética. El intento anterior #4 falló por salida rechazada y no se reintentó automáticamente. El CLI emitió eventos de error intermedios antes del `turn.completed`, conservados en el recibo. Este resultado no garantiza disponibilidad o calidad en otra instalación.

La publicación final debe generar un ZIP y recibos con el mismo SHA después del último cambio de fuente/documentación. Hasta entonces, el cierre aquí es **técnico local**, no entrega publicada ni aceptación del taller.

## Qué queda fuera de estas pruebas

La suite sintética y el servidor local no prueban ejecución nativa real con la cuenta Codex de otra instalación, entrega a cliente, calidad de datos de un taller real, aceptación del usuario, eficacia de propuestas ni mejoras financieras. Los comprobantes administrativos no equivalen a facturación fiscal. Los resultados se revisan con las limitaciones de [Analytics V6](V6-ANALYTICS.md) y [Automatizaciones V6](V6-AUTOMATIZACIONES.md).
