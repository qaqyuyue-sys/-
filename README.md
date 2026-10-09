# 杨凌城市宣传片 ·《杨凌 · 希望的田野》

约 60 秒城市宣传片的完整制作流水线：解说稿 + 分镜 → MiniMax 逐句配音 → 多机位镜头剪辑（航拍为主）→ 毛玻璃卡片字幕 → 混音成片。

- 解说稿与时间结构：[`config/script.yaml`](config/script.yaml)
- 镜头库（景别、运镜、检索词、是否需杨凌实景）：[`config/shots.yaml`](config/shots.yaml)
- 分镜脚本（给导演/摄影看的版本）：[`docs/分镜脚本.md`](docs/分镜脚本.md)

## 音画字如何保证同步

1. 每句解说单独调用 MiniMax `t2a_v2` 合成，并去掉首尾静音，得到精确时长；
2. 时间轴按"每句的真实音频时长 + 前后留白"排布，镜头切点、配音位置、卡片出入场全部用同一套时间值；
3. 卡片在配音开始前 0.15 秒浮现，配音结束后 0.3 秒淡出；卡片底部的金色进度条随朗读进度实时推进；
4. 同时导出 `output/subtitles.srt` 与 `output/timeline.json`，可直接导入剪映 / Premiere 二次精修。

## 卡片质感

毛玻璃卡片：卡片区域实时高斯模糊背后的视频画面 + 深色半透明底 + 顶部高光与描边 + 柔和投影 + 金色竖条与标签胶囊 + 序号 + 朗读进度条；入场 0.45 秒缓出上浮，出场 0.3 秒淡出。片头/片尾为居中大标题卡（思源宋体 Heavy）。

## 使用

```bash
pip install -r requirements.txt          # 另需 ffmpeg 6.x
python make.py fonts                      # 下载思源宋体/黑体

# 1. 素材：通用镜头可自动检索；★杨凌实景镜头请放入 footage/<镜头id>.mp4
export PEXELS_API_KEY=...                 # 或 PIXABAY_API_KEY
python make.py footage                    # 加 --include-local 用通用素材临时占位实景镜头

# 2. 配音（MiniMax）
export MINIMAX_API_KEY=...
export MINIMAX_API_HOST=https://api.minimaxi.com   # 海外账号：https://api.minimax.io
python make.py tts

# 3. 成片 → output/yangling_promo.mp4
cp 你的背景音乐.mp3 assets/bgm.mp3        # 可选，配音时自动压低
python make.py render
```

`python make.py all --test` 无需任何密钥和网络，用合成测试画面和占位音频跑通整条流水线（输出到 `build_test/`），用于检查时间轴与卡片效果。

### 常用调整

| 想改 | 位置 |
|---|---|
| 解说词 / 卡片标签 | `config/script.yaml` → `lines[].voice` / `card.tag` |
| 音色、语速、情绪 | `config/script.yaml` → `tts`（`voice_id`、`speed`、`emotion`） |
| 某句用哪些镜头 | `config/script.yaml` → `lines[].shots` |
| 素材入点 | `config/shots.yaml` → 对应镜头加 `start: 秒` |
| 调色 / 转场时长 | `config/script.yaml` → `video.grade` / `video.transition` |

素材版权信息记录在 `footage/credits.json`；Pexels / Pixabay 素材可商用、无需署名，杨凌实景素材请确认授权范围。
