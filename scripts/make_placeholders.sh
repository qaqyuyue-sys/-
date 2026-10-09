#!/usr/bin/env bash
# 为 public/clips/ 中缺失的镜头生成 1080p 渐变占位视频，便于在找齐素材前预览节奏。
# 已存在的真实素材不会被覆盖。
set -euo pipefail
cd "$(dirname "$0")/.."

python3 - <<'PY' | while read -r clip sec; do
import json
b = json.load(open("scripts/storyboard.json", encoding="utf-8"))
for s in b["scenes"]:
    print(s["clip"], s["targetSec"] + 4)
PY
  out="public/clips/$clip"
  if [[ -f "$out" ]]; then echo "跳过（已存在）：$out"; continue; fi
  seed=$(( $(printf '%s' "$clip" | cksum | cut -d' ' -f1) % 1000 ))
  ffmpeg -nostdin -loglevel error -y -f lavfi \
    -i "gradients=s=1920x1080:r=30:d=${sec}:speed=0.008:seed=${seed}:c0=0x1b1f2a:c1=0x6b4f2a:c2=0x2a3b4f:nb_colors=3" \
    -c:v libx264 -pix_fmt yuv420p -crf 28 "$out"
  echo "$clip" >> public/clips/.placeholders   # 供 fetch_footage.py 识别可替换的占位文件
  echo "已生成占位：$out"
done
