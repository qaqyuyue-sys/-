# 西安城市宣传片（Remotion + MiniMax 配音）

约 57 秒、11 个镜头的城市宣传片工程：航拍素材（缺素材的镜头自动用矢量插画）+ 毛玻璃信息卡片 + 逐字字幕 + 逐句配音 + 原创背景音乐，画面与旁白按音频实测时长自动对齐。

- 画面：[Remotion](https://www.remotion.dev/)（React 写视频），镜头之间 0.5 秒交叉淡化，每个镜头缓慢推镜
- 配音：MiniMax T2A（`speech-2.8-hd`）；备选 Edge TTS（免费、在线）或离线中文 TTS（无需任何网络服务和 Key）
- 素材：`fetch_footage.py` 用 Pexels / Pixabay 官方 API 按分镜搜索词自动下载，并记录来源。没有素材的镜头自动换成分层剪影插画（大雁塔、钟楼、城墙、兵马俑、秦岭等），不需要任何素材也能出完整成片
- 音乐：`make_bgm.py` 现场合成原创配乐（五声音阶铺底 + 类古筝拨弦 + 低音鼓），无版权问题
- 字体：思源宋体 / 思源黑体（Noto Serif SC / Noto Sans SC）的子集，已放在 `public/fonts/`，渲染时**不需要访问 Google**

## 快速开始

需要 Node.js 18+、Python 3.9+、ffmpeg（含 ffprobe）。

```bash
npm install
pip install requests            # 用 MiniMax 配音
# pip install edge-tts          # 或者用免费的 Edge TTS

# 1. 素材：自动下载（Key 免费申请），或手动按下方清单放入 public/clips/
export PEXELS_API_KEY=你的Key          # 或 PIXABAY_API_KEY
python3 scripts/fetch_footage.py
#   没有素材的镜头会自动使用插画，可以先跳过这一步

# 2. 生成配音，同时写出 src/scenes.json（镜头时长由音频时长决定）
export MINIMAX_API_KEY=你的Key
python3 scripts/gen_voice.py --engine minimax
#   MiniMax 不可用时：./scripts/setup_local_tts.sh && python3 scripts/gen_voice.py --engine local
#   只想先看排版：python3 scripts/gen_voice.py --engine silent

# 3. 背景音乐（可选，需 pip install numpy scipy）
python3 scripts/make_bgm.py

# 4. 预览
npm run studio

# 5. 输出
npm run render       # out/xian-promo-1080p.mp4
npm run render:4k    # out/xian-promo-4k.mp4（素材需为 4K 才有意义）
```

## 目录结构

```
scripts/storyboard.json     分镜脚本：文案、卡片标题、素材文件名、目标时长 ← 改内容只改这里
scripts/gen_voice.py        逐句配音 + ffprobe 测时长 → src/scenes.json
scripts/fetch_fonts.py      按文案下载需要的中文字体分片 → public/fonts/ + src/fonts.json
scripts/fetch_footage.py    按搜索词从 Pexels / Pixabay 下载素材 → public/clips/ + CREDITS.md
scripts/make_bgm.py         按时间轴合成原创背景音乐 → public/audio/bgm.mp3
scripts/setup_local_tts.sh  安装离线中文 TTS（local_tts.py）
src/scenes.json             生成文件：时间轴（不要手改，重新运行 gen_voice.py）
src/XianPromo.tsx           主合成：镜头串联、转场、背景音乐压低
src/components/Shot.tsx     单个镜头：视频或插画 + 推镜/拉远 + 渐变遮罩 + 卡片 + 配音
src/components/Card.tsx     信息卡片：入场弹出、金色细线、逐字字幕、出场淡出
src/illustrations/          无素材时的矢量插画：primitives.tsx（山脊、塔、楼、俑等图元）+ scenes.tsx（11 幅场景）
public/clips/               视频素材（文件名需与 storyboard.json 一致）
public/audio/               生成的配音 vo_01.mp3 … vo_11.mp3（可选 bgm.mp3）
```

## 时间轴是怎么对齐的

每个镜头时长 = `max(分镜目标时长, 前留白 0.4s + 旁白时长 + 尾留白 0.9s)`。旁白在镜头开始 0.4 秒后响起，字幕在旁白时长内逐字显示完；镜头之间的 0.5 秒淡化落在上一句旁白结束之后，不会出现两句重叠。旁白语速变化时只需重新运行 `gen_voice.py`，全片自动重排。

## 配音（MiniMax）

| 环境变量 | 默认值 | 说明 |
|---|---|---|
| `MINIMAX_API_KEY` | —（必填） | 控制台获取 |
| `MINIMAX_API_BASE` | `https://api.minimaxi.chat` | 大陆接口；国际站账号用 `https://api.minimax.io`。如控制台文档给出其他域名，以控制台为准 |
| `MINIMAX_GROUP_ID` | — | 部分账号需要，填了会拼到 URL 上 |
| `MINIMAX_MODEL` | `speech-2.8-hd` | |
| `MINIMAX_VOICE_ID` | `male-qn-jingying` | 在系统音色列表里挑选，宣传片常用沉稳男声或温婉女声 |
| `MINIMAX_SPEED` | `1.0` | 宣传片可略放慢到 `0.95` |

- 只重做某几句：`python3 scripts/gen_voice.py --engine minimax --only 3 5`
- 想在句中加停顿：在 `storyboard.json` 的文案里插入 MiniMax 的停顿标记（如 `<#0.5#>` 表示 0.5 秒，具体语法以官方文档为准）。注意标记也会被当作字幕显示，若使用请同时调整卡片文字。
- 自己录音或用其他工具配音：把文件按 `vo_01.mp3 …` 命名放进 `public/audio/`，然后运行 `python3 scripts/gen_voice.py --engine probe` 只重测时长。
- Edge TTS：`--engine edge`，可用 `EDGE_VOICE`（默认 `zh-CN-YunxiNeural`）和 `EDGE_RATE`（默认 `-5%`）调整。

### 离线兜底：`--engine local`

MiniMax 和 Edge TTS 都连不上时使用，全程离线，依赖只来自 PyPI。

```bash
./scripts/setup_local_tts.sh                 # 只需一次：建 .venv-tts，并把模型转成 ONNX（约 1 分钟）
python3 scripts/gen_voice.py --engine local  # 合成 11 句，自动响度归一到 -16 LUFS
```

- 模型是 [zhtts](https://pypi.org/project/zhtts/) 内置的 FastSpeech2 + MB-MelGAN，声音为标贝（Baker）女声。清晰度不错，但自然度明显不如 MiniMax，适合内部审片或应急。
- **授权注意**：zhtts 代码是 MIT 协议，但标贝数据集只许非商业使用。对外商用发布请改用 MiniMax 等商用授权的配音。
- 语速：`LOCAL_TTS_SPEED`（时长系数，默认 `1.05`，越大越慢）。
- 多音字和“一”的变调由 `scripts/local_tts.py` 顶部的词典纠正，目前已处理 曲江(qū)、一支/一城(yì)、一份(yí)。改了文案后，可以用下面的命令先看注音，再把读错的词补进词典：
  ```bash
  .venv-tts/bin/python -I -c "import sys,types;sys.modules['tensorflow']=types.ModuleType('t');import zhtts.tts as z;p=z.BakerProcessor(None,loaded_mapper_path=z.ASSET_DIR/'baker_mapper.json');print(p.text_to_phone('曲江池畔'))"
  ```

## 素材清单

`fetch_footage.py` 会按下表的搜索词自动挑选**横版、≥1920 宽、时长足够**的素材，下载到对应文件名，并把来源和作者写进 `public/clips/CREDITS.md`。对某个镜头不满意：`--list 5` 看第 5 镜的候选，`--only 5 --skip 1` 换成下一个候选。也可以手动按下表命名放入 `public/clips/`。素材比镜头长 2–4 秒更稳妥（会从头开始播放）。

| 镜头 | 文件名 | 画面 | 搜索词 |
|---|---|---|---|
| 01 | `01_dawn_aerial.mp4` | 黎明时分城市航拍 | Xi'an aerial sunrise / Xi'an skyline dawn |
| 02 | `02_city_panorama.mp4` | 城区全景 | Xi'an city panorama / Xi'an cityscape drone |
| 03 | `03_city_wall.mp4` | 城墙环线航拍 | Xi'an city wall aerial / ancient city wall China |
| 04 | `04_wild_goose.mp4` | 大雁塔航拍 | Big Wild Goose Pagoda / Dayan Pagoda aerial |
| 05 | `05_terracotta.mp4` | 兵马俑坑俯拍（无游客） | Terracotta Army / Terracotta Warriors pit |
| 06 | `06_lishan_mist.mp4` | 骊山晨雾 | Huaqing Palace / Lishan mountain mist |
| 07 | `07_qujiang.mp4` | 曲江池园林航拍 | Qujiang Pool Xi'an / Chinese garden lake aerial |
| 08 | `08_qinling_weihe.mp4` | 秦岭山脉与渭河 | Qinling mountains / Wei River aerial |
| 09 | `09_hitech_skyline.mp4` | 高新区白天天际线 | Xi'an high-tech zone skyline / modern China skyline day |
| 10 | `10_bell_tower_night.mp4` | 钟楼夜景航拍 | Xi'an Bell Tower night / Xi'an night aerial |
| 11 | `11_night_pullback.mp4` | 城市夜景收尾，缓慢拉远 | Xi'an night skyline drone pull back |

- 免费可商用：Pexels、Pixabay、Mixkit；西安素材较少，缺口可用视觉中国、Storyblocks、Artgrid 等正版付费站。
- 优先 4K（至少 1080p）、人少的画面；下载前逐条确认授权允许商用。
- 自行航拍前确认景区与空域的飞行许可。
- 素材不是 16:9 也没关系，会自动裁切铺满画面。

## 修改文案 / 换城市

1. 编辑 `scripts/storyboard.json`（标题、旁白、素材文件名、目标时长）。
2. `python3 scripts/fetch_fonts.py` —— 文案里出现新字时需要重新下载字体分片。
   网络访问不了 Google Fonts 时，可直接把思源宋体/黑体的 `.otf` 放进 `public/fonts/`，按脚本开头注释改写 `src/fonts.json`。
3. `python3 scripts/gen_voice.py --engine minimax`
4. `npm run studio` 检查。

## 实拍素材与插画的切换

`gen_voice.py` 每次运行都会检查 `public/clips/` 下有没有对应文件：有就用实拍，没有就用 `storyboard.json` 中 `art` 字段指定的插画。所以可以先用插画出片，素材找到一个放一个，放好后运行 `python3 scripts/gen_voice.py --engine probe` 再渲染即可。第 11 镜设置了 `"camera": "pullback"`，实拍或插画都会缓慢拉远收尾。

## 背景音乐

- 原创配乐：`python3 scripts/make_bgm.py`。它按当前时间轴生成同样长度的音乐，在第 1 镜、兵马俑、夜景和片尾落低音鼓，并自动启用背景音乐。改了镜头时长或重新配音后需要重新运行。
- 用自己的音乐：放到 `public/audio/bgm.mp3`，在 `scripts/storyboard.json` 中设置 `"bgm": "audio/bgm.mp3"`，再运行一次 `gen_voice.py --engine probe`。
- 旁白出现时音乐压到 -14dB，句间空隙回到 -8dB，过渡约 0.4 秒；片头片尾自动淡入淡出（`src/XianPromo.tsx` 中的 `SPEAK` / `GAP` 可调）。

## 在 Claude Code 云端环境里运行

云端环境默认只放行包管理器等少数域名。要让 MiniMax 配音和素材下载在云端跑通，需要在环境设置（会话标题栏的云环境菜单 → Edit → Network access）中把下列域名加入 Allowed domains（保持 “Allow package managers” 勾选）：

| 用途 | 域名 |
|---|---|
| MiniMax 配音 | `api.minimaxi.com`、`api.minimaxi.chat`（国际站账号用 `api.minimax.io`） |
| Pexels 素材 | `api.pexels.com`、`videos.pexels.com` |
| Pixabay 素材 | `pixabay.com`、`cdn.pixabay.com` |

API Key 请在同一设置页里以环境变量的形式添加：`MINIMAX_API_KEY`、`PEXELS_API_KEY`、`PIXABAY_API_KEY`。不要粘贴到聊天里。新会话才会读到新设置。

## 已验证

- Linux + Chromium 下完成整片 1080p 渲染。用测试音检测，11 句旁白的起点与时间轴误差都在 0.06 秒以内（来自 MP3 编码固有延迟）。
- 离线 TTS（`--engine local`）已生成全部 11 句，成片约 56.8 秒；逐句检查过注音。
- 11 幅插画逐帧渲染检查过构图（地标避开左下角卡片）；原创配乐已生成并混入成片。
- MiniMax 接口和 Pexels/Pixabay 下载**没有实际调用过**：所在云环境的网络策略拦截了这些域名，也没有 Key。首次使用 MiniMax 时请先用 `--only 1` 试一句。
