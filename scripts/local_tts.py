"""离线中文 TTS：zhtts 的文本前端 + ONNX 版 FastSpeech2 / MB-MelGAN。

由 gen_voice.py 用 .venv-tts 的解释器调用：
  .venv-tts/bin/python scripts/local_tts.py <输出.wav> <文本>
环境变量 LOCAL_TTS_SPEED：时长系数，>1 更慢，默认 1.05（宣传片语速略放慢）。
"""
import os
import sys
import types
from pathlib import Path

import numpy as np
import onnxruntime as ort
from scipy.io import wavfile

# zhtts 在顶层 import tensorflow，但我们只用它的文本前端，放一个空模块即可
sys.modules.setdefault("tensorflow", types.ModuleType("tensorflow"))
import zhtts.tts as zt  # noqa: E402
from pypinyin import load_phrases_dict  # noqa: E402

# 多音字 / 变调纠正：模型前端是 pypinyin，不处理“一”的变调，个别地名也会读错。
# 改了文案后用 `--engine local` 合成前，可在这里补充词条。
load_phrases_dict({
    "曲江": [["qū"], ["jiāng"]],
    "一支": [["yì"], ["zhī"]],
    "一城": [["yì"], ["chéng"]],
    "一份": [["yí"], ["fèn"]],
})

MODELS = Path(__file__).resolve().parent / "local_tts_models"
SR = 24000


def main() -> None:
    out, text = sys.argv[1], sys.argv[2]
    speed = float(os.environ.get("LOCAL_TTS_SPEED", "1.05"))
    proc = zt.BakerProcessor(data_dir=None, loaded_mapper_path=zt.ASSET_DIR / "baker_mapper.json")
    acoustic = ort.InferenceSession(str(MODELS / "fastspeech2.onnx"))
    vocoder = ort.InferenceSession(str(MODELS / "mb_melgan.onnx"))
    names = [i.name for i in acoustic.get_inputs()]

    pieces = []
    for seg in zt.split_sens(text):
        ids = np.array([proc.text_to_sequence(seg, inference=True)], np.int32)
        feeds = dict(zip(names, [ids, np.array([0], np.int32), np.array([speed], np.float32),
                                 np.array([1.0], np.float32), np.array([1.0], np.float32)]))
        mel = acoustic.run(None, feeds)[1]  # 第二个输出是 postnet 之后的 mel
        wav = vocoder.run(None, {vocoder.get_inputs()[0].name: mel})[0][0, :, 0]
        # 逗号处停 0.25 秒，句号处停 0.4 秒
        pause = 0.4 if seg.endswith(("。", "！", "？")) else 0.25
        pieces += [wav, np.zeros(int(pause * SR), np.float32)]
    wavfile.write(out, SR, np.concatenate(pieces[:-1]).astype(np.float32))


if __name__ == "__main__":
    main()
