#!/usr/bin/env python3
"""按分镜搜索词，从 Pexels / Pixabay 官方 API 自动下载横版高清素材到 public/clips/。

两家的 API Key 都是免费申请的：
  Pexels:  https://www.pexels.com/api/            → 环境变量 PEXELS_API_KEY
  Pixabay: https://pixabay.com/api/docs/           → 环境变量 PIXABAY_API_KEY

用法：
  python3 scripts/fetch_footage.py                    # 有哪个 Key 用哪个，两个都有时先 Pexels 后 Pixabay
  python3 scripts/fetch_footage.py --only 4 5         # 只重新找第 4、5 镜
  python3 scripts/fetch_footage.py --skip 2           # 跳过每个镜头的前 2 个候选（对结果不满意时换一批）
  python3 scripts/fetch_footage.py --list 5           # 只列出第 5 镜的候选，不下载

规则：只要横版、宽度 ≥ 1920、时长 ≥ 镜头时长 + 1 秒；已存在的素材不会被覆盖（用 --only 强制重找）。
来源与作者写入 public/clips/CREDITS.md。下载完成后运行 `gen_voice.py --engine probe`，对应镜头会从插画切换为实拍。
下载后请务必人工过一遍画面：API 无法判断画面是不是西安、有没有人群。
"""
import argparse
import json
import os
import sys
import urllib.parse
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CLIPS = ROOT / "public" / "clips"
CREDITS = CLIPS / "CREDITS.md"
UA = "xian-promo/1.0"


def get_json(url: str, headers: dict) -> dict:
    req = urllib.request.Request(url, headers={"User-Agent": UA, **headers})
    with urllib.request.urlopen(req, timeout=60) as r:
        return json.load(r)


def download(url: str, out: Path) -> None:
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    tmp = out.with_suffix(".part")
    with urllib.request.urlopen(req, timeout=300) as r, open(tmp, "wb") as f:
        while chunk := r.read(1 << 20):
            f.write(chunk)
    tmp.replace(out)


def search_pexels(query: str, min_sec: float):
    key = os.environ.get("PEXELS_API_KEY")
    if not key:
        return []
    q = urllib.parse.urlencode({"query": query, "orientation": "landscape", "size": "large", "per_page": 20})
    data = get_json(f"https://api.pexels.com/videos/search?{q}", {"Authorization": key})
    out = []
    for v in data.get("videos", []):
        if v["duration"] < min_sec:
            continue
        files = [f for f in v["video_files"]
                 if f.get("file_type") == "video/mp4" and (f.get("width") or 0) >= 1920
                 and (f.get("width") or 0) > (f.get("height") or 0)]
        if not files:
            continue
        # 选最接近 1920 宽的版本（4K 原片体积太大，1080p 成片用不上）
        f = min(files, key=lambda f: abs(f["width"] - 1920))
        out.append({"source": "Pexels", "page": v["url"], "author": v["user"]["name"],
                    "url": f["link"], "width": f["width"], "height": f["height"], "duration": v["duration"]})
    return out


def search_pixabay(query: str, min_sec: float):
    key = os.environ.get("PIXABAY_API_KEY")
    if not key:
        return []
    q = urllib.parse.urlencode({"key": key, "q": query, "video_type": "film", "per_page": 20, "safesearch": "true"})
    data = get_json(f"https://pixabay.com/api/videos/?{q}", {})
    out = []
    for h in data.get("hits", []):
        if h["duration"] < min_sec:
            continue
        for size in ("large", "medium"):
            f = h["videos"].get(size) or {}
            if f.get("url") and f.get("width", 0) >= 1920 and f["width"] > f["height"]:
                out.append({"source": "Pixabay", "page": h["pageURL"], "author": h["user"],
                            "url": f["url"], "width": f["width"], "height": f["height"], "duration": h["duration"]})
                break
    return out


def candidates(scene: dict, min_sec: float):
    seen, out = set(), []
    for query in [q.strip() for q in scene["search"].split("/")]:
        for c in search_pexels(query, min_sec) + search_pixabay(query, min_sec):
            if c["page"] not in seen:
                seen.add(c["page"])
                out.append({**c, "query": query})
    return out


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--only", type=int, nargs="*")
    ap.add_argument("--skip", type=int, default=0)
    ap.add_argument("--list", type=int)
    args = ap.parse_args()
    if not (os.environ.get("PEXELS_API_KEY") or os.environ.get("PIXABAY_API_KEY")):
        sys.exit("请设置 PEXELS_API_KEY 或 PIXABAY_API_KEY（均可免费申请）")

    board = json.loads((ROOT / "scripts" / "storyboard.json").read_text(encoding="utf-8"))
    credits = {}
    if CREDITS.exists():
        for line in CREDITS.read_text(encoding="utf-8").splitlines():
            if line.startswith("| `"):
                credits[line.split("`")[1]] = line

    for i, s in enumerate(board["scenes"], start=1):
        if args.list and i != args.list:
            continue
        if args.only and i not in args.only:
            continue
        out = CLIPS / s["clip"]
        if out.exists() and not args.only and not args.list:
            print(f"[{i:02d}] 已有素材，跳过：{s['clip']}")
            continue
        found = candidates(s, s["targetSec"] + 1)
        if args.list:
            for n, c in enumerate(found):
                print(f"  #{n} {c['source']} {c['width']}x{c['height']} {c['duration']}s  {c['page']}  （{c['query']}）")
            return
        if len(found) <= args.skip:
            print(f"[{i:02d}] 没有找到合适素材：{s['search']}（可换搜索词，或手动放入 {s['clip']}）")
            continue
        c = found[args.skip]
        print(f"[{i:02d}] {c['source']} {c['width']}x{c['height']} {c['duration']}s ← {c['page']}")
        download(c["url"], out)
        credits[s["clip"]] = f"| `{s['clip']}` | {s['shot']} | {c['source']} | {c['author']} | {c['page']} |"

    rows = [credits[k] for k in sorted(credits)]
    CREDITS.write_text(
        "# 素材来源\n\nPexels / Pixabay 素材均可免费商用、无需署名，但建议在片尾或简介中致谢。"
        "使用前请再确认各站最新授权条款。\n\n| 文件 | 镜头 | 来源 | 作者 | 页面 |\n|---|---|---|---|---|\n"
        + "\n".join(rows) + "\n",
        encoding="utf-8",
    )
    print(f"来源已写入 {CREDITS.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
