"""Code-synthesised score (numpy), laid out on the same timeline as the edit.

D major, 72 BPM, I–vi–IV–V. Layers enter by section so the music grows with
the story: intro drone + bells → piano arpeggio + pads → bass and soft pulse →
full chords, low drums and swells → sustained final chord.
"""
import wave
from pathlib import Path

import numpy as np

SR = 48000
BPM = 72
BEAT = 60 / BPM
BAR = 4 * BEAT
D3 = 146.83
CHORDS = [  # semitone offsets from D3: (root, third, fifth)
    (0, 4, 7),      # D
    (-3, 0, 4),     # Bm  (B2 D3 F#3)
    (-7, -3, 0),    # G   (G2 B2 D3)
    (-5, -1, 2),    # A   (A2 C#3 E3)
]


def hz(semi, base=D3):
    return base * 2 ** (semi / 12)


def env(n, a, r, sustain=1.0):
    e = np.full(n, sustain, np.float32)
    na, nr = int(a * SR), int(r * SR)
    if na:
        e[:na] = np.linspace(0, sustain, na)
    if nr:
        e[-nr:] *= np.linspace(1, 0, nr)
    return e


def osc(f, n, harmonics, detune=0.0, phase=0.0):
    t = np.arange(n) / SR
    out = np.zeros(n, np.float32)
    for k, amp in harmonics:
        out += amp * np.sin(2 * np.pi * f * k * (1 + detune) * t + phase * k)
    return out


def place(buf, sig, t0, gain=1.0, pan=0.0):
    i = int(t0 * SR)
    if i >= buf.shape[0]:
        return
    sig = sig[: buf.shape[0] - i]
    l, r = np.cos((pan + 1) * np.pi / 4), np.sin((pan + 1) * np.pi / 4)
    buf[i:i + len(sig), 0] += sig * gain * l
    buf[i:i + len(sig), 1] += sig * gain * r


PAD_H = [(1, 1), (2, .5), (3, .33), (4, .22), (5, .14), (6, .09), (7, .05), (8, .03)]
PIANO_H = [(1, 1), (2, .45), (3, .22), (4, .12), (5, .06)]
BELL_H = [(1, 1), (2.76, .45), (5.4, .2), (8.9, .08)]


def pad(f, dur, gain):
    n = int(dur * SR)
    s = sum(osc(f, n, PAD_H, d) for d in (-0.004, 0, 0.004)) / 3
    return s * env(n, min(1.4, dur * 0.4), min(1.6, dur * 0.4)) * gain


def pluck(f, dur=1.6):
    n = int(dur * SR)
    t = np.arange(n) / SR
    s = osc(f, n, PIANO_H) * np.exp(-t * 3.2) * env(n, 0.004, 0.2)
    return s


def bell(f, dur=3.0):
    n = int(dur * SR)
    t = np.arange(n) / SR
    return osc(f, n, BELL_H) * np.exp(-t * 1.6) * env(n, 0.002, 0.3)


def kick(dur=0.6, f0=110, f1=42):
    n = int(dur * SR)
    t = np.arange(n) / SR
    f = f1 + (f0 - f1) * np.exp(-t * 18)
    return np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t * 6)


def boom(dur=3.5):
    n = int(dur * SR)
    t = np.arange(n) / SR
    rng = np.random.default_rng(7)
    low = np.sin(2 * np.pi * np.cumsum(30 + 60 * np.exp(-t * 4)) / SR) * np.exp(-t * 1.3)
    noise = np.convolve(rng.standard_normal(n), np.ones(60) / 60, "same") * np.exp(-t * 3) * 0.5
    return (low + noise) * env(n, 0.01, 0.8)


def swell(dur):
    n = int(dur * SR)
    t = np.arange(n) / SR
    rng = np.random.default_rng(3)
    w = rng.standard_normal(n)
    out = np.zeros(n, np.float32)
    cut = np.linspace(0.02, 0.35, n)
    acc = 0.0
    for i in range(n):
        acc += cut[i] * (w[i] - acc)
        out[i] = acc
    return out * (t / dur) ** 2.2 * 0.6


def reverb(buf, seconds=2.6, mix=0.28):
    rng = np.random.default_rng(11)
    n = int(seconds * SR)
    t = np.arange(n) / SR
    out = np.empty_like(buf)
    for c in range(2):
        ir = rng.standard_normal(n) * np.exp(-t * 6.9 / seconds)
        ir[: int(0.012 * SR)] = 0
        ir /= np.sqrt((ir ** 2).sum())
        L = buf.shape[0] + n
        N = 1 << (L - 1).bit_length()
        wet = np.fft.irfft(np.fft.rfft(buf[:, c], N) * np.fft.rfft(ir, N), N)[: buf.shape[0]]
        out[:, c] = buf[:, c] * (1 - mix) + wet * mix * 1.4
    return out


def compose(total, sections, out_path):
    """sections: dict with times of intro_end, build, climax, outro."""
    n = int((total + 3) * SR)
    buf = np.zeros((n, 2), np.float32)
    s_a, s_b, s_c, s_o = sections["a"], sections["b"], sections["c"], sections["outro"]
    bars = int(np.ceil(total / BAR)) + 1

    # drone + bells in the intro
    place(buf, pad(hz(-12), s_a + 1.5, 0.22), 0)
    place(buf, pad(hz(7, D3), s_a + 1.5, 0.10), 0, pan=0.3)
    for i, (t, semi) in enumerate([(0.6, 24), (1.8, 19), (2.9, 28), (3.8, 26)]):
        place(buf, bell(hz(semi)), t, 0.16, pan=(-0.4, 0.4)[i % 2])
    place(buf, boom(), 0.55, 0.55)

    for b in range(bars):
        t = s_a + b * BAR
        if t >= total:
            break
        ch = CHORDS[b % 4]
        final = t >= s_o
        if final:
            ch = CHORDS[0]
        lvl = 0.10 if t < s_b else (0.13 if t < s_c else 0.17)
        for i, semi in enumerate(ch):
            place(buf, pad(hz(semi + 12), BAR + 1.0, lvl), t, pan=(-0.5, 0, 0.5)[i])
        if t >= s_c and not final:
            for i, semi in enumerate(ch):
                place(buf, pad(hz(semi + 24), BAR + 0.8, 0.06), t, pan=(0.6, -0.6, 0)[i])
        # piano arpeggio, 8th notes
        if not final:
            pattern = [0, 2, 1, 2, 0 + 12, 2, 1, 2] if t < s_c else [0, 1, 2, 12, 14, 12, 2, 1]
            for k, idx in enumerate(pattern):
                semi = ch[idx % 3] + (12 if idx >= 12 else 0) + 12
                place(buf, pluck(hz(semi)), t + k * BEAT / 2, 0.12 if t < s_b else 0.15,
                      pan=0.25 * np.sin(k))
        # bass from the build
        if t >= s_b:
            for half in range(2):
                bt = t + half * 2 * BEAT
                nb = int(2 * BEAT * SR)
                place(buf, osc(hz(ch[0] - 12), nb, [(1, 1), (2, .3)]) * env(nb, 0.05, 0.3), bt, 0.22)
        # pulse: kick on 1 & 3 from the build, every beat in the climax
        if s_b <= t < s_o:
            for beat in range(4):
                if t < s_c and beat % 2:
                    continue
                place(buf, kick(), t + beat * BEAT, 0.35 if t < s_c else 0.45)

    place(buf, swell(2.2), s_c - 2.2, 0.35)
    place(buf, boom(), s_c, 0.45)
    place(buf, swell(2.0), s_o - 2.0, 0.4)
    place(buf, boom(4.5), s_o, 0.6)
    for i, semi in enumerate([24, 31, 36]):
        place(buf, bell(hz(semi), 4.0), s_o + 0.2 + i * 0.6, 0.12, pan=(-0.3, 0.3, 0)[i])
    place(buf, pad(hz(-12), total - s_o + 2, 0.2), s_o)

    buf = reverb(buf)
    buf = buf[: int(total * SR)]
    fade = int(2.5 * SR)
    buf[-fade:] *= np.linspace(1, 0, fade)[:, None]
    buf /= np.abs(buf).max() / 0.8
    pcm = (buf * 32767).astype("<i2")
    Path(out_path).parent.mkdir(parents=True, exist_ok=True)
    with wave.open(str(out_path), "wb") as w:
        w.setnchannels(2)
        w.setsampwidth(2)
        w.setframerate(SR)
        w.writeframes(pcm.tobytes())
    return out_path


def for_timeline(tl, out_path):
    """Map story beats to music sections: lines 1–4 calm, 5–7 build, 8–9 climax."""
    starts = [v.start for v in tl.voices]
    return compose(tl.duration, {
        "a": starts[0] - 0.35,
        "b": starts[4] - 0.35,
        "c": starts[7] - 0.35,
        "outro": starts[9] - 0.35,
    }, out_path)
