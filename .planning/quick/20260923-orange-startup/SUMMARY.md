# Marca Milenio y acceso persistente

Estado: implementado y verificado localmente, 2026-09-23.

Solicitud: reparar el acceso que no carga y elevar la interfaz con iconos de mecánica; identidad naranja y blanco confirmada por el usuario.

## Entrega

- GPT-6 Sol: shell, acceso y dashboard blancos con naranja de marca, iconos SVG propios de herramientas, elevador, vehículos, refacciones y diagnóstico; foco visible y navegación responsive.
- GPT-6 Luna: integración Windows del launcher con procesos y datos desechables.
- Revisión Sol independiente: contraste y controles; límites detallados en docs/MECHANICAL-UI-REVIEW.md.
- Agente principal: launcher persistente con pythonw, logs locales, identidad de instancia, cierre ordenado y protección de puertos ocupados. Conserva la carpeta de datos; no instala autoarranque de Windows.

## Evidencia

- scripts/verify_web.py: 124 pruebas, cero fallos, errores u omisiones. Recibo local artifacts/v6-orange-startup-verification.json.
- Pruebas cubren salida del shell, servidor todavía activo, reutilización de PID, demo sembrada una sola vez, cierre incluso con HTTP keepalive y conservación de la base.
- Navegador: dashboard a 1280x900 y 320x850, sin desbordamiento global a 320; acceso cargado después de terminar el shell original. Pantalla de acceso naranja/blanco inspeccionada.
- La revisión visual no equivale a aceptación del cliente ni a uso de datos reales. El servicio es local y debe abrirse nuevamente con Abrir-Demo.cmd o Abrir-Taller.cmd tras reiniciar Windows.
