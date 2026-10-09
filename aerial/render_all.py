#!/usr/bin/env python3
"""Render every aerial shot at exactly the length the edit needs.

Shot lengths come from the same timeline the final edit uses (voice durations
→ segments → shots), plus the dissolve overlap, so footage/<id>.mp4 drops
straight into `python make.py render`.
"""
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
sys.path.insert(0, str(ROOT))
from promo import timeline, tts  # noqa: E402
from promo.common import load_script  # noqa: E402


def main(only):
    sc = load_script()
    tl = timeline.build(sc, tts.synthesize(sc, ROOT / "build" / "audio"))
    T = sc["video"]["transition"]
    for s in tl.shots:
        if only and s.id not in only:
            continue
        out = ROOT / "footage" / f"{s.id}.mp4"
        if out.exists() and not only:
            continue
        if not (HERE / "assets" / s.id / "manifest.json").exists():
            print("assets not ready:", s.id)
            continue
        dur = round(s.length + T + 0.2, 3)
        subprocess.run([sys.executable, str(HERE / "render_shot.py"), s.id,
                        "--dur", str(dur), "--out", str(out)], check=True)


if __name__ == "__main__":
    main(sys.argv[1:])
