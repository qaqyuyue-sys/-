#!/usr/bin/env python3
"""合成一段原创背景音乐（无版权问题）：五声音阶铺底 + 类古筝拨弦 + 关键镜头低音鼓。

按 src/scenes.json 的时间轴生成，长度与成片一致；鼓点落在第 1 镜、兵马俑、夜景和片尾。
生成后自动写入 storyboard.json / scenes.json 的 "bgm" 字段，旁白出现时 Remotion 会压低音乐。

用法：pip install numpy scipy && python3 scripts/make_bgm.py
（也可用离线 TTS 的环境：.venv-tts/bin/python scripts/make_bgm.py）
改了镜头时长或重新配音后，请重新运行一次。
"""
import json
import subprocess
from pathlib import Path

import numpy as np
from scipy.signal import fftconvolve, lfilter

ROOT = Path(__file__).resolve().parent.parent
SR = 44100
OUT = ROOT / "public" / "audio" / "bgm.mp3"


def midi(n: float) -> float:
    return 440.0 * 2 ** ((n - 69) / 12)


def env(n: int, attack: float, release: float) -> np.ndarray:
    a, r = min(int(attack * SR), n // 2), min(int(release * SR), n // 2)
    e = np.ones(n)
    e[:a] = np.linspace(0, 1, a) ** 2
    e[n - r:] *= np.linspace(1, 0, r) ** 2
    return e


def pad(freqs, dur: float, rng) -> np.ndarray:
    n = int(dur * SR)
    t = np.arange(n) / SR
    out = np.zeros((n, 2))
    for f in freqs:
        for ch in range(2):
            det = 1 + rng.uniform(-0.002, 0.002)  # 左右声道轻微失谐，拉开空间感
            ph = rng.uniform(0, 6.28)
            tone = sum(np.sin(2 * np.pi * f * det * k * t + ph * k) / k ** 1.6 for k in range(1, 5))
            trem = 1 + 0.08 * np.sin(2 * np.pi * 0.15 * t + ph)
            out[:, ch] += tone * trem
    return out * env(n, 1.8, 2.2)[:, None] / len(freqs)


def pluck(f: float, dur: float, rng) -> np.ndarray:
    # Karplus-Strong 弦模型，近似古筝音色
    n, period = int(dur * SR), int(SR / f)
    x = np.zeros(n)
    x[:period] = rng.uniform(-1, 1, period) * np.hanning(period)
    a = np.zeros(period + 2)
    a[0], a[period], a[period + 1] = 1, -0.497, -0.497
    y = lfilter([1], a, x)
    return y * np.exp(-np.arange(n) / SR * 1.6)


def drum(dur: float = 2.5) -> np.ndarray:
    n = int(dur * SR)
    t = np.arange(n) / SR
    f = 42 + 50 * np.exp(-t * 9)
    body = np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t * 2.4)
    hit = np.random.default_rng(7).normal(0, 1, n) * np.exp(-t * 60) * 0.25
    return body + hit


def reverb(x: np.ndarray, seconds: float, rng) -> np.ndarray:
    n = int(seconds * SR)
    decay = np.exp(-np.arange(n) / SR * (6.9 / seconds))
    out = np.zeros((len(x) + n - 1, 2))
    for ch in range(2):
        ir = rng.normal(0, 1, n) * decay
        ir /= np.sqrt(np.sum(ir ** 2))
        out[:, ch] = fftconvolve(x[:, ch], ir)
    return out[: len(x)]


def main() -> None:
    t = json.loads((ROOT / "src" / "scenes.json").read_text(encoding="utf-8"))
    fps, trans = t["fps"], t["transitionSec"]
    starts, s = [], 0.0
    for sc in t["scenes"]:
        starts.append(s)
        s += sc["durationSec"] - trans
    total = s + trans + 1.0
    n = int(total * SR)
    rng = np.random.default_rng(2024)
    mix = np.zeros((n, 2))

    # 和声进行（D 宫五声为主）：D → Bm → G → A，每 4 秒一换，循环
    chords = [[50, 57, 62, 64, 69], [47, 54, 59, 62, 66], [43, 50, 55, 59, 64], [45, 52, 57, 61, 64]]
    step = 4.0
    for i, c0 in enumerate(np.arange(0, total, step)):
        seg = pad([midi(m) for m in chords[i % 4]], min(step + 2.5, total - c0), rng)
        a = int(c0 * SR)
        mix[a:a + len(seg)] += seg[: n - a] * 0.55
    # 持续低音 D
    tt = np.arange(n) / SR
    drone = np.sin(2 * np.pi * midi(38) * tt) * 0.25 * env(n, 3, 4)
    mix += drone[:, None]

    # 拨弦旋律：五声音阶随机游走，8 分音符网格上稀疏出现
    scale = [62, 64, 66, 69, 71, 74, 76, 78, 81]
    idx, beat = 4, 60 / 72 / 2
    for k, bt in enumerate(np.arange(2.0, total - 3, beat)):
        if rng.random() > (0.42 if k % 2 == 0 else 0.18):
            continue
        idx = int(np.clip(idx + rng.choice([-2, -1, 1, 2]), 0, len(scale) - 1))
        note = pluck(midi(scale[idx]), 2.2, rng)
        a = int(bt * SR)
        pan = rng.uniform(0.3, 0.7)
        seg = note[: n - a] * 0.28
        mix[a:a + len(seg), 0] += seg * (1 - pan)
        mix[a:a + len(seg), 1] += seg * pan

    # 低音鼓：第 1 镜、兵马俑（第 5 镜）、夜景（第 10 镜）、片尾
    hits = [0.05, starts[4], starts[9], starts[-1] + t["scenes"][-1]["durationSec"] - 3.2]
    for h in hits:
        d = drum()
        a = int(h * SR)
        seg = d[: n - a] * 0.9
        mix[a:a + len(seg)] += seg[:, None]

    wet = reverb(mix, 3.0, rng)
    out = mix * 0.6 + wet * 0.7
    out *= env(n, 1.5, 3.0)[:, None]
    out /= np.max(np.abs(out)) * 1.05

    wav = OUT.with_suffix(".wav")
    OUT.parent.mkdir(parents=True, exist_ok=True)
    from scipy.io import wavfile
    wavfile.write(wav, SR, out.astype(np.float32))
    subprocess.run(["ffmpeg", "-nostdin", "-loglevel", "error", "-y", "-i", str(wav),
                    "-af", "loudnorm=I=-16:TP=-1.5:LRA=11", "-ar", "44100", "-b:a", "192k", str(OUT)], check=True)
    wav.unlink()

    for p in (ROOT / "scripts" / "storyboard.json", ROOT / "src" / "scenes.json"):
        text = p.read_text(encoding="utf-8")
        text = text.replace('"bgm": null', '"bgm": "audio/bgm.mp3"')
        p.write_text(text, encoding="utf-8")
    print(f"已生成 {OUT.relative_to(ROOT)}（{total:.1f} 秒），并启用背景音乐")


if __name__ == "__main__":
    main()
