"""Generate the demo's original, restrained electronic score locally."""
import wave
from pathlib import Path

import numpy as np

RATE = 48000
SECONDS = 40
score = np.zeros(SECONDS * RATE, dtype=np.float64)


def note(start, length, frequency, level, color=0.15, decay=2):
    first = round(start * RATE)
    end = min(len(score), first + round(length * RATE))
    time = np.arange(end - first) / RATE
    envelope = np.minimum(time / .025, 1) * np.minimum((length - time) / .10, 1)
    phase = 2 * np.pi * frequency * time
    tone = np.sin(phase) + color * np.sin(2 * phase) + .07 * np.sin(3 * phase)
    score[first:end] += tone * envelope * np.exp(-time * decay) * level


chords = [(110, 130.813, 164.814), (87.307, 110, 130.813),
          (130.813, 164.814, 195.998), (97.999, 123.471, 146.832)]
for bar in range(20):
    time = 2.0 * bar
    chord = chords[bar % len(chords)]
    for frequency in chord:
        note(time, 1.98, frequency, .034, .16, .32)
    for beat in range(4):
        note(time + .5 * beat, .41, chord[beat % 3] * 2, .05, .22, 4)
        note(time + .5 * beat, .21, 53, .09, .06, 14)
        note(time + .5 * beat + .26, .11, chord[(beat + 1) % 3] * 4, .018, .24, 13)

for mark in (0.5, 5, 12, 19, 27, 34):
    note(mark, .20, 540, .055, .25, 8)
    note(mark + .095, .21, 812, .045, .12, 7)

score[:RATE] *= np.linspace(0, 1, RATE)
score[-RATE:] *= np.linspace(1, 0, RATE)
right = .91 * score + .07 * np.r_[np.zeros(390), score[:-390]]
sound = (np.column_stack([score, right]) * 32767).astype("<i2")
path = Path(__file__).resolve().parent / "hyperframes/assets/pulso-taller.wav"
with wave.open(str(path), "wb") as output:
    output.setparams((2, 2, RATE, 0, "NONE", "not compressed"))
    output.writeframes(sound.tobytes())
