#!/usr/bin/env python3
"""Render aerial shots from index.html frame by frame (Playwright + ffmpeg).

Same approach as the xilo-opus-video skill's render.py (page exposes
window.render(t); frames are captured one by one), but serves the page over a
local HTTP server so WebGL can load textures, supersamples, and can apply a
tilt-shift pass.

  python render_shot.py A04_city_skyline_aerial --dur 3.2 --out ../footage/A04_city_skyline_aerial.mp4
  python render_shot.py A04_city_skyline_aerial --still 1.5 --out qa.png
"""
import argparse
import base64
import functools
import http.server
import subprocess
import sys
import threading
import time
from pathlib import Path

import yaml
from playwright.sync_api import sync_playwright

HERE = Path(__file__).resolve().parent
GPU_ARGS = ["--enable-gpu", "--ignore-gpu-blocklist", "--enable-unsafe-swiftshader",
            "--use-gl=angle", "--use-angle=swiftshader"]


class Quiet(http.server.SimpleHTTPRequestHandler):
    def log_message(self, *a):
        pass


def serve():
    srv = http.server.ThreadingHTTPServer(("127.0.0.1", 0),
                                          functools.partial(Quiet, directory=str(HERE)))
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    return srv.server_address[1]


def post_filter(shot_cfg, W, H, dur=1.0):
    vf = [f"scale={W}:{H}:flags=lanczos"]
    ts = shot_cfg.get("tiltshift")
    if ts:
        # blur grows toward top and bottom edges; centre band stays sharp
        mask = (f"geq=lum='255*min(1,pow(abs(Y/{H}-0.55)/0.32,2)*{ts})'")
        vf = [f"scale={W}:{H}:flags=lanczos,split[a][b];[b]gblur=sigma=6[bl];"
              f"color=black:s={W}x{H}:d={dur + 1:.2f},format=gray,{mask}[m];"
              f"[bl][m]alphamerge[blm];[a][blm]overlay=format=auto,format=yuv420p"]
    vf.append("unsharp=5:5:0.45")
    return ",".join(vf)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("shot")
    ap.add_argument("--dur", type=float, default=3.0)
    ap.add_argument("--fps", type=int, default=30)
    ap.add_argument("--still", type=float)
    ap.add_argument("--size", default="1920x1080", help="output size")
    ap.add_argument("--ss", type=float, default=1.25, help="supersampling factor")
    ap.add_argument("--out", required=True)
    a = ap.parse_args()
    W, H = map(int, a.size.split("x"))
    RW, RH = int(W * a.ss), int(H * a.ss)
    cfg = yaml.safe_load(open(HERE / "shots.yaml", encoding="utf-8"))["shots"][a.shot]
    port = serve()

    with sync_playwright() as p:
        b = p.chromium.launch(headless=True, args=GPU_ARGS)
        pg = b.new_page(viewport={"width": RW, "height": RH}, device_scale_factor=1)
        pg.on("console", lambda m: m.type == "error" and print("console:", m.text, file=sys.stderr))
        pg.on("pageerror", lambda e: print("pageerror:", e, file=sys.stderr))
        pg.goto(f"http://127.0.0.1:{port}/index.html?shot={a.shot}&dur={a.dur}&w={RW}&h={RH}&aa=0&aniso=4")
        pg.wait_for_function("window.ready === true", timeout=300000)
        pg.set_default_timeout(600000)

        def frame(t):
            url = pg.evaluate(f"(() => {{ window.render({t}); return document.getElementById('c').toDataURL('image/jpeg', 0.96); }})()")
            return base64.b64decode(url.split(",", 1)[1])
        vf = post_filter(cfg, W, H, a.dur)

        if a.still is not None:
            raw = frame(a.still)
            subprocess.run(["ffmpeg", "-y", "-v", "error", "-f", "jpeg_pipe", "-i", "-",
                            "-filter_complex" if ";" in vf else "-vf", vf, "-frames:v", "1", a.out],
                           input=raw, check=True)
            print("still", a.out)
            return

        n = int(round(a.dur * a.fps))
        enc = subprocess.Popen(
            ["ffmpeg", "-y", "-v", "error", "-f", "image2pipe", "-framerate", str(a.fps),
             "-c:v", "mjpeg", "-i", "-", "-filter_complex" if ";" in vf else "-vf", vf,
             "-t", f"{a.dur:.3f}",
             "-c:v", "libx264", "-preset", "slow", "-crf", "15", "-pix_fmt", "yuv420p", a.out],
            stdin=subprocess.PIPE)
        t0 = time.time()
        for f in range(n):
            enc.stdin.write(frame(f / a.fps))
            if f % 30 == 0:
                print(f"{a.shot} {f}/{n} {(time.time() - t0) / (f + 1):.2f}s/frame", flush=True)
        enc.stdin.close()
        if enc.wait() != 0:
            sys.exit("ffmpeg failed")
        print(f"done {a.out} {time.time() - t0:.0f}s")
        b.close()


if __name__ == "__main__":
    main()
