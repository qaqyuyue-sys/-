# 杨凌城市宣传片 ·《杨凌 · 希望的田野》

约 60 秒、1920×1080 / 30fps 的城市宣传片，从数据到成片全部由代码完成：

- **画面**：用**真实地理数据**在代码里"航拍"杨凌——Sentinel-2 卫星影像（10m，五个季节）+ Copernicus 30m 数字高程，
  Three.js 三维渲染出俯冲、环绕、横移、正俯拍、急速拉升、秦岭雪峰飞越、四季更替等 23 个镜头；
  近景纹理用 Real-ESRGAN 4× 超分。画面中没有人物。
- **配音**：MiniMax T2A 逐句合成（首选）；MiniMax 不可用时自动改用本地 Kokoro v1.1-zh 中文男声。
- **字幕**：每句配音一张毛玻璃卡片，与配音同进同出，金色进度条随朗读推进；片头片尾为居中标题卡。
- **配乐**：按同一时间轴用 numpy 合成（D 大调 72 BPM），配音出现时自动压低。

| 文件 | 内容 |
|---|---|
| [`brief.md`](brief.md) | 完整制作 brief（xilo-opus-video skill 格式），逐镜头说明 |
| [`config/script.yaml`](config/script.yaml) | 解说词、卡片标签、每句对应的镜头、配音与配乐参数 |
| [`aerial/shots.yaml`](aerial/shots.yaml) | 23 个航拍镜头的真实坐标、季节、机位路径、天空 |
| [`docs/分镜脚本.md`](docs/分镜脚本.md) | 分镜表与史实核对 |
| `qa/review_log.md` | 自检打分记录 |

## 流水线

```
aerial/fetch_geodata.py   下载 Sentinel-2（GCS 公共桶）与 Copernicus DEM（AWS 公共桶），拼接、重投影
aerial/prep.py            每个镜头裁切影像与地形、调色、超分（aerial/sr/esrgan_onnx.py，无需 PyTorch）
aerial/render_all.py      按成片时间轴的镜头长度逐帧渲染 aerial/index.html → footage/<镜头>.mp4
make.py render            逐句配音 → 时间轴 → 叠化剪辑 → 卡片字幕图层 → 毛玻璃合成 → 配乐与混音 → output/
```

## 音画字同步

1. 每句解说单独合成并去掉首尾静音，得到精确时长；
2. 段长 = 0.35s + 配音时长 + 0.8s，镜头平分段长；镜头渲染长度、切点、配音位置、卡片出入场都取自同一条时间轴；
3. 卡片在配音前 0.15s 浮现，结束后 0.3s 淡出，进度条按朗读进度推进；
4. 同时导出 `output/subtitles.srt` 与 `output/timeline.json`。

## 运行

```bash
pip install -r requirements.txt                      # 另需 ffmpeg 6.x、Node 18+
(cd aerial && npm install)                           # three.js
python -m playwright install chromium                # 若本机没有 Chromium
python make.py fonts                                 # 思源宋体/黑体
python make.py models                                # Kokoro 中文语音 + Real-ESRGAN（GitHub releases）

python aerial/fetch_geodata.py                       # ~1.5 GB 卫星影像与高程
python aerial/prep.py                                # 超分较慢（CPU 约 1 小时）
python aerial/render_all.py                          # SwiftShader 软件渲染，约 1 秒/帧

export MINIMAX_API_KEY=...                           # 可选；不设置则用本地 Kokoro
python make.py render                                # → output/yangling_promo.mp4
```

`python make.py all --test` 用合成测试画面和占位音频跑通剪辑流水线，不需要任何数据和密钥。

### 替换成实拍素材

把任意镜头的实拍/授权素材命名为 `footage/<镜头id>.mp4` 覆盖即可（镜头 id 见 `config/script.yaml`），
`python make.py render` 会自动裁切、调色并对齐时间轴。`python make.py footage` 可在配置 `PEXELS_API_KEY` / `PIXABAY_API_KEY`
后从图库检索通用镜头（自动过滤含人物的素材，检索词见 `config/shots.yaml`）。

### 常用调整

| 想改 | 位置 |
|---|---|
| 解说词 / 卡片标签 | `config/script.yaml` → `lines[].voice` / `card.tag`（`tts_text` 可替换多音字的读音） |
| 音色、语速 | `config/script.yaml` → `tts`（MiniMax `voice_id`/`speed`；Kokoro `kokoro.speaker`/`speed`） |
| 镜头机位、季节、天空 | `aerial/shots.yaml`，改完重跑 `prep.py` + `render_all.py <镜头id>` |
| 配乐 | 放 `assets/bgm.mp3` 即替代合成配乐；或改 `promo/music.py` |

## 数据来源与许可

- Copernicus Sentinel-2 数据（2024–2026），经 Google Cloud 公共数据集获取 —— 含修改的 Copernicus Sentinel 数据
- Copernicus DEM GLO-30 © DLR e.V. 2010-2014 and © Airbus Defence and Space GmbH 2014-2018，由欧空局在 Copernicus 计划下提供
- 思源宋体 / 思源黑体（SIL OFL 1.1）；Kokoro-82M v1.1-zh（Apache-2.0）；Real-ESRGAN（BSD-3-Clause）；three.js（MIT）
