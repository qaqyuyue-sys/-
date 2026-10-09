#!/usr/bin/env python3
"""Build the soundtrack: 120 BPM synth (7 bars + an Am ending bar) + UI sfx from index.html's window.EVENTS, then mix.

  python3 audio/build_audio.py      (run from the project folder)
Writes audio/timeline.json, audio/sfx.wav, audio/music.wav, audio/mix.wav.
"""
import json, pathlib, subprocess, sys, wave

import numpy as np
from scipy.signal import butter, lfilter
from playwright.sync_api import sync_playwright

ROOT = pathlib.Path(__file__).resolve().parent.parent
TOOLS = ROOT.parent.parent / ".claude/skills/xilo-opus-video/scripts/audio_tools.py"
SR, BPM, DUR = 48000, 120, 16.0
BEAT = 60 / BPM
N = int(DUR * SR)


def write(path, sig):
    sig = np.clip(sig, -1, 1)
    with wave.open(str(path), "wb") as w:
        w.setnchannels(1); w.setsampwidth(2); w.setframerate(SR)
        w.writeframes((sig * 32767).astype(np.int16).tobytes())


def read(path):
    with wave.open(str(path)) as w:
        return np.frombuffer(w.readframes(w.getnframes()), np.int16).astype(np.float64) / 32767


def lp(x, hz, order=2): b, a = butter(order, hz / (SR / 2)); return lfilter(b, a, x)
def hp(x, hz, order=2): b, a = butter(order, hz / (SR / 2), "high"); return lfilter(b, a, x)
def env(n, a, d): x = np.arange(n) / SR; return np.minimum(1, x / a) * np.exp(-x / d)
def midi(m): return 440 * 2 ** ((m - 69) / 12)


# ---- 1. sfx timeline straight from the page, so sound lands on the frame of the action ----
with sync_playwright() as p:
    b = p.chromium.launch(); pg = b.new_page()
    pg.goto((ROOT / "index.html").as_uri()); pg.wait_for_function("window.ready === true")
    events = pg.evaluate("window.EVENTS"); b.close()
(ROOT / "audio/timeline.json").write_text(json.dumps({"duration": DUR, "events": sorted(events, key=lambda e: e["t"])}, indent=1))
subprocess.run([sys.executable, str(TOOLS), "sfx", str(ROOT / "audio/timeline.json"), str(ROOT / "audio/sfx.wav")], check=True)

# ---- 2. music: 7 bars of groove, then bar 8 resolves to Am under the logo and rings out ----
L = int((DUR + 2) * SR)
kick, clap, hat, bass, pad = (np.zeros(L) for _ in range(5))
rng = np.random.default_rng(7)

def add(buf, t, s, g=1.0):
    i = int(t * SR); n = min(len(s), L - i); buf[i:i + n] += s[:n] * g

k_n = int(0.4 * SR); kx = np.arange(k_n) / SR
KICK = np.sin(2 * np.pi * np.cumsum(np.geomspace(150, 44, k_n)) / SR) * env(k_n, 0.001, 0.16)
c_n = int(0.25 * SR)
CLAP = hp(lp(rng.standard_normal(c_n), 5000), 900) * (env(c_n, 0.001, 0.05) + 0.5 * np.roll(env(c_n, 0.001, 0.012), int(0.012 * SR)))
h_n = int(0.06 * SR)
HAT = hp(rng.standard_normal(h_n), 7000, 4) * env(h_n, 0.0005, 0.018)

CHORDS = [[57, 60, 64], [53, 57, 60], [48, 52, 55], [55, 59, 62], [57, 60, 64], [53, 57, 60], [55, 59, 62], [57, 60, 64]]  # Am F C G Am F G | Am
for bar in range(8):
    t0 = bar * 4 * BEAT
    ch = CHORDS[bar]
    end = bar == 7                                      # logo bar: one hit, then just the pad
    for beat in range(1 if end else 4):
        add(kick, t0 + beat * BEAT, KICK, 1.0)
        if beat in (1, 3) and not end: add(clap, t0 + beat * BEAT, CLAP, 0.55)
        for e in range(0 if end else 2):
            add(hat, t0 + beat * BEAT + (e + 0.5) * BEAT / 2, HAT, 0.28 if e else 0.18)
    # bass: root on 8ths, octave jump on the "and" of 2 and 4
    root = ch[0] - 24
    for s8 in range(1 if end else 8):
        f = midi(root + (12 if s8 in (3, 7) else 0)); n = int((1.6 if end else 0.24) * SR); x = np.arange(n) / SR
        tone = sum(np.sin(2 * np.pi * f * h * x) / h for h in range(1, 6)) * env(n, 0.004, 0.6 if end else 0.12)
        add(bass, t0 + s8 * BEAT / 2, tone, 0.5)
    # pad: chord with detuned harmonics, slow attack, lasts the bar
    n = int(4 * BEAT * SR); x = np.arange(n) / SR
    shape = np.minimum(1, x / 0.25) * np.minimum(1, (4 * BEAT - x) / 0.3)
    for m in ch:
        for det in (-0.07, 0.07):
            f = midi(m + 12 + det)
            add(pad, t0, sum(np.sin(2 * np.pi * f * h * x) / h ** 1.6 for h in (1, 2, 3)) * shape, 0.09)

music = lp(kick, 2500) * 0.85 + clap * 0.5 + hat * 0.5 + lp(bass, 900) * 0.8 + lp(pad, 2800) * 0.8
# light room: a few short echoes on the pad/clap bus
room = lp(clap * 0.5 + pad * 0.6, 3000)
for d, g in ((0.031, 0.25), (0.067, 0.18), (0.113, 0.12), (0.19, 0.07)):
    music[int(d * SR):] += room[: L - int(d * SR)] * g
music = music[:N]
music *= np.minimum(1, (N - np.arange(N)) / (0.6 * SR))  # ring out over the last 0.6 s
write(ROOT / "audio/music.wav", music / np.abs(music).max() * 0.8)

# ---- 3. mix and normalise ----
sfx = read(ROOT / "audio/sfx.wav")[:N]
sfx = np.pad(sfx, (0, N - len(sfx)))
mix = read(ROOT / "audio/music.wav") * 0.55 + sfx * 0.75
write(ROOT / "audio/mix_raw.wav", mix / np.abs(mix).max() * 0.9)
subprocess.run([sys.executable, str(TOOLS), "normalize", str(ROOT / "audio/mix_raw.wav"), str(ROOT / "audio/mix_norm.wav")], check=True)
# single-pass loudnorm lands ~2 LU short on 14 s; finish with gain + 4x-oversampled limiter (true peak < -1 dBTP)
subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", str(ROOT / "audio/mix_norm.wav"), "-af",
                "volume=3.1dB,aresample=192000,alimiter=limit=0.8:attack=2:release=60:level=false,aresample=48000",
                str(ROOT / "audio/mix.wav")], check=True)
print("audio/mix.wav ready")
