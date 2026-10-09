import React from "react";
import { AbsoluteFill, Audio, staticFile } from "remotion";
import { TransitionSeries, linearTiming } from "@remotion/transitions";
import { fade } from "@remotion/transitions/fade";
import { Shot } from "./components/Shot";
import { sec, timeline, totalFrames, transitionFrames, voiceWindows } from "./data";

// 背景音乐：旁白时压到 -14dB，句间空隙回到 -8dB，约 0.4 秒平滑过渡；首尾淡入淡出
const SPEAK = 0.2;
const GAP = 0.4;
const RAMP = 12;
const bgmVolume = (f: number) => {
  const duck = Math.max(
    0,
    ...voiceWindows.map(([a, b]) => Math.min(1, Math.max(0, Math.min(f - (a - RAMP), b + RAMP - f) / RAMP))),
  );
  const base = GAP - (GAP - SPEAK) * duck;
  const fadeIn = Math.min(1, f / 30);
  const fadeOut = Math.min(1, (totalFrames - f) / 60);
  return base * Math.max(0, Math.min(fadeIn, fadeOut));
};

export const XianPromo: React.FC = () => (
  <AbsoluteFill style={{ backgroundColor: "#000" }}>
    <TransitionSeries>
      {timeline.scenes.map((scene, i) => (
        <React.Fragment key={scene.id}>
          {i > 0 && (
            <TransitionSeries.Transition
              presentation={fade()}
              timing={linearTiming({ durationInFrames: transitionFrames })}
            />
          )}
          <TransitionSeries.Sequence durationInFrames={sec(scene.durationSec)}>
            <Shot scene={scene} index={i} count={timeline.scenes.length} />
          </TransitionSeries.Sequence>
        </React.Fragment>
      ))}
    </TransitionSeries>
    {timeline.bgm && <Audio src={staticFile(timeline.bgm)} volume={bgmVolume} loop />}
  </AbsoluteFill>
);
