"""Shared helpers: paths, config loading, subprocess and media probing."""
import json
import os
import shlex
import subprocess
import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent
CONFIG_DIR = ROOT / "config"
FONT_DIR = ROOT / "assets" / "fonts"
VIDEO_EXTS = (".mp4", ".mov", ".mkv", ".webm", ".m4v")


def log(msg):
    print(f"[promo] {msg}", flush=True)


def load_yaml(path):
    with open(path, encoding="utf-8") as f:
        return yaml.safe_load(f)


def load_script():
    return load_yaml(CONFIG_DIR / "script.yaml")


def load_shots():
    return load_yaml(CONFIG_DIR / "shots.yaml")


def run(cmd, **kw):
    """Run a command, echoing it; raise with stderr tail on failure."""
    printable = " ".join(shlex.quote(str(c)) for c in cmd)
    if len(printable) > 400:
        printable = printable[:400] + " ..."
    log(f"$ {printable}")
    proc = subprocess.run([str(c) for c in cmd], capture_output=True, text=True, **kw)
    if proc.returncode != 0:
        sys.stderr.write(proc.stderr[-4000:])
        raise RuntimeError(f"command failed ({proc.returncode}): {cmd[0]}")
    return proc


def probe(path):
    out = subprocess.run(
        ["ffprobe", "-v", "error", "-print_format", "json",
         "-show_format", "-show_streams", str(path)],
        capture_output=True, text=True, check=True).stdout
    return json.loads(out)


def duration(path):
    return float(probe(path)["format"]["duration"])


def video_size(path):
    for s in probe(path)["streams"]:
        if s.get("codec_type") == "video":
            return int(s["width"]), int(s["height"])
    raise ValueError(f"no video stream in {path}")


def find_footage(footage_dir, shot_id):
    for ext in VIDEO_EXTS:
        p = Path(footage_dir) / f"{shot_id}{ext}"
        if p.exists():
            return p
    return None


def env(name, default=None):
    v = os.environ.get(name, default)
    return v.strip() if isinstance(v, str) else v
