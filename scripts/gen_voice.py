#!/usr/bin/env python3
"""逐句生成旁白配音，并按音频时长写出 src/scenes.json（Remotion 据此排镜头）。

用法：
  python3 scripts/gen_voice.py --engine minimax     # MiniMax T2A（需 MINIMAX_API_KEY）
  python3 scripts/gen_voice.py --engine edge        # Edge TTS（免费，需 pip install edge-tts）
  python3 scripts/gen_voice.py --engine silent      # 按字数生成静音占位，用于无 Key 时预览
  python3 scripts/gen_voice.py --engine probe       # 不合成，只重新测量现有音频时长
  python3 scripts/gen_voice.py --engine minimax --only 3 5   # 只重做第 3、5 句

MiniMax 相关环境变量：
  MINIMAX_API_KEY    必填
  MINIMAX_API_BASE   默认 https://api.minimaxi.chat（大陆）；国际站用 https://api.minimax.io
  MINIMAX_GROUP_ID   可选，部分账号需要拼在 URL 上
  MINIMAX_MODEL      默认 speech-2.8-hd
  MINIMAX_VOICE_ID   默认 male-qn-jingying（可在 MiniMax 控制台的系统音色列表中替换）
  MINIMAX_SPEED      默认 1.0
"""
import argparse
import asyncio
import binascii
import json
import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
STORYBOARD = ROOT / "scripts" / "storyboard.json"
AUDIO_DIR = ROOT / "public" / "audio"
SCENES_OUT = ROOT / "src" / "scenes.json"


def tts_minimax(text: str, out: Path) -> None:
    import requests

    base = os.environ.get("MINIMAX_API_BASE", "https://api.minimaxi.chat").rstrip("/")
    url = f"{base}/v1/t2a_v2"
    if os.environ.get("MINIMAX_GROUP_ID"):
        url += f"?GroupId={os.environ['MINIMAX_GROUP_ID']}"
    r = requests.post(
        url,
        headers={
            "Authorization": f"Bearer {os.environ['MINIMAX_API_KEY']}",
            "Content-Type": "application/json",
        },
        json={
            "model": os.environ.get("MINIMAX_MODEL", "speech-2.8-hd"),
            "text": text,
            "stream": False,
            "output_format": "hex",
            "voice_setting": {
                "voice_id": os.environ.get("MINIMAX_VOICE_ID", "male-qn-jingying"),
                "speed": float(os.environ.get("MINIMAX_SPEED", "1.0")),
                "vol": 1.0,
                "pitch": 0,
            },
            "audio_setting": {"sample_rate": 32000, "bitrate": 128000, "format": "mp3", "channel": 1},
        },
        timeout=90,
    )
    r.raise_for_status()
    body = r.json()
    status = body.get("base_resp", {})
    if status.get("status_code", 0) != 0:
        raise RuntimeError(f"MiniMax 返回错误 {status.get('status_code')}: {status.get('status_msg')}")
    out.write_bytes(binascii.unhexlify(body["data"]["audio"]))


def tts_edge(text: str, out: Path) -> None:
    import edge_tts

    voice = os.environ.get("EDGE_VOICE", "zh-CN-YunxiNeural")
    rate = os.environ.get("EDGE_RATE", "-5%")
    asyncio.run(edge_tts.Communicate(text, voice, rate=rate).save(str(out)))


def tts_silent(text: str, out: Path) -> None:
    # 约 4.5 字/秒的正常播音语速，生成等长静音，方便没有 Key 时先排版预览
    sec = max(1.0, len(text) / 4.5)
    subprocess.run(
        ["ffmpeg", "-nostdin", "-loglevel", "error", "-y", "-f", "lavfi", "-i", "anullsrc=r=32000:cl=mono",
         "-t", f"{sec:.2f}", "-q:a", "9", str(out)],
        check=True,
    )


def duration(path: Path) -> float:
    res = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", str(path)],
        check=True, capture_output=True, text=True,
    )
    return float(res.stdout.strip())


ENGINES = {"minimax": tts_minimax, "edge": tts_edge, "silent": tts_silent}


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--engine", choices=[*ENGINES, "probe"], required=True)
    ap.add_argument("--only", type=int, nargs="*", help="只处理这些镜头编号（从 1 开始）")
    args = ap.parse_args()

    if args.engine == "minimax" and not os.environ.get("MINIMAX_API_KEY"):
        sys.exit("请先设置环境变量 MINIMAX_API_KEY")

    board = json.loads(STORYBOARD.read_text(encoding="utf-8"))
    AUDIO_DIR.mkdir(parents=True, exist_ok=True)
    lead, tail = board["leadInSec"], board["tailSec"]

    scenes = []
    for i, s in enumerate(board["scenes"], start=1):
        audio = AUDIO_DIR / f"vo_{i:02d}.mp3"
        if args.engine != "probe" and (not args.only or i in args.only):
            print(f"[{i:02d}] 合成：{s['text']}")
            ENGINES[args.engine](s["text"], audio)
        if not audio.exists():
            sys.exit(f"缺少音频 {audio}，请先用 --engine minimax/edge/silent 生成")
        audio_sec = round(duration(audio), 3)
        # 镜头至少保持分镜设定的时长；旁白较长时自动延长，保证“前留白 + 旁白 + 尾留白”
        dur = round(max(s["targetSec"], lead + audio_sec + tail), 3)
        scenes.append({
            "id": i,
            "label": f"{i:02d} / {len(board['scenes']):02d}",
            "title": s["title"],
            "text": s["text"],
            "clip": f"clips/{s['clip']}",
            "audio": f"audio/{audio.name}",
            "audioSec": audio_sec,
            "durationSec": dur,
        })
        print(f"[{i:02d}] 旁白 {audio_sec:.2f}s → 镜头 {dur:.2f}s")

    out = {k: board[k] for k in ("fps", "width", "height", "transitionSec", "leadInSec", "bgm")}
    out["scenes"] = scenes
    SCENES_OUT.write_text(json.dumps(out, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    total = sum(s["durationSec"] for s in scenes) - board["transitionSec"] * (len(scenes) - 1)
    print(f"已写出 {SCENES_OUT.relative_to(ROOT)}，成片约 {total:.1f} 秒")


if __name__ == "__main__":
    main()
