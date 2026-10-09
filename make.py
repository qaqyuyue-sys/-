#!/usr/bin/env python3
"""杨凌城市宣传片 —— 一键生成

  python make.py fonts              下载思源宋体/黑体（GitHub）
  python make.py footage            从 Pexels/Pixabay 检索下载通用镜头
  python make.py tts                MiniMax 逐句合成配音
  python make.py render             剪辑 + 卡片字幕 + 混音 → output/yangling_promo.mp4
  python make.py all                以上全部

  --test   用合成测试画面 + 占位音频跑通整条流水线（不需要任何密钥/网络），
           输出到 build_test/，仅用于检查时间轴与卡片效果
"""
import argparse
import sys
import urllib.request
from pathlib import Path

from promo import cards, footage, render, timeline, tts
from promo.common import FONT_DIR, ROOT, load_script, load_shots, log, run

FONT_URLS = {
    "SourceHanSerifCN-Bold.otf": "adobe-fonts/source-han-serif/release/SubsetOTF/CN/SourceHanSerifCN-Bold.otf",
    "SourceHanSerifCN-Heavy.otf": "adobe-fonts/source-han-serif/release/SubsetOTF/CN/SourceHanSerifCN-Heavy.otf",
    "SourceHanSansCN-Medium.otf": "adobe-fonts/source-han-sans/release/SubsetOTF/CN/SourceHanSansCN-Medium.otf",
    "SourceHanSansCN-Bold.otf": "adobe-fonts/source-han-sans/release/SubsetOTF/CN/SourceHanSansCN-Bold.otf",
}


def cmd_fonts(_):
    FONT_DIR.mkdir(parents=True, exist_ok=True)
    for name, path in FONT_URLS.items():
        dest = FONT_DIR / name
        if dest.exists():
            continue
        log(f"下载字体 {name}")
        urllib.request.urlretrieve(f"https://raw.githubusercontent.com/{path}", dest)


def make_test_footage(shots, footage_dir):
    """Synthetic moving gradients labelled with the shot id (pipeline test only)."""
    footage_dir.mkdir(parents=True, exist_ok=True)
    palettes = ["0x1d3b2a:0xd9a441", "0x16324f:0x8fb8de", "0x2f4f2f:0xe8d9a0",
                "0x40250f:0xf0b35a", "0x0f2a3d:0x6fc3b2", "0x2b2b45:0xf2a65a"]
    for i, sid in enumerate(shots):
        out = footage_dir / f"{sid}.mp4"
        if out.exists():
            continue
        c0, c1 = palettes[i % len(palettes)].split(":")
        run(["ffmpeg", "-y", "-v", "error", "-f", "lavfi",
             "-i", f"gradients=s=1920x1080:r=30:c0={c0}:c1={c1}:speed=0.02:duration=8",
             "-vf", f"drawtext=fontfile=/usr/share/fonts/truetype/wqy/wqy-zenhei.ttc:"
                    f"text='TEST {sid}':fontcolor=white@0.35:fontsize=44:x=60:y=60",
             "-c:v", "libx264", "-preset", "ultrafast", "-crf", "23", out])


def cmd_footage(args):
    shots = load_shots()
    if args.test:
        make_test_footage(shots, args.footage)
    else:
        footage.fetch(shots, args.footage, include_local=args.include_local)


def cmd_tts(args):
    return tts.synthesize(load_script(), args.build / "audio", mock=args.test)


def cmd_render(args):
    script, shots = load_script(), load_shots()
    v = script["video"]
    voices = tts.synthesize(script, args.build / "audio", mock=args.test)
    tl = timeline.build(script, voices)
    log(timeline.describe(tl))
    args.build.mkdir(parents=True, exist_ok=True)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    render.write_sidecars(tl, args.out.parent)

    clips = render.conform_shots(tl, shots, args.footage, v, args.build / "shots")
    base, mix = args.build / "base.mp4", args.build / "mix.wav"
    render.edit_base(tl, clips, v, base)
    render.mix_audio(tl, script.get("music"), mix, ROOT)
    overlay, mask = cards.render_layers(tl, v["width"], v["height"], v["fps"], args.build)
    render.composite(base, mask, overlay, mix, args.out)
    log(f"完成 → {args.out}  ({tl.duration:.1f}s)")


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawTextHelpFormatter)
    p.add_argument("step", choices=["fonts", "footage", "tts", "render", "all"])
    p.add_argument("--test", action="store_true", help="合成测试画面+占位音频，验证流水线")
    p.add_argument("--include-local", action="store_true",
                   help="杨凌实景镜头也先用图库通用素材占位")
    args = p.parse_args()
    base = "build_test" if args.test else "build"
    args.build = ROOT / base
    args.footage = ROOT / (f"{base}/footage" if args.test else "footage")
    args.out = ROOT / (f"{base}/output/yangling_promo_TEST.mp4" if args.test
                       else "output/yangling_promo.mp4")

    steps = {"fonts": [cmd_fonts], "footage": [cmd_footage], "tts": [cmd_tts],
             "render": [cmd_render],
             "all": [cmd_fonts, cmd_footage, cmd_render]}[args.step]
    for s in steps:
        s(args)


if __name__ == "__main__":
    sys.exit(main())
