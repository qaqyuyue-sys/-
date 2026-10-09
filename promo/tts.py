"""Narration TTS: MiniMax (primary) with a local Kokoro fallback.

One request per narration line.

Each line is synthesised separately and trimmed of leading/trailing silence,
so its exact duration is known and the on-screen card can be timed to it.

Env:
  MINIMAX_API_KEY   required
  MINIMAX_API_HOST  default https://api.minimaxi.com (国内); 海外账号用 https://api.minimax.io
  MINIMAX_GROUP_ID  optional, appended as ?GroupId= for older accounts
  TTS_ENGINE        auto (default: MiniMax, fall back to Kokoro) | minimax | kokoro

Kokoro v1.1-zh runs offline through sherpa-onnx; `python make.py models`
downloads it from GitHub releases into models/.
"""
import hashlib
import json
import urllib.error
import urllib.request
import wave
from pathlib import Path

from .common import ROOT, duration, env, log, run

KOKORO_DIR = ROOT / "models" / "kokoro-multi-lang-v1_1"

SILENCE_TRIM = (
    "silenceremove=start_periods=1:start_threshold=-50dB:start_silence=0.03,"
    "areverse,"
    "silenceremove=start_periods=1:start_threshold=-50dB:start_silence=0.05,"
    "areverse"
)


def _cache_key(text, cfg):
    blob = json.dumps({"text": text, **cfg}, ensure_ascii=False, sort_keys=True)
    return hashlib.sha1(blob.encode("utf-8")).hexdigest()[:12]


def minimax_request(text, cfg):
    key = env("MINIMAX_API_KEY")
    if not key:
        raise SystemExit("缺少 MINIMAX_API_KEY 环境变量（MiniMax 开放平台 → 接口密钥）")
    host = env("MINIMAX_API_HOST", "https://api.minimaxi.com").rstrip("/")
    url = f"{host}/v1/t2a_v2"
    if env("MINIMAX_GROUP_ID"):
        url += f"?GroupId={env('MINIMAX_GROUP_ID')}"
    voice = {
        "voice_id": cfg["voice_id"],
        "speed": cfg.get("speed", 1.0),
        "vol": cfg.get("vol", 1.0),
        "pitch": cfg.get("pitch", 0),
    }
    if cfg.get("emotion"):
        voice["emotion"] = cfg["emotion"]
    body = {
        "model": cfg.get("model", "speech-02-hd"),
        "text": text,
        "stream": False,
        "voice_setting": voice,
        "audio_setting": {
            "sample_rate": cfg.get("sample_rate", 32000),
            "bitrate": cfg.get("bitrate", 128000),
            "format": "mp3",
            "channel": 1,
        },
        "output_format": "hex",
    }
    req = urllib.request.Request(
        url, data=json.dumps(body, ensure_ascii=False).encode("utf-8"),
        headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=120) as resp:
        data = json.loads(resp.read().decode("utf-8"))
    status = (data.get("base_resp") or {}).get("status_code", -1)
    if status != 0:
        raise RuntimeError(f"MiniMax 返回错误: {data.get('base_resp')}")
    return bytes.fromhex(data["data"]["audio"])


_kokoro = None


def kokoro_request(text, cfg, out_wav):
    global _kokoro
    import sherpa_onnx
    if _kokoro is None:
        m = KOKORO_DIR
        if not (m / "model.onnx").exists():
            raise SystemExit("缺少 Kokoro 模型，先运行 python make.py models")
        _kokoro = sherpa_onnx.OfflineTts(sherpa_onnx.OfflineTtsConfig(
            model=sherpa_onnx.OfflineTtsModelConfig(
                kokoro=sherpa_onnx.OfflineTtsKokoroModelConfig(
                    model=str(m / "model.onnx"), voices=str(m / "voices.bin"),
                    tokens=str(m / "tokens.txt"), data_dir=str(m / "espeak-ng-data"),
                    dict_dir=str(m / "dict"),
                    lexicon=f"{m / 'lexicon-us-en.txt'},{m / 'lexicon-zh.txt'}"),
                num_threads=4),
            rule_fsts=f"{m / 'date-zh.fst'},{m / 'phone-zh.fst'},{m / 'number-zh.fst'}",
            max_num_sentences=1))
    k = cfg.get("kokoro", {})
    audio = _kokoro.generate(text, sid=k.get("speaker", 62), speed=k.get("speed", 0.92))
    import numpy as np
    pcm = (np.clip(np.array(audio.samples), -1, 1) * 32767).astype("<i2")
    with wave.open(str(out_wav), "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(audio.sample_rate)
        w.writeframes(pcm.tobytes())


def pick_engine(mock):
    if mock:
        return "mock"
    choice = env("TTS_ENGINE", "auto")
    if choice != "auto":
        return choice
    if not env("MINIMAX_API_KEY"):
        log("未设置 MINIMAX_API_KEY，改用本地 Kokoro 配音")
        return "kokoro"
    host = env("MINIMAX_API_HOST", "https://api.minimaxi.com")
    try:
        urllib.request.urlopen(host, timeout=10)
    except urllib.error.HTTPError:
        pass  # reachable, just no route at "/"
    except Exception as e:
        log(f"MiniMax 不可达（{e}），改用本地 Kokoro 配音")
        return "kokoro"
    return "minimax"


def mock_request(text, out_mp3):
    """Test-only stand-in: a quiet tone whose length matches ~4.6 chars/s speech."""
    secs = max(1.2, len(text) / 4.6)
    run(["ffmpeg", "-y", "-v", "error", "-f", "lavfi",
         "-i", f"sine=frequency=330:duration={secs:.2f}:sample_rate=32000",
         "-af", "volume=0.08", "-ac", "1", str(out_mp3)])


def synthesize(script, out_dir, mock=False):
    """Return {line_id: {"file": wav, "duration": secs, "text": text}}."""
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    cfg = script["tts"]
    engine = pick_engine(mock)
    manifest = {}
    for line in script["lines"]:
        text = line["voice"]
        # tts_text may swap a polyphonic character for a homophone (e.g. 教→交)
        # so the engine reads it right; the card still shows `voice`.
        spoken = line.get("tts_text", text)
        tag = f"{engine}_" + _cache_key(spoken, cfg)
        raw = out_dir / f"{line['id']}_{tag}.{'wav' if engine == 'kokoro' else 'mp3'}"
        wav = out_dir / f"{line['id']}_{tag}.out.wav"
        if not raw.exists():
            log(f"TTS[{engine}] {line['id']}: {spoken}")
            if engine == "mock":
                mock_request(spoken, raw)
            elif engine == "kokoro":
                kokoro_request(spoken, cfg, raw)
            else:
                raw.write_bytes(minimax_request(spoken, cfg))
        if not wav.exists():
            af = "anull" if engine == "mock" else SILENCE_TRIM
            run(["ffmpeg", "-y", "-v", "error", "-i", raw, "-af", af,
                 "-ar", "48000", "-ac", "2", wav])
        manifest[line["id"]] = {"file": str(wav), "duration": duration(wav), "text": text}
    (out_dir / "manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    total = sum(m["duration"] for m in manifest.values())
    log(f"配音合计 {total:.1f}s / {len(manifest)} 句（引擎 {engine}）")
    return manifest
