import React from "react";
import { AbsoluteFill, Audio, OffthreadVideo, Sequence, interpolate, staticFile, useCurrentFrame, useVideoConfig } from "remotion";
import { Scene, sec, timeline } from "../data";
import { Card } from "./Card";

export const Shot: React.FC<{ scene: Scene; index: number }> = ({ scene, index }) => {
  const frame = useCurrentFrame();
  const { durationInFrames } = useVideoConfig();
  // 缓慢推镜（Ken Burns），奇偶镜头左右交替漂移，避免节奏单调
  const scale = interpolate(frame, [0, durationInFrames], [1.0, 1.07]);
  const drift = interpolate(frame, [0, durationInFrames], [0, index % 2 === 0 ? -18 : 18]);
  const voiceFrom = sec(timeline.leadInSec);

  return (
    <AbsoluteFill style={{ backgroundColor: "#000" }}>
      <AbsoluteFill style={{ transform: `scale(${scale}) translateX(${drift}px)` }}>
        <OffthreadVideo
          src={staticFile(scene.clip)}
          muted
          style={{ width: "100%", height: "100%", objectFit: "cover" }}
        />
      </AbsoluteFill>
      <AbsoluteFill style={{ background: "linear-gradient(to top, rgba(0,0,0,0.55), transparent 45%)" }} />
      <Card
        label={scene.label}
        title={scene.title}
        text={scene.text}
        voiceFrom={voiceFrom}
        voiceFrames={sec(scene.audioSec)}
      />
      <Sequence from={voiceFrom} layout="none">
        <Audio src={staticFile(scene.audio)} />
      </Sequence>
    </AbsoluteFill>
  );
};
