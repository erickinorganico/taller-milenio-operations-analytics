"""Check frame selection and time-addressable GSAP motion in a clean browser."""
import hashlib
import json
import os
from pathlib import Path
from io import BytesIO

import numpy as np
from PIL import Image
from playwright.sync_api import sync_playwright

HERE = Path(__file__).resolve().parent
OUT = HERE / "evidence"
ENTRY = HERE / "hyperframes/index.html"
TIMES = [0, 7, 15, 23, 30, 36, 39.9]
SEEK = """(time) => {
    const timeline = window.__timelines['taller-demo'];
    timeline.seek(time);
    const bounds = [];
    for (const scene of document.querySelectorAll('.scene')) {
      const start = Number(scene.dataset.start);
      const visible = start <= time && time < start + Number(scene.dataset.duration);
      scene.style.visibility = visible ? 'visible' : 'hidden';
      if (!visible) continue;
      for (const selector of ['.artwork', '.message', 'h1']) {
        const {left, right, top, bottom} = scene.querySelector(selector).getBoundingClientRect();
        bounds.push({selector,left,right,top,bottom});
      }
    }
    return bounds;
}"""


with sync_playwright() as app:
    browser = app.chromium.launch(executable_path=os.environ.get("MILENIO_DEMO_CHROMIUM"))
    page = browser.new_page(viewport={"width": 1920, "height": 1080})
    page.goto(ENTRY.as_uri())
    page.evaluate("document.fonts.ready")
    assert page.evaluate("Array.from(document.images).every(img => img.complete && img.naturalWidth > 0)")
    sequence = {}
    for time in TIMES:
        bounds = page.evaluate(SEEK, time)
        for item in bounds:
            assert 0 <= item["left"] < item["right"] <= 1920, (time, item)
            assert 0 <= item["top"] < item["bottom"] <= 1080, (time, item)
        shot = page.screenshot(path=OUT / f"preview-{time:g}.png")
        sequence[time] = hashlib.sha256(shot).hexdigest()
    direct = {}
    differences = {}
    for time in reversed(TIMES):
        page.reload()
        page.evaluate("document.fonts.ready")
        page.evaluate(SEEK, time)
        shot = page.screenshot()
        direct[time] = hashlib.sha256(shot).hexdigest()
        with Image.open(BytesIO(shot)) as fresh, Image.open(OUT / f"preview-{time:g}.png") as previous:
            diff = np.abs(np.asarray(fresh, dtype=np.int16) - np.asarray(previous, dtype=np.int16))
        differences[time] = {"mean_delta": float(diff.mean()),
                             "pixels_delta_over_16": float((diff.max(axis=2) > 16).mean())}
    browser.close()

sheet = Image.new("RGB", (1440, 812), "#121f1e")
for index, time in enumerate(TIMES[:6]):
    with Image.open(OUT / f"preview-{time:g}.png") as frame:
        sheet.paste(frame.resize((480, 270), Image.Resampling.LANCZOS),
                    ((index % 3) * 480, (index // 3) * 270))
with Image.open(OUT / "preview-39.9.png") as frame:
    sheet.paste(frame.resize((480, 270), Image.Resampling.LANCZOS), (480, 540))
sheet.save(OUT / "preview-sheet.jpg", quality=91)
(OUT / "seek.json").write_text(json.dumps({
    "method": "Sequential timeline seeks versus isolated seeks from a clean DOM with identical clip visibility",
    "times": TIMES, "identical_pngs": sum(sequence[t] == direct[t] for t in TIMES),
    "differences": differences, "sha256": sequence,
}, indent=2) + "\n", encoding="utf-8")
assert all(row["pixels_delta_over_16"] < .003 for row in differences.values()), differences
