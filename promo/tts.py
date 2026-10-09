"""MiniMax text-to-speech: one request per narration line.

Each line is synthesised separately and trimmed of leading/trailing silence,
so its exact duration is known and the on-screen card can be timed to it.

Env:
  MINIMAX_API_KEY   required
  MINIMAX_API_HOST  default https://api.minimaxi.com (国内); 海外账号用 https://api.minimax.io
  MINIMAX_GROUP_ID  optional, appended as ?GroupId= for older accounts
"""
import hashlib
import json
import urllib.request
from pathlib import Path

from .common import duration, env, log, run

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
    manifest = {}
    for line in script["lines"]:
        text = line["voice"]
        tag = ("mock_" if mock else "") + _cache_key(text, cfg)
        raw = out_dir / f"{line['id']}_{tag}.mp3"
        wav = out_dir / f"{line['id']}_{tag}.wav"
        if not raw.exists():
            log(f"TTS {line['id']}: {text}")
            if mock:
                mock_request(text, raw)
            else:
                raw.write_bytes(minimax_request(text, cfg))
        if not wav.exists():
            af = "anull" if mock else SILENCE_TRIM
            run(["ffmpeg", "-y", "-v", "error", "-i", raw, "-af", af,
                 "-ar", "48000", "-ac", "2", wav])
        manifest[line["id"]] = {"file": str(wav), "duration": duration(wav), "text": text}
    (out_dir / "manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    total = sum(m["duration"] for m in manifest.values())
    log(f"配音合计 {total:.1f}s / {len(manifest)} 句")
    return manifest
