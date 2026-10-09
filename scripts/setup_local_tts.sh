#!/usr/bin/env bash
# 离线中文 TTS（MiniMax / Edge TTS 都不可用时的兜底方案）
# 模型：zhtts 内置的 FastSpeech2 + MB-MelGAN（标贝女声数据训练），只需从 PyPI 安装。
# 新版 TensorFlow 已不带 TFLite Flex 算子，因此这里一次性把模型转成 ONNX，
# 之后合成只依赖 onnxruntime，不再需要 TensorFlow。
set -euo pipefail
cd "$(dirname "$0")/.."

VENV=.venv-tts
OUT=scripts/local_tts_models
python3 -m venv "$VENV"
"$VENV/bin/pip" install -q --upgrade pip
"$VENV/bin/pip" install -q onnxruntime numpy scipy pypinyin
"$VENV/bin/pip" install -q --no-deps zhtts==0.0.1

if [[ ! -f "$OUT/fastspeech2.onnx" || ! -f "$OUT/mb_melgan.onnx" ]]; then
  echo "首次运行：安装转换工具并把 TFLite 模型转成 ONNX（只需一次）…"
  "$VENV/bin/pip" install -q "tensorflow-cpu==2.20.0" tf2onnx onnx
  ASSET=$("$VENV/bin/python" -c "import importlib.util,os;print(os.path.join(os.path.dirname(importlib.util.find_spec('zhtts').origin),'asset'))")
  mkdir -p "$OUT"
  "$VENV/bin/python" -m tf2onnx.convert --tflite "$ASSET/fastspeech2_quan.tflite" --output "$OUT/fastspeech2.onnx" --opset 17 >/dev/null 2>&1
  "$VENV/bin/python" -m tf2onnx.convert --tflite "$ASSET/mb_melgan.tflite" --output "$OUT/mb_melgan.onnx" --opset 17 >/dev/null 2>&1
fi
echo "离线 TTS 已就绪：python3 scripts/gen_voice.py --engine local"
