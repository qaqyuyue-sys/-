#!/usr/bin/env python3
"""Download the real geodata the aerial shots are built from.

  Sentinel-2 L2A true colour, 10 m  — Google Cloud public bucket gcp-public-data-sentinel-2
      tiles 49SBU (Yangling) + 49SBT (Wei River, Qinling), relative orbit R018 (full coverage)
  Copernicus DEM GLO-30             — AWS open data bucket copernicus-dem-30m

Writes to $GEODATA (default /home/user/sat):
  mosaic_<date>.npy   16000 x 10980 x 3 uint8, UTM 49N, top-left E199980 N3900000, 10 m
  dem_utm30.npy       same grid at 30 m (float32 metres)

  python fetch_geodata.py                       # the five dates used in the film
  python fetch_geodata.py --list 2025 5 1.0     # clear R018 scenes in May 2025 (<1 % cloud)
"""
import argparse
import json
import os
import re
import urllib.parse
import urllib.request
from pathlib import Path

import numpy as np

GCS = "https://storage.googleapis.com/storage/v1/b/gcp-public-data-sentinel-2/o"
RAW = "https://storage.googleapis.com/gcp-public-data-sentinel-2/"
DEM = "https://copernicus-dem-30m.s3.amazonaws.com/{n}/{n}.tif"
GEO = Path(os.environ.get("GEODATA", "/home/user/sat"))
DATES = ["20250616", "20240512", "20250417", "20260721", "20251120"]
TILES = {"BU": "L2/tiles/49/S/BU/", "BT": "L2/tiles/49/S/BT/"}
BT_ROW = 9996                       # (3900000 - 3800040) / 10
Y_BOTTOM = 3740000


def ls(prefix, delimiter=None):
    out, tok = [], None
    while True:
        q = {"prefix": prefix, "maxResults": 1000}
        if delimiter:
            q["delimiter"] = delimiter
        if tok:
            q["pageToken"] = tok
        d = json.load(urllib.request.urlopen(GCS + "?" + urllib.parse.urlencode(q)))
        out += d.get("prefixes", []) if delimiter else [i["name"] for i in d.get("items", [])]
        tok = d.get("nextPageToken")
        if not tok:
            return out


def scenes(tile):
    return [s for s in ls(TILES[tile], "/") if "_R018_" in s]


def cloud(scene):
    x = urllib.request.urlopen(RAW + scene + "MTD_MSIL2A.xml", timeout=30).read().decode()
    return float(re.search(r"<Cloud_Coverage_Assessment>([\d.]+)", x).group(1))


def tci(tile, date):
    out = GEO / f"{tile}_{date}_TCI_10m.jp2"
    if out.exists():
        return out
    scene = [s for s in scenes(tile) if f"_{date}T" in s][-1]
    name = [n for n in ls(scene + "GRANULE/") if n.endswith("TCI_10m.jp2")][0]
    print("download", out.name, flush=True)
    urllib.request.urlretrieve(RAW + urllib.parse.quote(name), out)
    return out


def mosaic(date):
    from PIL import Image
    Image.MAX_IMAGE_PIXELS = None
    out = GEO / f"mosaic_{date}.npy"
    if out.exists():
        return
    H = (3900000 - Y_BOTTOM) // 10
    m = np.zeros((H, 10980, 3), np.uint8)
    bt = np.asarray(Image.open(tci("BT", date)))
    m[BT_ROW:H] = bt[:H - BT_ROW]
    del bt
    bu = np.asarray(Image.open(tci("BU", date)))
    m[:10980] = np.where(bu.sum(2, keepdims=True) > 0, bu, m[:10980])
    np.save(out, m)
    print("mosaic", out.name, flush=True)


def dem():
    import rasterio
    from rasterio.merge import merge
    from rasterio.transform import from_origin
    from rasterio.warp import Resampling, reproject
    out = GEO / "dem_utm30.npy"
    if out.exists():
        return
    files = []
    for la in (33, 34, 35):
        for lo in (107, 108):
            n = f"Copernicus_DSM_COG_10_N{la}_00_E{lo}_00_DEM"
            f = GEO / "dem" / f"{n}.tif"
            f.parent.mkdir(exist_ok=True)
            if not f.exists():
                print("download", f.name, flush=True)
                urllib.request.urlretrieve(DEM.format(n=n), f)
            files.append(rasterio.open(f))
    arr, tr = merge(files)
    dst = np.zeros(((3900000 - Y_BOTTOM) // 30 + 1, 10980 // 3 + 1), np.float32)
    reproject(arr[0], dst, src_transform=tr, src_crs="EPSG:4326",
              dst_transform=from_origin(199980, 3900000, 30, 30), dst_crs="EPSG:32649",
              resampling=Resampling.bilinear)
    np.save(out, dst)
    print("dem", out.name, dst.shape, flush=True)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--list", nargs=3, metavar=("YEAR", "MONTH", "MAXCLOUD"))
    a = ap.parse_args()
    GEO.mkdir(parents=True, exist_ok=True)
    if a.list:
        y, mth, mx = a.list
        for s in scenes("BU"):
            if f"_{y}{int(mth):02d}" in s:
                c = cloud(s)
                if c <= float(mx):
                    print(s.split("/")[-2], c)
        return
    for d in DATES:
        mosaic(d)
    dem()


if __name__ == "__main__":
    main()
