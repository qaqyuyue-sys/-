"""Stock footage search & download (Pexels / Pixabay) with clean-frame filters.

Only shots marked `local: false` in config/shots.yaml are fetched by default:
landmark shots of Yangling itself are not in stock libraries and should come
from authorised local aerial footage. `--include-local` fills those with
generic stand-ins so a full draft can be cut; credits.json flags them.

Env: PEXELS_API_KEY and/or PIXABAY_API_KEY
"""
import json
import re
import shutil
import urllib.parse
import urllib.request
from pathlib import Path

from .common import env, find_footage, log

PEOPLE = re.compile(
    r"\b(person|people|man|men|woman|women|girl|boy|child|children|kid|kids|"
    r"farmer|worker|crowd|couple|family|tourist|portrait|selfie|face|walking|"
    r"student|students|businessman|dancer|runner|cyclist)\b", re.I)
MIN_W = 1920
UA = {"User-Agent": "yangling-promo/1.0"}


def _get_json(url, headers=None):
    req = urllib.request.Request(url, headers={**UA, **(headers or {})})
    with urllib.request.urlopen(req, timeout=60) as r:
        return json.loads(r.read().decode("utf-8"))


def search_pexels(query, key):
    q = urllib.parse.urlencode({"query": query, "orientation": "landscape",
                                "size": "large", "per_page": 20})
    data = _get_json(f"https://api.pexels.com/videos/search?{q}", {"Authorization": key})
    for v in data.get("videos", []):
        words = v.get("url", "").replace("-", " ") + " " + " ".join(v.get("tags") or [])
        files = [f for f in v.get("video_files", [])
                 if (f.get("width") or 0) >= MIN_W and f.get("file_type") == "video/mp4"
                 and (f.get("width") or 0) > (f.get("height") or 0)]
        if not files:
            continue
        # Prefer 4K (downscaled = sharper 1080p), then the next best.
        f = sorted(files, key=lambda f: (f["width"] >= 3840, f["width"]), reverse=True)[0]
        yield {"source": "Pexels", "page": v.get("url"), "author": v.get("user", {}).get("name"),
               "duration": v.get("duration", 0), "width": f["width"], "height": f["height"],
               "download": f["link"], "words": words, "license": "Pexels License"}


def search_pixabay(query, key):
    q = urllib.parse.urlencode({"key": key, "q": query, "video_type": "film",
                                "safesearch": "true", "per_page": 20})
    data = _get_json(f"https://pixabay.com/api/videos/?{q}")
    for h in data.get("hits", []):
        vids = h.get("videos", {})
        for size in ("large", "medium"):
            f = vids.get(size) or {}
            if f.get("url") and (f.get("width") or 0) >= MIN_W:
                yield {"source": "Pixabay", "page": h.get("pageURL"), "author": h.get("user"),
                       "duration": h.get("duration", 0), "width": f["width"],
                       "height": f["height"], "download": f["url"],
                       "words": h.get("tags", ""), "license": "Pixabay Content License"}
                break


def pick(shot_id, meta, used):
    keys = {"pexels": env("PEXELS_API_KEY"), "pixabay": env("PIXABAY_API_KEY")}
    if not any(keys.values()):
        raise SystemExit("需要 PEXELS_API_KEY 或 PIXABAY_API_KEY 才能自动检索素材")
    for query in meta.get("queries", []):
        cands = []
        if keys["pexels"]:
            cands += list(search_pexels(query, keys["pexels"]))
        if keys["pixabay"]:
            cands += list(search_pixabay(query, keys["pixabay"]))
        for c in cands:
            if c["page"] in used or PEOPLE.search(c["words"]) or c["duration"] < 4:
                continue
            return c
    return None


def fetch(shots_meta, footage_dir, include_local=False, force=False):
    footage_dir = Path(footage_dir)
    footage_dir.mkdir(parents=True, exist_ok=True)
    credits_path = footage_dir / "credits.json"
    credits = json.loads(credits_path.read_text("utf-8")) if credits_path.exists() else {}
    used = {c.get("page") for c in credits.values()}
    for sid, meta in shots_meta.items():
        if find_footage(footage_dir, sid) and not force:
            continue
        if meta.get("local") and not include_local:
            log(f"跳过 {sid}（杨凌实景镜头，需授权素材：{meta['desc']}）")
            continue
        c = pick(sid, meta, used)
        if not c:
            log(f"!! {sid}: 未找到合格素材，请手动补充")
            continue
        dest = footage_dir / f"{sid}.mp4"
        log(f"下载 {sid} ← {c['source']} {c['width']}x{c['height']} {c['page']}")
        req = urllib.request.Request(c["download"], headers=UA)
        with urllib.request.urlopen(req, timeout=300) as r, open(dest, "wb") as f:
            shutil.copyfileobj(r, f)
        used.add(c["page"])
        credits[sid] = {k: c[k] for k in ("source", "page", "author", "license", "width", "height")}
        credits[sid]["placeholder_for_local"] = bool(meta.get("local"))
        credits_path.write_text(json.dumps(credits, ensure_ascii=False, indent=2), "utf-8")
    return credits
