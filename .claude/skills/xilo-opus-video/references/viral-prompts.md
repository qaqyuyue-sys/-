# 爆款 Opus 5.5 视频提示词（收藏榜前十）

用途：写方案（第 2 步）和 brief.md（第 4 步）时参考别人**已经验证过**的写法。只学结构和手法，不照搬文案。

数据：[zhuyansen/awesome-opus-5.5-video](https://github.com/zhuyansen/awesome-opus-5.5-video) 的 `cases.json`（1427 条，收藏数为 2026-10-05 快照）。规则：只收公开提示词的作品，按收藏排序，每位作者最多两条。提示词原文来自 [yihui-dev/awesome-opus5-5-videos](https://github.com/yihui-dev/awesome-opus5-5-videos)（MIT），版权归各原作者。

| # | 作品 | 收藏 | 提示词类型 | 实际做法 | 原文 |
|---|---|---|---|---|---|
| 1 | 纯代码 UI 动效 @twoclipping | 20,060 | **完整结构化**（2.7k 字） | 单 HTML + 闭式弹簧 + Playwright 4 子帧 + numpy 节拍 | 见下文 A |
| 2 | 动效自荐片·原版 @stephanlivera | 13,027 | 一句话 | 模型自选 | 见下文 B |
| 3 | Claude Pop 音乐视频 @donaldjewkes | 11,574 | 完整（9.6k 字，未抓到） | 原歌+原代码 + Seedance 2.5 + ElevenLabs，自主跑 12 小时 | [X 回复](https://x.com/donaldjewkes/status/2102801469976248500) |
| 4 | 相机对焦实验室 @RyanSael | 10,041 | 简述（未抓到） | **交互网页录屏**，不是渲染成片；1h26m、约 $25.66 | [原帖](https://x.com/RyanSael/status/2102591147927654847) |
| 5 | 动效自荐片·Skia @shneural | 6,413 | 同 B 一句话 | Python/Skia + Blender | 同 B |
| 6 | 高能动效展示片 @crvdesign0 | 6,164 | 完整（192 字，未抓到） | — | [原帖](https://x.com/crvdesign0/status/2103817034618339682) |
| 7 | 真人尺寸乐高鸭 @victormustar | 5,714 | 简述（未抓到） | 产品设计演示 | [原帖](https://x.com/victormustar/status/2103110908444631120) |
| 8 | 猛禽三号发动机 @konstantinsaifo | 5,136 | 简述 | **交互网页录屏**（可拆解 3D 发动机） | 见下文 C |
| 9 | 浏览器版辐射游戏 @chrisfirst | 4,772 | 简述（未抓到） | **网页游戏录屏** | [原帖](https://x.com/chrisfirst/status/2104644598626934858) |
| 10 | 动效自荐片·Remotion @ajith_io | 4,739 | 同 B 一句话 | Remotion | 同 B |

## 规律

- 前十里 **3 条（#2 #5 #10）是同一句话**，换了渲染栈（模型自选 / Skia+Blender / Remotion）。一句话提示词能出爆款，但结果靠抽卡。
- **#1 是唯一一条可复现的完整提示词**，结构正好是 brief-template.md 的七块：`<inputs> <direction> <structure> <build> <gotchas> <start>`。要稳定出片就学它。
- **#4 #8 #9 是交互网页/游戏的录屏**，不是逐帧渲染的视频。做这类的时候，交付物是网页，视频用 render.py 录一段操作。
- **#3 用了视频模型**（Seedance + ElevenLabs），不是纯代码。

## A. 纯代码 UI 动效（@twoclipping，#1）

```text
<inputs>
Ask me for: 8 to 12 UI states I want the shape to become (e.g. button, loader, player, slider, toggle, tabs, chart, command palette, toast), pure black and white or one accent color, and a royalty-free song around 120 BPM (e.g. Mixkit, free for commercial use).
</inputs>

<direction>
Dribbble-level UI motion. One shape, never cut: every state is the same element morphing its size, radius and color while its content swaps with a short blur. A cursor drives every change with real clicks and drags. Light warm-gray canvas, black and white components, one clean UI font (Geist). Springs everywhere, a tiny overshoot at most. The camera zooms so each state fills the frame. The last frame is the first frame, so it loops.
Banned: bouncy easing, particle bursts, glows, gradients on UI chrome, mismatched icon strokes, dead time, anything that looks like a template.
</direction>

<structure>
120 BPM, 7 bars, something happens on every beat.
Button → loader → check → dynamic island → music player with a play/pause morph → scrub the progress bar → it becomes a volume slider that stretches when dragged past max → a toggle flips on the beat → the knob becomes a liquid tab indicator → the tabs open into a chart that draws itself, with a tooltip on hover → it collapses into ⌘K → type to filter → enter → toast → back to the button.
</structure>

<build>
1. One HTML file, square 1440x1440. Every style is computed from time inside seek(t): no CSS transitions, no timers, no state carried between frames.
2. Springs are closed-form step responses. A value that changes target many times is the sum of one spring per change, so it stays a pure function of time.
3. The tab indicator's two edges ride different springs, so the leading edge stretches ahead of the trailing one. Same trick for the toggle knob.
4. Drags are direct manipulation: while the cursor is held, the value is computed from its position. On release it springs back from wherever it was.
5. Analyze the song with numpy for the beat grid and start on a downbeat. Place every UI sound by its measured peak.
6. Render with Playwright: 4 subframes per frame, blended with ffmpeg tmix for motion blur at 60fps.
7. Render one frame per beat before the full render. Fix anything off the grid, cramped or hard to read.
</build>

<gotchas>
Never put will-change on anything the camera scales or the text renders blurry. Text that swaps inside a morphing container needs its own enter and exit timing or it overlaps. Make the last frame identical to the first, cursor position and speed included, or the loop stutters.
</gotchas>

<start>
Ask me for the inputs, then show me the state list on the beat grid before you write any code.
</start>
```

值得学的点：明确的「禁止清单」（Banned）；每拍都有事件（7 小节 120 BPM）；`seek(t)` 纯函数 + 多段弹簧叠加；正式渲染前每拍出一帧自检；首尾帧相同可循环。

## B. 动效自荐片一句话（#2 #5 #10 共用）

```text
make a dynamic 15-second motion graphics video that shows what an incredible motion designer you are, like it's your showreel for a résumé. go all out.
```

用法：用户只给一个模糊想法时，这就是三个方案里「风格化 / 放开发挥」那一档的起点；同一句话配三种渲染栈，本身就是三个拉开差别的方案。

## C. 可交互火箭发动机（@konstantinsaifo，#8）

```text
I asked Claude Opus 5.5 to explain how a rocket engine works by building an interactive Raptor 3 you can take apart in your browser.

Cut it open, follow the oxygen and the methane through both turbopumps, then throttle it and watch the shock diamonds move.
```

用法：讲解类主题可以先做交互网页（Three.js），再给每个交互步骤写 `render(t)` 的自动演示，录成视频。

## 更多

- 全部 1427 条：[zhuyansen/awesome-opus-5.5-video](https://github.com/zhuyansen/awesome-opus-5.5-video)；提示词原文页在 jasonzhu.ai。
- 按 7 类制作路径重写的模板（代码动画、教育讲解、产品宣传、3D、视频模型协作、改编、调用 skill）：[athemeroy/awesome-opus-5-5-videos](https://github.com/athemeroy/awesome-opus-5-5-videos) 的 `docs/prompt-playbook.zh-CN.md`（CC-BY-4.0）。
