#!/usr/bin/env python3
"""把旁白/标题用到的中文字体分片下载到 public/fonts/，并写出 src/fonts.json。

Google Fonts 把思源宋体 / 思源黑体（Noto Serif SC / Noto Sans SC）切成上百个分片，
这里只下载文案中真正出现的字所在的分片（通常只有几百 KB），渲染时完全离线。

用法：python3 scripts/fetch_fonts.py
修改文案后请重新运行一次。

若网络无法访问 Google Fonts，也可以手动把字体文件放进 public/fonts/，
再把 src/fonts.json 改成：
  {"serif": [{"file": "fonts/SourceHanSerifSC-Bold.otf", "weight": "700"}],
   "sans":  [{"file": "fonts/SourceHanSansSC-Regular.otf", "weight": "400"}]}
"""
import json
import re
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
FONT_DIR = ROOT / "public" / "fonts"
MANIFEST = ROOT / "src" / "fonts.json"
UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36"

FAMILIES = {"serif": ("Noto Serif SC", "700"), "sans": ("Noto Sans SC", "400")}


def get(url: str) -> bytes:
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=60) as r:
        return r.read()


def parse_ranges(s: str):
    out = []
    for part in s.split(","):
        part = part.strip().upper().removeprefix("U+")
        lo, _, hi = part.partition("-")
        out.append((int(lo, 16), int(hi or lo, 16)))
    return out


def main() -> None:
    board = json.loads((ROOT / "scripts" / "storyboard.json").read_text(encoding="utf-8"))
    chars = set("0123456789 /·")
    for s in board["scenes"]:
        chars |= set(s["title"]) | set(s["text"])
    codepoints = {ord(c) for c in chars}

    FONT_DIR.mkdir(parents=True, exist_ok=True)
    manifest = {}
    for key, (family, weight) in FAMILIES.items():
        css = get(f"https://fonts.googleapis.com/css2?family={family.replace(' ', '+')}:wght@{weight}&display=block").decode()
        faces = re.findall(r"@font-face\s*{([^}]*)}", css)
        entries = []
        for face in faces:
            url = re.search(r"url\((https://[^)]+\.woff2)\)", face).group(1)
            rng = re.search(r"unicode-range:\s*([^;]+);", face).group(1)
            if not any(lo <= cp <= hi for cp in codepoints for lo, hi in parse_ranges(rng)):
                continue
            name = f"{key}-{weight}-{len(entries):02d}.woff2"
            (FONT_DIR / name).write_bytes(get(url))
            entries.append({"file": f"fonts/{name}", "weight": weight, "unicodeRange": rng})
        manifest[key] = entries
        size = sum((FONT_DIR / Path(e["file"]).name).stat().st_size for e in entries) / 1024
        print(f"{family} {weight}: {len(entries)} 个分片，共 {size:.0f} KB")

    MANIFEST.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"已写出 {MANIFEST.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
