import React from "react";
import { AbsoluteFill, Audio, staticFile } from "remotion";
import { TransitionSeries, linearTiming } from "@remotion/transitions";
import { fade } from "@remotion/transitions/fade";
import { Shot } from "./components/Shot";
import { sec, timeline, totalFrames, transitionFrames, voiceWindows } from "./data";

// 背景音乐：旁白出现时压到约 -20dB，空隙处回升，首尾淡入淡出
const bgmVolume = (f: number) => {
  const speaking = voiceWindows.some(([a, b]) => f >= a - 6 && f <= b + 6);
  const base = speaking ? 0.1 : 0.25;
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
            <Shot scene={scene} index={i} />
          </TransitionSeries.Sequence>
        </React.Fragment>
      ))}
    </TransitionSeries>
    {timeline.bgm && <Audio src={staticFile(timeline.bgm)} volume={bgmVolume} loop />}
  </AbsoluteFill>
);
