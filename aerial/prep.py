#!/usr/bin/env python3
"""Cut per-shot textures and heightfields from the Sentinel-2 mosaics and DEM.

Inputs (built by fetch_geodata.py, kept outside git):
  $GEODATA/mosaic_<date>.npy   10 m true-colour mosaic, UTM 49N,
                               top-left E199980 N3900000, 16000 x 10980 px
  $GEODATA/dem_utm30.npy       Copernicus GLO-30 on the same grid at 30 m
Outputs: aerial/assets/
"""
import json
import os
import sys
from pathlib import Path

import numpy as np
import yaml
from PIL import Image, ImageEnhance

Image.MAX_IMAGE_PIXELS = None
HERE = Path(__file__).resolve().parent
GEO = Path(os.environ.get("GEODATA", "/home/user/sat"))
OUT = HERE / "assets"
X0, Y0 = 199980, 3900000          # mosaic top-left (UTM 49N)
CE, CN = 230427, 3796196          # Yangling centre = local origin
MAX_TEX = 8192


def mosaic(date):
    return np.load(GEO / f"mosaic_{date}.npy", mmap_mode="r")


_stretch = {}


def grade(arr, date):
    """Per-date percentile stretch measured on the plain, then mild contrast/saturation."""
    if date not in _stretch:
        m = mosaic(date)
        sample = np.asarray(m[8000:12000:4, 1000:9000:4]).reshape(-1, 3).astype(np.float32)
        sample = sample[sample.sum(1) > 0]
        lo = np.percentile(sample, 0.15, axis=0)
        hi = np.percentile(sample, 99.8, axis=0)
        _stretch[date] = (lo, hi)
    lo, hi = _stretch[date]
    a = (arr.astype(np.float32) - lo) / (hi - lo)
    a = np.clip(a, 0, 1) ** 0.82                         # lift vegetation shadows
    img = Image.fromarray((np.clip(a, 0, 1) * 255).astype(np.uint8))
    return ImageEnhance.Color(img).enhance(1.06)


def local_to_px(e, n, res=10):
    return (CE + e - X0) / res, (Y0 - (CN + n)) / res


def crop(date, region):
    e0, n0, e1, n1 = region
    m = mosaic(date)
    H, W = m.shape[:2]
    x0, y0 = local_to_px(e0, n1)
    x1, y1 = local_to_px(e1, n0)
    x0, y0 = max(0, int(x0)), max(0, int(y0))
    x1, y1 = min(W, int(x1)), min(H, int(y1))
    # report the clipped extent back in local metres
    ext = [X0 + x0 * 10 - CE, Y0 - y1 * 10 - CN, X0 + x1 * 10 - CE, Y0 - y0 * 10 - CN]
    return np.asarray(m[y0:y1, x0:x1]), ext


def super_res(img, mode, cache):
    """Real-ESRGAN 4x (ONNX, CPU) for close-range shots; cached per crop."""
    if cache.exists():
        return Image.open(cache)
    sys.path.insert(0, str(HERE / "sr"))
    import esrgan_onnx
    src = cache.with_suffix(".src.png")
    img.save(src)
    model = Path(os.environ.get("MODELS", HERE.parent / "models")) / f"{mode}.onnx"
    esrgan_onnx.upscale(str(model), str(src), str(cache))
    src.unlink()
    return Image.open(cache)


def save_tex(arr, date, path, sr=None):
    img = grade(arr, date)
    if sr:
        img = super_res(img, sr, path.with_name(path.stem + f".sr_{sr}.jpg"))
    w, h = img.size
    s = min(1.0, MAX_TEX / max(w, h))
    if s < 1:
        img = img.resize((int(w * s), int(h * s)), Image.LANCZOS)
    img.save(path, quality=93)
    return img.size


def save_dem(ext, path, max_seg):
    dem = np.load(GEO / "dem_utm30.npy", mmap_mode="r")
    e0, n0, e1, n1 = ext
    x0, y0 = local_to_px(e0, n1, 30)
    x1, y1 = local_to_px(e1, n0, 30)
    x0, y0, x1, y1 = int(x0), int(y0), int(np.ceil(x1)), int(np.ceil(y1))
    sub = np.asarray(dem[max(0, y0):y1 + 1, max(0, x0):x1 + 1], dtype=np.float32)
    step = max(1, int(np.ceil(max(sub.shape) / max_seg)))
    sub = sub[::step, ::step]
    sub.astype("<f4").tofile(path)
    return sub.shape  # rows, cols


def main(only=None):
    cfg = yaml.safe_load(open(HERE / "shots.yaml", encoding="utf-8"))
    d = cfg["defaults"]
    OUT.mkdir(exist_ok=True)
    dates = {s.get("date", d["date"]) for s in cfg["shots"].values()}
    for s in cfg["shots"].values():
        dates.update(s.get("wipe", []))

    # Whole-mosaic base layer reaching to the horizon (20 m texture, 180 m mesh).
    full = [X0 - CE, Y0 - 16000 * 10 - CN, X0 + 10980 * 10 - CE, Y0 - CN]
    if not (OUT / "world_dem.bin").exists():
        rows, cols = save_dem(full, OUT / "world_dem.bin", 480)
        json.dump({"ext": full, "rows": rows, "cols": cols},
                  open(OUT / "world.json", "w"))
    for date in sorted(dates):
        p = OUT / f"world_{date}.jpg"
        if not p.exists():
            print("world", date, flush=True)
            m = mosaic(date)
            save_tex(np.asarray(m[::2, ::2]), date, p)

    for sid, s in cfg["shots"].items():
        if only and sid not in only:
            continue
        sd = OUT / sid
        sd.mkdir(exist_ok=True)
        date = s.get("date", d["date"])
        arr, ext = crop(date, s["region"])
        texs = []
        for dt in s.get("wipe", [date]):
            a = arr if dt == date else crop(dt, s["region"])[0]
            size = save_tex(a, dt, sd / f"tex_{dt}.jpg", s.get("sr"))
            texs.append(f"tex_{dt}.jpg")
        rows, cols = save_dem(ext, sd / "dem.bin", 768)
        man = {**d, **s, "id": sid, "ext": ext, "textures": texs, "tex_size": size,
               "dem": {"rows": rows, "cols": cols}, "world_tex": f"world_{date}.jpg"}
        json.dump(man, open(sd / "manifest.json", "w", encoding="utf-8"), ensure_ascii=False)
        print(sid, ext, size, (rows, cols), flush=True)


if __name__ == "__main__":
    main(sys.argv[1:] or None)
