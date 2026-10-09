import React from "react";

// 插画用的基础图元：全部是 1920×1080 坐标系下的 SVG，用固定随机种子生成，
// 保证每一帧、每次渲染结果完全一致。

export const W = 1920;
export const H = 1080;

export const rng = (seed: number) => {
  let a = seed >>> 0;
  return () => {
    a = (a + 0x6d2b79f5) >>> 0;
    let t = a;
    t = Math.imul(t ^ (t >>> 15), t | 1);
    t ^= t + Math.imul(t ^ (t >>> 7), t | 61);
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
  };
};

export const Sky: React.FC<{ id: string; stops: [number, string][] }> = ({ id, stops }) => (
  <>
    <defs>
      <linearGradient id={id} x1="0" y1="0" x2="0" y2="1">
        {stops.map(([o, c]) => (
          <stop key={o} offset={o} stopColor={c} />
        ))}
      </linearGradient>
    </defs>
    <rect x={-200} y={-200} width={W + 400} height={H + 400} fill={`url(#${id})`} />
  </>
);

export const Glow: React.FC<{ id: string; cx: number; cy: number; r: number; color: string; opacity?: number }> = ({
  id, cx, cy, r, color, opacity = 1,
}) => (
  <>
    <defs>
      <radialGradient id={id}>
        <stop offset="0" stopColor={color} stopOpacity={opacity} />
        <stop offset="1" stopColor={color} stopOpacity={0} />
      </radialGradient>
    </defs>
    <circle cx={cx} cy={cy} r={r} fill={`url(#${id})`} />
  </>
);

export const Sun: React.FC<{ id: string; cx: number; cy: number; r: number; color: string; glow: string }> = ({
  id, cx, cy, r, color, glow,
}) => (
  <>
    <Glow id={`${id}-g`} cx={cx} cy={cy} r={r * 7} color={glow} opacity={0.55} />
    <circle cx={cx} cy={cy} r={r} fill={color} />
  </>
);

export const Stars: React.FC<{ seed: number; count: number; maxY: number; frame: number }> = ({ seed, count, maxY, frame }) => {
  const r = rng(seed);
  return (
    <g>
      {Array.from({ length: count }, (_, i) => {
        const x = r() * W, y = r() * maxY, s = 0.6 + r() * 1.6, ph = r() * 6.28;
        const tw = 0.45 + 0.55 * Math.abs(Math.sin(frame / 18 + ph));
        return <circle key={i} cx={x} cy={y} r={s} fill="#fff" opacity={tw * (1 - y / maxY) * 0.9} />;
      })}
    </g>
  );
};

// 山脊：若干正弦叠加的“分形”轮廓，可平移做视差
export const Ridge: React.FC<{
  seed: number; baseY: number; amp: number; color: string; freq?: number; shift?: number; opacity?: number;
}> = ({ seed, baseY, amp, color, freq = 1, shift = 0, opacity = 1 }) => {
  const r = rng(seed);
  const waves = Array.from({ length: 5 }, (_, k) => ({
    f: (0.0016 * freq) * Math.pow(2.1, k), a: Math.pow(0.5, k), p: r() * 100,
  }));
  const pts: string[] = [];
  for (let x = -300; x <= W + 300; x += 12) {
    const X = x - shift;
    let n = 0;
    for (const w of waves) n += w.a * Math.sin(X * w.f + w.p);
    pts.push(`${x},${(baseY - amp * (0.55 + 0.5 * n)).toFixed(1)}`);
  }
  return <polygon points={`-300,${H + 50} ${pts.join(" ")} ${W + 300},${H + 50}`} fill={color} opacity={opacity} />;
};

export const Mist: React.FC<{ id: string; y: number; h: number; color: string; opacity: number; shift: number }> = ({
  id, y, h, color, opacity, shift,
}) => (
  <>
    <defs>
      <filter id={id} x="-20%" y="-100%" width="140%" height="300%">
        <feGaussianBlur stdDeviation={h * 0.35} />
      </filter>
    </defs>
    <g filter={`url(#${id})`} opacity={opacity}>
      {[0, 1, 2, 3].map((i) => (
        <ellipse key={i} cx={((i * 720 + shift) % 2880) - 480} cy={y + (i % 2) * h * 0.3} rx={520} ry={h * 0.5} fill={color} />
      ))}
    </g>
  </>
);

export const Birds: React.FC<{ seed: number; count: number; frame: number; y: number; color: string }> = ({
  seed, count, frame, y, color,
}) => {
  const r = rng(seed);
  return (
    <g>
      {Array.from({ length: count }, (_, i) => {
        const x0 = r() * 600 + 900, y0 = y + r() * 120, sp = 1.2 + r() * 0.8, ph = r() * 6.28, s = 0.7 + r() * 0.6;
        const flap = Math.sin(frame / 4 + ph) * 5;
        const x = x0 + frame * sp, yy = y0 - frame * 0.25 * sp;
        return (
          <path key={i} transform={`translate(${x},${yy}) scale(${s})`} fill="none" stroke={color} strokeWidth={2.2} strokeLinecap="round"
            d={`M-12 ${flap} Q-6 ${-4 + flap * 0.3} 0 0 Q6 ${-4 + flap * 0.3} 12 ${flap}`} />
        );
      })}
    </g>
  );
};

// 中式屋顶：两端起翘的歇山/庑殿轮廓；ridge=0 时为攒尖顶
export const roofPath = (cx: number, y: number, w: number, h: number, curl: number, ridge = 0.35) => {
  const L = cx - w - curl, R = cx + w + curl;
  return [
    `M${L},${y - curl * 0.55}`,
    `Q${cx - w * 0.85},${y + h * 0.08} ${cx - w * 0.6},${y}`,
    `L${cx + w * 0.6},${y}`,
    `Q${cx + w * 0.85},${y + h * 0.08} ${R},${y - curl * 0.55}`,
    `Q${cx + w * 0.5},${y - h * 0.25} ${cx + w * ridge},${y - h}`,
    `L${cx - w * ridge},${y - h}`,
    `Q${cx - w * 0.5},${y - h * 0.25} ${L},${y - curl * 0.55}`,
    "Z",
  ].join(" ");
};

// 大雁塔：七层方形楼阁式砖塔
export const Pagoda: React.FC<{ cx: number; baseY: number; s: number; color: string; window: string }> = ({
  cx, baseY, s, color, window,
}) => {
  const parts: React.ReactNode[] = [];
  let y = baseY;
  parts.push(<rect key="plat" x={cx - 170 * s} y={y - 34 * s} width={340 * s} height={34 * s} fill={color} />);
  y -= 34 * s;
  for (let i = 0; i < 7; i++) {
    const w = 210 * s * (1 - 0.075 * i), h = 66 * s * (1 - 0.055 * i);
    parts.push(<rect key={`b${i}`} x={cx - w / 2} y={y - h} width={w} height={h} fill={color} />);
    parts.push(<path key={`w${i}`} fill={window}
      d={`M${cx - 9 * s},${y - 6 * s} v${-h * 0.45} a${9 * s},${9 * s} 0 0 1 ${18 * s},0 v${h * 0.45} Z`} />);
    y -= h;
    parts.push(<rect key={`e${i}`} x={cx - w / 2 - 14 * s} y={y - 8 * s} width={w + 28 * s} height={8 * s} fill={color} />);
    y -= 8 * s;
  }
  parts.push(<path key="top" fill={color} d={`M${cx - 40 * s},${y} L${cx},${y - 46 * s} L${cx + 40 * s},${y} Z`} />);
  parts.push(<rect key="pole" x={cx - 3 * s} y={y - 92 * s} width={6 * s} height={50 * s} fill={color} />);
  parts.push(<circle key="ball" cx={cx} cy={y - 94 * s} r={7 * s} fill={color} />);
  return <g>{parts}</g>;
};

// 钟楼：方形砖台 + 重檐三滴水攒尖顶
export const BellTower: React.FC<{ cx: number; baseY: number; s: number; color: string; accent: string; lit?: boolean }> = ({
  cx, baseY, s, color, accent, lit = false,
}) => {
  const y0 = baseY - 170 * s;
  return (
    <g>
      <rect x={cx - 200 * s} y={y0} width={400 * s} height={170 * s} fill={color} />
      <path fill={lit ? accent : "rgba(0,0,0,0.35)"} opacity={lit ? 0.85 : 1}
        d={`M${cx - 42 * s},${baseY} v${-80 * s} a${42 * s},${42 * s} 0 0 1 ${84 * s},0 v${80 * s} Z`} />
      <rect x={cx - 212 * s} y={y0 - 10 * s} width={424 * s} height={10 * s} fill={color} />
      <rect x={cx - 130 * s} y={y0 - 78 * s} width={260 * s} height={68 * s} fill={color} />
      {lit && Array.from({ length: 7 }, (_, i) => (
        <rect key={i} x={cx - 118 * s + i * 36 * s} y={y0 - 70 * s} width={24 * s} height={52 * s} fill={accent} opacity={0.75} />
      ))}
      <path d={roofPath(cx, y0 - 78 * s, 170 * s, 48 * s, 30 * s)} fill={color} />
      <rect x={cx - 100 * s} y={y0 - 166 * s} width={200 * s} height={42 * s} fill={color} />
      {lit && Array.from({ length: 5 }, (_, i) => (
        <rect key={i} x={cx - 88 * s + i * 36 * s} y={y0 - 160 * s} width={22 * s} height={30 * s} fill={accent} opacity={0.7} />
      ))}
      <path d={roofPath(cx, y0 - 124 * s, 140 * s, 40 * s, 26 * s)} fill={color} />
      <path d={roofPath(cx, y0 - 166 * s, 118 * s, 110 * s, 24 * s, 0)} fill={color} />
      <rect x={cx - 3 * s} y={y0 - 312 * s} width={6 * s} height={40 * s} fill={lit ? accent : color} />
      <circle cx={cx} cy={y0 - 316 * s} r={10 * s} fill={lit ? accent : color} />
    </g>
  );
};

// 城墙：连续垛口 + 城楼（箭楼）
export const CityWall: React.FC<{ baseY: number; top: number; color: string; dark: string; gateX: number; s: number }> = ({
  baseY, top, color, dark, gateX, s,
}) => {
  const merlons: React.ReactNode[] = [];
  for (let x = -300; x < W + 300; x += 44) {
    merlons.push(<rect key={x} x={x} y={top - 18} width={26} height={18} fill={color} />);
  }
  const gw = 300 * s, gy = top - 10;
  return (
    <g>
      <rect x={-300} y={top} width={W + 600} height={baseY - top} fill={color} />
      <rect x={-300} y={top + 26} width={W + 600} height={6} fill={dark} opacity={0.5} />
      {merlons}
      {/* 城楼 */}
      <rect x={gateX - gw / 2} y={gy - 150 * s} width={gw} height={150 * s} fill={color} />
      {Array.from({ length: 4 }, (_, row) =>
        Array.from({ length: 8 }, (_, col) => (
          <rect key={`${row}-${col}`} x={gateX - gw / 2 + 22 * s + col * 34 * s} y={gy - 136 * s + row * 34 * s}
            width={14 * s} height={14 * s} fill={dark} />
        )),
      )}
      <path d={roofPath(gateX, gy - 150 * s, gw * 0.56, 66 * s, 34 * s)} fill={color} />
      <path fill={dark} d={`M${gateX - 46 * s},${baseY} v${-(baseY - top) * 0.55} a${46 * s},${46 * s} 0 0 1 ${92 * s},0 v${(baseY - top) * 0.55} Z`} />
    </g>
  );
};

// 天际线：现代楼群，可点亮窗户
export const Skyline: React.FC<{
  seed: number; baseY: number; minH: number; maxH: number; color: string; shift?: number;
  windows?: string; frame?: number; litRatio?: number; spires?: boolean;
}> = ({ seed, baseY, minH, maxH, color, shift = 0, windows, frame = 0, litRatio = 0.35, spires = false }) => {
  const r = rng(seed);
  const els: React.ReactNode[] = [];
  for (let x = -260; x < W + 260;) {
    const w = 46 + r() * 110, h = minH + Math.pow(r(), 1.6) * (maxH - minH), X = x + shift;
    els.push(<rect key={`b${x}`} x={X} y={baseY - h} width={w} height={h + 60} fill={color} />);
    if (spires && h > maxH * 0.7) els.push(<rect key={`s${x}`} x={X + w / 2 - 2} y={baseY - h - 50} width={4} height={50} fill={color} />);
    if (windows) {
      for (let wy = baseY - h + 14; wy < baseY - 8; wy += 22) {
        for (let wx = X + 8; wx < X + w - 12; wx += 18) {
          const v = r();
          if (v < litRatio) {
            const on = Math.sin(frame / 25 + v * 400) > -0.8;
            els.push(<rect key={`w${wx}-${wy}`} x={wx} y={wy} width={8} height={11} fill={windows} opacity={on ? 0.55 + v : 0.1} />);
          }
        }
      }
    }
    x += w + 4 + r() * 18;
  }
  return <g>{els}</g>;
};

// 兵马俑剪影（原点在脚底中心，高约 100）
export const Warrior: React.FC<{ x: number; y: number; s: number; fill: string; shade: string; variant: number }> = ({
  x, y, s, fill, shade, variant,
}) => (
  <g transform={`translate(${x},${y}) scale(${s})`}>
    <rect x={-12} y={-24} width={9} height={24} fill={shade} />
    <rect x={3} y={-24} width={9} height={24} fill={shade} />
    <path d="M-19 -48 L19 -48 L22 -22 L-22 -22 Z" fill={fill} />
    <path d="M-15 -80 L15 -80 L18 -47 L-18 -47 Z" fill={fill} />
    {[0, 1, 2, 3].map((i) => (
      <rect key={i} x={-15} y={-76 + i * 8} width={30} height={2} fill={shade} opacity={0.6} />
    ))}
    <path d="M-21 -78 L-15 -79 L-17 -46 L-24 -48 Z" fill={shade} />
    <path d="M21 -78 L15 -79 L17 -46 L24 -48 Z" fill={shade} />
    <rect x={-4} y={-86} width={8} height={7} fill={shade} />
    <ellipse cx={0} cy={-93} rx={8} ry={9} fill={fill} />
    {variant % 2 === 0 ? <circle cx={4} cy={-103} r={4.5} fill={shade} /> : <rect x={-7} y={-106} width={14} height={6} rx={2} fill={shade} />}
  </g>
);

// 中式亭子（攒尖）
export const Pavilion: React.FC<{ cx: number; baseY: number; s: number; color: string }> = ({ cx, baseY, s, color }) => (
  <g>
    <rect x={cx - 90 * s} y={baseY - 14 * s} width={180 * s} height={14 * s} fill={color} />
    {[-70, -24, 24, 70].map((dx) => (
      <rect key={dx} x={cx + dx * s - 5 * s} y={baseY - 100 * s} width={10 * s} height={88 * s} fill={color} />
    ))}
    <rect x={cx - 80 * s} y={baseY - 52 * s} width={160 * s} height={5 * s} fill={color} />
    <path d={roofPath(cx, baseY - 100 * s, 100 * s, 90 * s, 26 * s, 0)} fill={color} />
    <circle cx={cx} cy={baseY - 196 * s} r={6 * s} fill={color} />
  </g>
);

export const Willow: React.FC<{ x: number; y: number; color: string; frame: number; seed: number }> = ({ x, y, color, frame, seed }) => {
  const r = rng(seed);
  return (
    <g>
      <path d={`M${x - 40},${y - 40} Q${x + 80},${y - 10} ${x + 340},${y + 30}`} stroke={color} strokeWidth={14} fill="none" />
      {Array.from({ length: 26 }, (_, i) => {
        const bx = x + i * 13 + r() * 8, by = y - 30 + i * 2.4, len = 140 + r() * 220;
        const sway = Math.sin(frame / 30 + i * 0.5) * 14;
        return (
          <path key={i} d={`M${bx},${by} Q${bx + sway * 0.4},${by + len * 0.5} ${bx + sway},${by + len}`}
            stroke={color} strokeWidth={2.4} fill="none" opacity={0.9} />
        );
      })}
    </g>
  );
};

export const Vignette: React.FC<{ id: string; strength?: number }> = ({ id, strength = 0.55 }) => (
  <>
    <defs>
      <radialGradient id={id} cx="0.5" cy="0.5" r="0.75">
        <stop offset="0.55" stopColor="#000" stopOpacity={0} />
        <stop offset="1" stopColor="#000" stopOpacity={strength} />
      </radialGradient>
    </defs>
    <rect x={0} y={0} width={W} height={H} fill={`url(#${id})`} />
  </>
);
