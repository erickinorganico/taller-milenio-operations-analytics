# Demo interna · Taller móvil Milenio — «Folio MIL-0417»

**Duración:** 40.0 s exactos · **Formato:** 1920×1080, 30 fps (1200 frames) · **Idioma:** español mexicano · **Sin narrador**
**Renderer:** HyperFrames (HTML + GSAP → MP4), con capturas reales de la app en entorno de prueba.

---

## Hilo y datos ficticios (iguales en todas las capturas)

| Dato | Valor |
|---|---|
| Folio | **MIL-0417** (abierto, etapa Inspección) |
| Vehículo | Nissan Versa 2017, gris |
| Placa | **BCX-417-D** (ficticia) |
| Cliente | Laura Méndez (ficticia) |
| Técnico asignado | Raúl P. (ficticio) |
| Foto | `prueba-defensa-del.jpg`: defensa delantera rayada, sin personas ni placas reales |
| Nota del agente | «Cliente pidió presupuesto de defensa antes de continuar.» |

---

## Sistema visual fijo (toda la pieza)

- **Fondo:** gris carbón `#16181C` con grano sutil (opacidad 4 %).
- **Distribución:** captura a la izquierda en un panel de **1180×740 px** (x=80, y=170, radio 18 px, sombra suave). Columna de texto a la derecha, de **x=1320 a x=1840**.
- **Frase grande:** 96 px, peso 800, máximo **5 palabras**, en blanco. Una palabra clave puede ir en el color de acento de la marca.
- **Línea de apoyo:** 44 px, peso 500, 70 % blanco, máximo 9 palabras.
- **Lectura en celular:** no uses texto menor de 40 px. Cuando una UI tenga texto pequeño, aplica zoom de cámara sobre la captura (scale ≤ 1.6) en lugar de agregar rótulos.
- **Persistentes, del frame 0 al 1199:**
  - Arriba a la izquierda: chip **«Folio MIL-0417»** (36 px, fondo blanco 10 %).
  - Arriba a la derecha: insignia **«ENTORNO DE PRUEBA»** (32 px, ámbar `#F2B705` sobre negro, con borde). No se anima y nunca queda tapada.
- **Barra de URL:** recórtala o sustitúyela por una barra neutra sin dominio. No debe verse ningún subdominio ni dirección.
- **Cursor/tap:** círculo blanco de 28 px con pulso (scale 1→1.4, opacity 0.6→0, 0.35 s) en cada clic.
- **Transición entre beats:** la frase sale con `y:-30, opacity:0` en 0.25 s; la nueva entra con `y:40→0, opacity:0→1` en 0.4 s, `power3.out`, con un desfase de 0.08 s entre palabras. El panel de captura hace crossfade de 0.3 s. No hay cortes en negro.

**Música:** pista instrumental local de Tijuana con licencia o de la librería del proyecto, con estilo norteño-electrónico (acordeón y bajo sintetizado), a **120 BPM**. Así, cada corte en segundo entero cae en tiempo (1 tiempo = 0.5 s). Mezcla la música a −18 LUFS y los efectos 4–6 dB por encima. La pieza debe entenderse también en silencio.

---

## Beats

### Beat 1 · 0.0–6.0 s (frames 0–179)
- **Frase:** **¿Y la orden de Laura?**
- **Apoyo:** Cliente en mostrador. Placa en mano.
- **Pantalla real a capturar:** Recepción → buscador de vehículos, en dos estados: (a) campo vacío y (b) resultados tras escribir `BCX-417-D`, con la tarjeta de MIL-0417 y su indicador de **folio abierto**.
- **Encuadre:** el panel entra ya con zoom 1.35 sobre el campo de búsqueda. Desde 3.5 s se abre a 1.0 para mostrar la tarjeta de resultado.
- **Entrada:** el **frame 0** ya muestra la frase completa y el cursor parpadeando en el campo vacío. No hay logo ni fade desde negro. De 0.4 a 2.4 s, la placa se escribe carácter por carácter: anima un `<span>` superpuesto sobre la captura (a), 9 caracteres a unos 0.22 s cada uno. A los 2.6 s hace crossfade a la captura (b).
- **Estado de salida:** la tarjeta MIL-0417 queda resaltada con un contorno de acento de 3 px y el botón **Continuar** es visible.
- **Sonido:** música en la primera nota (sin intro). Tecleo suave sincronizado con cada carácter. Un «tick» al aparecer el resultado.

### Beat 2 · 6.0–13.0 s (frames 180–389)
- **Frase:** **Sigue el mismo folio**
- **Apoyo:** ¿Otra visita? Se confirmaexplícitamente.
- **Pantalla real a capturar:** (a) la tarjeta MIL-0417 con el cursor sobre **Continuar**; (b) el folio MIL-0417 abierto en Recepción, con la etapa Inspección visible; (c) el diálogo real de confirmación que aparece al iniciar una **visita distinta** para el mismo vehículo.
- **Encuadre:** captura a 1.0. Para (c), zoom 1.4 centrado en el diálogo.
- **Entrada:** a los 6.4 s, tap sobre **Continuar** y crossfade a (b), que se mantiene hasta 9.5 s. De 9.5 a 10.0 s, el panel (b) se atenúa al 40 % y el diálogo (c) entra encima con `scale:0.92→1, opacity:0→1` en 0.35 s, `back.out(1.4)`. Se mantiene sin clic hasta 12.6 s para que se lea completo.
- **Estado de salida:** se ve el diálogo de confirmación sin pulsar nada; el folio MIL-0417 sigue detrás.
- **Sonido:** «click» seco en el tap. Un golpe grave corto (*thud*) cuando aparece el diálogo, a 10.0 s, en tiempo.

### Beat 3 · 13.0–21.0 s (frames 390–629)
- **Frase:** **La foto, desde el celular**
- **Apoyo:** Inspección: cámara o galería.
- **Pantalla real a capturar (navegador móvil, viewport de unos 390×844, a 2x):** (a) la lista de órdenes asignadas a Raúl P. con MIL-0417; (b) la orden abierta en etapa **Inspección**, con el control de foto (Cámara / Galería) y el campo de notas; (c) la **vista previa** con `prueba-defensa-del.jpg` adjuntada mediante el control real de archivo y una nota escrita; (d) el estado guardado, con la miniatura y la nota conservadas.
- **Encuadre:** el panel de escritorio sale y entra un marco de teléfono genérico (sin marca, 420×860 px, centrado en x=700). La columna de texto se mantiene a la derecha.
- **Entrada:**
  - El marco sube con `y:120→0, opacity:0→1` en 0.45 s, `power3.out`.
  - Secuencia de capturas: (a) de 13.5 a 15.0 s; tap en MIL-0417; (b) de 15.0 a 17.0 s; tap en **Galería**; (c) de 17.0 a 19.5 s, con un zoom del teléfono a 1.25 sobre la vista previa; tap en **Guardar**; (d) de 19.5 a 21.0 s.
  - Cada cambio de captura es un *slide* horizontal de 0.3 s.
- **Estado de salida:** la orden guardada muestra la miniatura de la foto, la nota y un check de guardado.
- **Sonido:** un «tap» suave en cada toque. Obturador leve al aparecer la vista previa. Confirmación ascendente de dos notas al guardar, a 19.5 s.

### Beat 4 · 21.0–28.0 s (frames 630–839)
- **Frase:** **Recepción ya la ve**
- **Apoyo:** Se actualiza sola, o con Actualizar.
- **Pantalla real a capturar (otro equipo u otra sesión de escritorio):** (a) el folio MIL-0417 **sin** la foto todavía, con el botón **Actualizar** visible; (b) el mismo folio después de tocar Actualizar, con la foto y la nota del técnico.
- **Encuadre:** el teléfono se desliza a la izquierda y reduce su escala a 0.55, quedando como referencia en la esquina inferior izquierda (x≈260). El panel de escritorio entra a la derecha del teléfono a escala 0.9.
- **Entrada:**
  - Una línea punteada de acento se traza del teléfono al panel con `strokeDashoffset` en 0.5 s, de 21.4 a 21.9 s.
  - A 23.5 s, tap en **Actualizar** y crossfade a (b).
  - De 24.0 a 26.0 s, zoom 1.3 sobre la foto recién visible.
- **Estado de salida:** la foto de la defensa se ve en el folio de escritorio. El teléfono sigue visible pero pequeño.
- **Sonido:** *whoosh* corto con la línea. «Click» en Actualizar. Un *ding* brillante cuando aparece la foto, a 24.0 s.
- **Nota para Codex:** no muestres un contador de segundos. La línea de apoyo basta y evita prometer una latencia exacta.

### Beat 5 · 28.0–34.0 s (frames 840–1019)
- **Frase:** **¿Se cortó? Reintenta**
- **Apoyo:** Desde la misma página. Un solo registro.
- **Pantalla real a capturar:** (a) el error real que aparece tras una interrupción de red, con la opción de **Reintentar** en la página abierta; (b) el resultado exitoso después de reintentar; (c) la lista o el historial del folio con **una sola** entrada de la foto o el punto, sin duplicados.
- **Encuadre:** el teléfono vuelve al centro a escala 1.0 si el error se capturó en móvil; si no, usa el panel de escritorio. Haz zoom 1.4 sobre el mensaje de error.
- **Entrada:**
  - Un icono de señal cortada parpadea dos veces junto al mensaje durante 0.3 s.
  - A 30.5 s, tap en **Reintentar** y transición a (b).
  - A 32.0 s, crossfade a (c). Sobre la entrada única aparece un contorno de acento y una etiqueta superpuesta **«1»** de 48 px.
- **Estado de salida:** la lista muestra una sola entrada, resaltada.
- **Sonido:** *glitch* breve y seco con el error. La música baja 6 dB durante 0.5 s y vuelve al reintentar. Confirmación de dos notas en (b).
- **Restricción:** ningún texto debe sugerir modo sin conexión ni que las fotos se suben solas cuando vuelve internet.

### Beat 6 · 34.0–40.0 s (frames 1020–1199)
- **Frase:** **Agentes con permiso acotado**
- **Apoyo:** Notas internas en folios delimitados. No deciden.
- **Pantalla real a capturar:** el folio MIL-0417 con la **nota interna ya guardada** por el agente autorizado: el texto de la nota, su autor marcado como agente y la marca de tiempo. Alternativa: la pantalla real de permisos de agentes. No muestres conteos para evitar cifras.
- **Encuadre:** panel de escritorio a 1.0. De 34.5 a 36.5 s, zoom 1.35 sobre la nota.
- **Entrada:**
  - La nota se resalta con un barrido de acento de izquierda a derecha en 0.6 s.
  - A 37.0 s, el zoom vuelve a 1.0 y el panel se reduce a 0.85.
  - De 37.5 a 38.0 s, entra un pie de cierre bajo la frase: el logo de Autoservicio Milenio pequeño (altura 64 px) y el texto **«Taller móvil · Entorno de prueba»** (40 px).
- **Estado de salida (frame 1199):** se ven el folio con la nota, la frase, el logo pequeño, el chip del folio y la insignia **ENTORNO DE PRUEBA**. No hay fundido a negro ni logo a pantalla completa.
- **Sonido:** *ding* suave en el resaltado de la nota. La música resuelve con un acorde final a 38.0 s y el *decay* termina natural hacia 40.0 s, sin corte abrupto.

---

## Lista de capturas para Codex

1. Recepción: buscador vacío.
2. Recepción: resultados de `BCX-417-D` con MIL-0417 y su indicador de folio abierto.
3. Recepción: MIL-0417 abierto en etapa Inspección.
4. Diálogo de confirmación de visita distinta.
5. Móvil: lista de órdenes asignadas a Raúl P.
6. Móvil: MIL-0417 en Inspección, con el control Cámara / Galería.
7. Móvil: vista previa con `prueba-defensa-del.jpg` y la nota escrita.
8. Móvil: estado guardado con la miniatura y la nota.
9. Equipo distinto: MIL-0417 sin la foto, con el botón Actualizar visible.
10. Equipo distinto: MIL-0417 con la foto y la nota.
11. Error tras la interrupción de red, con la opción Reintentar.
12. Resultado exitoso después de reintentar.
13. Lista o historial con una sola entrada.
14. Nota interna del agente guardada en MIL-0417, o la pantalla de permisos.

**Formato de captura:** PNG a 2x. Barra de URL recortada o neutralizada. Sin datos reales ni dominio visible. El indicador de entorno de prueba de la app, si existe, puede quedar visible además de la insignia superpuesta.

## Verificación antes de entregar el render

- La duración es exactamente de 1200 frames a 30 fps.
- La insignia **ENTORNO DE PRUEBA** es visible en todos los frames.
- El frame 0 muestra la frase, la UI de búsqueda y el cursor, sin logo.
- Ningún texto es menor de 40 px después del escalado final.
- Revisa la legibilidad en una reproducción de unos 390 px de ancho.
- No aparecen cifras de negocio, subdominios ni promesas de funcionamiento sin conexión.
- Escucha la pieza completa para confirmar que los efectos caen en tiempo y que la música no tapa los *dings* de confirmación.
