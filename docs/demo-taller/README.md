# El mismo folio · Demo de Taller Milenio

**Versión 1 · 25 de noviembre de 2026 · 40 segundos · 1080p.** [Descargar el MP4](Taller-Milenio-demo-v1.mp4) · [Vista previa](vista-previa.png).

Una orden ficticia muestra cómo buscar el vehículo, continuar el folio abierto, guardar una imagen desde el celular y consultarla en recepción. El video también enseña el reintento y los permisos de agentes. Claude Opus 5.5 propuso el guion visual y el montaje. Codex adaptó la propuesta a los controles de la aplicación, capturó las pantallas, preparó la música y renderizó el video.

| Tiempo | Qué se ve |
| --- | --- |
| 0:00–0:13 | Búsqueda por placa y folio existente |
| 0:13–0:28 | Inspección en un navegador móvil y foto visible en otra sesión |
| 0:28–0:34 | Aviso de envío sin confirmación y reintento desde la misma página |
| 0:34–0:40 | Pantalla de agentes y ejemplos de permisos |

Las pantallas provienen de un taller temporal en la [revisión de aplicación 93e023f](https://github.com/erickinorganico/taller-milenio-operations-analytics/commit/93e023f6ba6642cbc462b2a7228a3be48bfaff29). La muestra de freno es una ilustración. El ensayo adjuntó la imagen mediante el control real en Chromium con pantalla móvil emulada y simuló un corte previo al envío. El alta final dejó un punto visible en ambas sesiones. La aceptación en un teléfono físico y el despliegue en el VPS siguen pendientes. [Guía de puesta en servicio](../../infra/nube/README.md)

## Fuente editable

El [guion de Claude](montaje-claude.md) conserva la propuesta. El [contrato](studio.json) y la [composición de HyperFrames](hyperframes/index.html) muestran cómo se aplicó con los nombres, el folio y las pantallas del ensayo. La composición usa capturas locales, GSAP 3.15.0 y una pista instrumental original generada por `score.py`.

Desde la raíz del repositorio, con Python 3.12, Node.js, FFmpeg y FFprobe instalados:

```powershell
python -m pip install numpy
python docs/demo-taller/score.py
Set-Location docs/demo-taller/hyperframes
npm install --no-save --package-lock=false --prefix .deps gsap@3.15.0
Copy-Item .deps/node_modules/gsap/dist/gsap.min.js assets/gsap.min.js
npx --yes hyperframes@0.9.96 lint
npx --yes hyperframes@0.9.96 render --quality delivery -o demo-render.mp4
ffmpeg -n -i demo-render.mp4 -c:v copy -af "volume=8dB" -c:a aac -b:a 192k -t 40 -movflags +faststart demo-render-master.mp4
```

Las capturas incluidas permiten volver a renderizar. Para recrearlas en una instalación desechable, instala `requirements-web.txt`, Playwright y su Chromium en el mismo entorno Python. Desde la raíz del repo, ejecuta `python docs/demo-taller/capture_demo.py`. El script regenera capturas y conviene ejecutarlo en otro checkout para conservar la versión revisada. `check_timeline.py` comprueba el encuadre y compara accesos al mismo fotograma desde distintos tiempos del editable.

## Evidencia

- [Fotogramas revisados](evidence/fotogramas/contact-sheet.png), [formato del MP4](evidence/ffprobe.json) y [verificación de conservación audiovisual y privacidad](evidence/media-privacy.json).
- [Comparación de fotogramas del editable](evidence/seek.json) y [medición de audio](evidence/audio-ffmpeg.txt). La revisión técnica pasó. El linter del render registró cero errores y ocho avisos de organización de escenas y arte repetido.
- [QA del Taller](evidence/qa-taller.json) confirmó el folio y la leyenda de prueba en 12 muestras. Su ejecución falló al guardar el dictamen. La revisión de Codex comprobó las seis escenas y la decodificación del máster.
