import raw from "./scenes.json";

export type Scene = {
  id: number;
  label: string;
  title: string;
  text: string;
  clip: string;
  visual: "clip" | "illustration";
  art: string;
  camera: "push" | "pullback";
  audio: string;
  audioSec: number;
  durationSec: number;
};

export type Timeline = {
  fps: number;
  width: number;
  height: number;
  transitionSec: number;
  leadInSec: number;
  bgm: string | null;
  scenes: Scene[];
};

export const timeline = raw as Timeline;

export const sec = (s: number) => Math.round(s * timeline.fps);

export const transitionFrames = sec(timeline.transitionSec);

// 交叉淡化会让相邻镜头重叠，因此总时长要减去转场帧数
export const totalFrames =
  timeline.scenes.reduce((sum, s) => sum + sec(s.durationSec), 0) -
  transitionFrames * (timeline.scenes.length - 1);

// 每段旁白在整片中的起止帧，用于背景音乐自动压低
export const voiceWindows = (() => {
  let start = 0;
  return timeline.scenes.map((s) => {
    const from = start + sec(timeline.leadInSec);
    start += sec(s.durationSec) - transitionFrames;
    return [from, from + sec(s.audioSec)] as const;
  });
})();
