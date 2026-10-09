# 用代码做视频：已安装的 Skills

入口只有一个：**`xilo-opus-video`**。所有「做视频 / 做动效 / 宣传片 / 复刻视频」的请求都从它开始（问需求 → 三个方案 + 预览 → brief.md → 制作 → 验收）。
它在 `references/code-stack.md` 里选定技术框架后，再去读下面对应的框架 skill。

| Skill | 作用 | 什么时候读 | 来源 |
|---|---|---|---|
| `xilo-opus-video` | 总流程（入口） | 任何做视频的请求 | [Kianzzz/xilo-opus-video](https://github.com/Kianzzz/xilo-opus-video) |
| `remotion-best-practices` | Remotion 官方规范（含 create / markup / render / captions / maps 等子文档） | 方案选了 Remotion | [remotion-dev/skills](https://github.com/remotion-dev/skills) |
| `hyperframes-core` | HyperFrames 合成规范（data-* 时间属性、确定性渲染） | 方案选了 HyperFrames，写 HTML 前 | [heygen-com/hyperframes](https://github.com/heygen-com/hyperframes)（Apache-2.0） |
| `hyperframes-animation` | 动效规则、场景蓝图、GSAP/Three.js/Lottie 适配 | HyperFrames 动效设计 | 同上 |
| `hyperframes-keyframes` | 推拉摇移、Ken Burns、关键帧 | HyperFrames 镜头运动 | 同上 |
| `hyperframes-cli` | init / lint / preview / render 命令 | HyperFrames 预览和渲染 | 同上 |
| `manim-skill` | Manim 数学动画 + TTS 配音 + 字幕同步 | 数学、物理、算法讲解 | [Yusuke710/manim-skill](https://github.com/Yusuke710/manim-skill)（MIT） |

## 有意没装的

HyperFrames 仓库里的 `hyperframes` 路由 skill 自称「任何视频请求的强制入口」，`product-launch-video`、`faceless-explainer`、`motion-graphics` 等工作流 skill 也会抢同样的触发词，装上会和 `xilo-opus-video` 冲突，所以没装。需要时可以单独装：

```bash
npx skills add https://github.com/heygen-com/hyperframes --skill <名字>
```

## 更新

各 skill 是上游仓库的快照（2026-10-09）。更新时重新从上游复制对应目录覆盖即可；`xilo-opus-video/references/code-stack.md` 的「默认选择」一节有本地改动（指向上面这些 skill），覆盖后要补回。
