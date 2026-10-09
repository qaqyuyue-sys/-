#!/usr/bin/env python3
"""Vectorize the supplied 常青文创设计 logo into three SVGs (emblem, wordmark, subline) plus brand/logo.js.

  python3 brand/trace_logo.py brand/logo-source.png
Bounds were measured from the ink of the 1254×1254 source.
"""
import json, sys, pathlib

import numpy as np
import potrace
from PIL import Image, ImageFilter

SRC = sys.argv[1]
OUT = pathlib.Path(__file__).resolve().parent
UP = 4                                                     # trace on a 4x upscale for smoother curves
PARTS = {"emblem": (60, 464, 331, 736), "wordmark": (366, 496, 1189, 633), "subline": (366, 667, 1189, 717)}

src = Image.open(SRC).convert("L")
LOGO = {}
for name, box in PARTS.items():
    crop = src.crop(box)
    big = crop.resize((crop.width * UP, crop.height * UP), Image.LANCZOS).filter(ImageFilter.GaussianBlur(UP * 0.35))
    ink = np.asarray(big) < 128
    paths = potrace.Bitmap(~ink).trace(turdsize=8, alphamax=1.0, opticurve=True, opttolerance=0.2)
    d = []
    for curve in paths:
        s = curve.start_point
        seg = [f"M{s.x / UP:.2f} {s.y / UP:.2f}"]
        for c in curve.segments:
            if c.is_corner:
                seg.append(f"L{c.c.x / UP:.2f} {c.c.y / UP:.2f}L{c.end_point.x / UP:.2f} {c.end_point.y / UP:.2f}")
            else:
                seg.append(f"C{c.c1.x / UP:.2f} {c.c1.y / UP:.2f} {c.c2.x / UP:.2f} {c.c2.y / UP:.2f} {c.end_point.x / UP:.2f} {c.end_point.y / UP:.2f}")
        d.append("".join(seg) + "Z")
    w, h = crop.size
    svg = (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {w} {h}" width="{w}" height="{h}">'
           f'<path fill="currentColor" fill-rule="evenodd" d="{" ".join(d)}"/></svg>\n')
    (OUT / f"{name}.svg").write_text(svg)
    LOGO[name] = {"w": w, "h": h, "box": box, "d": " ".join(d)}
    print(f"{name}.svg  {w}x{h}  {len(paths)} paths")

# inline copy for the page (file:// pages cannot use external SVGs as masks)
(OUT / "logo.js").write_text("window.LOGO = " + json.dumps(LOGO) + ";\n")
print("logo.js")
