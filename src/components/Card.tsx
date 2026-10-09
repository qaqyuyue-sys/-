import React from "react";
import { interpolate, spring, useCurrentFrame, useVideoConfig } from "remotion";
import { sans, serif } from "../fonts";

type Props = {
  label: string;
  title: string;
  text: string;
  // 旁白在本镜头内的起止帧，逐字显示与配音同步
  voiceFrom: number;
  voiceFrames: number;
  // 入场 / 出场时机：避开镜头之间的交叉淡化，免得前后两张卡片叠在一起
  enterAt: number;
  exitBy: number;
};

export const Card: React.FC<Props> = ({ label, title, text, voiceFrom, voiceFrames, enterAt, exitBy }) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();

  const enter = spring({ frame: frame - enterAt, fps, config: { damping: 200 }, durationInFrames: 24 });
  const exit = interpolate(frame, [exitBy - 12, exitBy], [1, 0], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });
  const shown = Math.round(
    interpolate(frame, [voiceFrom, voiceFrom + voiceFrames * 0.92], [0, text.length], {
      extrapolateLeft: "clamp",
      extrapolateRight: "clamp",
    }),
  );
  const lineWidth = interpolate(enter, [0, 1], [0, 72]);

  return (
    <div
      style={{
        position: "absolute",
        left: 120,
        bottom: 110,
        width: 1000,
        boxSizing: "border-box",
        padding: "36px 46px",
        borderRadius: 24,
        background: "rgba(12,14,20,0.55)",
        backdropFilter: "blur(18px)",
        WebkitBackdropFilter: "blur(18px)",
        border: "1px solid rgba(255,255,255,0.18)",
        boxShadow: "0 20px 60px rgba(0,0,0,0.35)",
        color: "#fff",
        opacity: enter * exit,
        transform: `translateY(${interpolate(enter, [0, 1], [40, 0])}px)`,
      }}
    >
      <div style={{ fontFamily: sans, fontSize: 20, letterSpacing: 6, color: "#E8C547" }}>{label}</div>
      <div style={{ width: lineWidth, height: 3, background: "#E8C547", marginTop: 12, borderRadius: 2 }} />
      <div style={{ fontFamily: serif, fontSize: 60, fontWeight: 700, marginTop: 14, letterSpacing: 4 }}>
        {title}
      </div>
      <div style={{ fontFamily: sans, fontSize: 34, marginTop: 16, lineHeight: 1.5, textWrap: "balance" }}>
        {text.slice(0, shown)}
        {/* 占位保持卡片高度不随逐字显示跳动 */}
        <span style={{ opacity: 0 }}>{text.slice(shown)}</span>
      </div>
    </div>
  );
};
