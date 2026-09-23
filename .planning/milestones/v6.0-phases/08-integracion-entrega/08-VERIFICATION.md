---
phase: 08-integracion-entrega
status: passed
---

# Verificación de fase 8

| Requisito | Evidencia observada | Resultado |
| --- | --- | --- |
| DEL-05 | `artifacts/v6-delivery-verification.json`: migración V5→V6 con registros/saldo conservados, respaldo/restauración con sesiones purgadas, paquete candidato 2 extraído e instalado offline, páginas autenticadas 200, worker de reglas y cierre supervisado | passed_local |

La suite vigente `artifacts/v6-verification.json` reporta 115 pruebas, 0 fallos, 0 errores, 2 omisiones de pruebas antiguas cuyos puertos estaban ocupados. El recibo de entrega comprueba el servidor extraído y arranque por otro camino. El paquete verificado tiene SHA-256 `a0845d2f2a418f863e86d06a0da2a42999849018146c0b92081a4cf916e8fa1f`; este no es automáticamente el hash del ZIP que se publique. `docs/V6-VERIFICACION.md` explica comandos y fronteras. Aceptación del cliente y publicación final permanecen fuera del cierre técnico local.
