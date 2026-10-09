import React from "react";
import {
  BellTower, Birds, CityWall, Glow, H, Mist, Pagoda, Pavilion, Ridge, Skyline, Sky, Stars, Sun,
  Vignette, W, Warrior, Willow, rng,
} from "./primitives";

// 每个镜头一幅分层剪影插画。地标都放在画面中右侧，避开左下角的信息卡片。
// p = 本镜头内的进度 0→1，f = 本镜头内的帧号；各图层按不同速度平移形成视差。
type P = { f: number; p: number };

const Dawn: React.FC<P> = ({ f, p }) => (
  <>
    <Sky id="dawn" stops={[[0, "#1b2442"], [0.45, "#6b4a6e"], [0.72, "#d9825f"], [0.86, "#f4c27c"]]} />
    <Sun id="dawn-sun" cx={1420} cy={800 - p * 90} r={46} color="#ffe2a8" glow="#ffb46b" />
    <Ridge seed={3} baseY={780} amp={150} color="#5d4566" opacity={0.8} shift={f * 0.3} />
    <Mist id="dawn-m1" y={760} h={90} color="#f2b48a" opacity={0.45} shift={f * 0.8} />
    <Skyline seed={11} baseY={880} minH={40} maxH={170} color="#3a2b45" shift={f * 0.5} />
    <Pagoda cx={1180 + f * 0.5} baseY={880} s={0.42} color="#3a2b45" window="#3a2b45" />
    <BellTower cx={1640 + f * 0.5} baseY={890} s={0.34} color="#3a2b45" accent="#ffcf8a" />
    <Mist id="dawn-m2" y={900} h={110} color="#c98a7a" opacity={0.55} shift={f * 1.4} />
    <Skyline seed={12} baseY={1080} minH={60} maxH={200} color="#21182b" shift={f * 1.1} />
    <Birds seed={5} count={6} frame={f} y={420} color="#2a1f33" />
  </>
);

const Panorama: React.FC<P> = ({ f }) => (
  <>
    <Sky id="pan" stops={[[0, "#26365e"], [0.5, "#8c6a7a"], [0.8, "#eaa260"], [1, "#f6c98a"]]} />
    <Glow id="pan-g" cx={1500} cy={720} r={700} color="#ffcf8a" opacity={0.6} />
    <Skyline seed={21} baseY={760} minH={60} maxH={260} color="#8a6a80" shift={f * 0.25} spires />
    <Skyline seed={22} baseY={860} minH={50} maxH={320} color="#5a4566" shift={f * 0.55} spires />
    <Pagoda cx={1460 + f * 0.55} baseY={860} s={0.6} color="#5a4566" window="#5a4566" />
    <Mist id="pan-m" y={860} h={100} color="#f0b080" opacity={0.4} shift={f * 1.2} />
    <Skyline seed={23} baseY={1000} minH={80} maxH={380} color="#2c2238" shift={f * 1.0} />
    <Skyline seed={24} baseY={1120} minH={60} maxH={180} color="#1a1422" shift={f * 1.6} />
  </>
);

const Wall: React.FC<P> = ({ f }) => {
  const lanterns = Array.from({ length: 14 }, (_, i) => -100 + i * 160 + f * 0.9);
  return (
    <>
      <Sky id="wall" stops={[[0, "#2b2f5a"], [0.5, "#a35f6d"], [0.8, "#f09a6a"]]} />
      <Sun id="wall-sun" cx={1550} cy={560} r={40} color="#ffd9a0" glow="#ff9b6a" />
      <Skyline seed={31} baseY={640} minH={30} maxH={150} color="#7a4e66" shift={f * 0.3} />
      <g transform={`translate(${f * 0.9 - 40},0)`}>
        <CityWall baseY={H + 20} top={660} color="#3b2a2e" dark="#24181b" gateX={1400} s={1.1} />
      </g>
      {lanterns.map((x, i) => (
        <g key={i}>
          <Glow id={`lan-${i}`} cx={x} cy={720} r={40} color="#ff7a3c" opacity={0.7} />
          <ellipse cx={x} cy={720} rx={10} ry={13} fill="#ff5a2a" />
        </g>
      ))}
    </>
  );
};

const GooseP: React.FC<P> = ({ f, p }) => (
  <>
    <Sky id="goose" stops={[[0, "#173a4a"], [0.55, "#6f8a8a"], [0.85, "#f0c48e"]]} />
    <Sun id="goose-sun" cx={1420} cy={560 + p * 30} r={52} color="#fff0c8" glow="#ffd08a" />
    <Ridge seed={41} baseY={900} amp={80} color="#4f6460" opacity={0.7} shift={f * 0.4} />
    <Pagoda cx={1420} baseY={960} s={1.05} color="#1e2a2c" window="#ffd08a" />
    <Ridge seed={42} baseY={1040} amp={90} freq={3} color="#141d1f" shift={f * 1.2} />
    <Birds seed={44} count={5} frame={f} y={300} color="#1e2a2c" />
  </>
);

const Terracotta: React.FC<P> = ({ f }) => {
  const rows: React.ReactNode[] = [];
  const r = rng(51);
  for (let row = 0; row < 9; row++) {
    const t = row / 8;
    const y = 470 + Math.pow(t, 1.5) * 640, s = 0.5 + t * 1.9, gap = 62 * s;
    const fade = 0.35 + 0.65 * t;
    const fill = `rgb(${Math.round(70 + 100 * fade)},${Math.round(45 + 62 * fade)},${Math.round(30 + 42 * fade)})`;
    const shade = `rgb(${Math.round(40 + 60 * fade)},${Math.round(26 + 36 * fade)},${Math.round(18 + 22 * fade)})`;
    const off = (row % 2) * gap * 0.5 + f * (0.2 + t * 0.6);
    if (row % 3 === 0) {
      rows.push(<rect key={`wall${row}`} x={0} y={y - 120 * s} width={W} height={30 * s} fill={shade} opacity={0.8} />);
    }
    for (let x = -gap + (off % gap); x < W + gap; x += gap) {
      rows.push(<Warrior key={`${row}-${x}`} x={x} y={y} s={s} fill={fill} shade={shade} variant={Math.floor(r() * 4)} />);
    }
  }
  const dust = rng(52);
  return (
    <>
      <Sky id="pit" stops={[[0, "#1a120c"], [0.4, "#3b2a1c"], [1, "#2a1d14"]]} />
      <Glow id="pit-l1" cx={1400} cy={300} r={700} color="#ffcf9a" opacity={0.35} />
      <Glow id="pit-l2" cx={500} cy={200} r={500} color="#ffcf9a" opacity={0.18} />
      {rows}
      {Array.from({ length: 50 }, (_, i) => {
        const x = dust() * W, y = (dust() * H + f * (0.3 + dust())) % H;
        return <circle key={i} cx={x} cy={y} r={1 + dust() * 2} fill="#ffe0b0" opacity={0.25} />;
      })}
    </>
  );
};

const Lishan: React.FC<P> = ({ f }) => (
  <>
    <Sky id="li" stops={[[0, "#8fa3b0"], [0.6, "#e6d2b4"], [1, "#f3e3c6"]]} />
    <Sun id="li-sun" cx={1500} cy={330} r={38} color="#fff6e0" glow="#ffe6b8" />
    <Ridge seed={61} baseY={560} amp={220} color="#a9b4b0" shift={f * 0.2} />
    <Mist id="li-m1" y={560} h={120} color="#f4ebdc" opacity={0.75} shift={f * 0.7} />
    <Ridge seed={62} baseY={720} amp={240} color="#7f908a" shift={f * 0.45} />
    <Pavilion cx={1460 + f * 0.45} baseY={560} s={0.55} color="#5f6f69" />
    <Mist id="li-m2" y={740} h={140} color="#efe4d2" opacity={0.7} shift={f * 1.1} />
    <Ridge seed={63} baseY={930} amp={220} color="#55655f" shift={f * 0.8} />
    <Mist id="li-m3" y={960} h={150} color="#e9dccb" opacity={0.6} shift={f * 1.6} />
    <Ridge seed={64} baseY={1120} amp={160} freq={2} color="#33403b" shift={f * 1.3} />
  </>
);

const Qujiang: React.FC<P> = ({ f }) => {
  const horizon = 610;
  const scene = (
    <>
      <Skyline seed={71} baseY={horizon} minH={20} maxH={120} color="#4c4a72" shift={f * 0.3} />
      <path d={`M-100,${horizon} L2020,${horizon} L2020,${horizon - 40} Q1700,${horizon - 70} 1300,${horizon - 30} L-100,${horizon - 20} Z`} fill="#2e2c4c" />
      <Pavilion cx={1430} baseY={horizon - 30} s={1.15} color="#2e2c4c" />
    </>
  );
  return (
    <>
      <Sky id="qj" stops={[[0, "#2a2f5e"], [0.4, "#8a6c9a"], [0.56, "#f1a98a"], [0.565, "#2b3058"], [1, "#151832"]]} />
      <Glow id="qj-g" cx={1250} cy={horizon} r={600} color="#ffb48a" opacity={0.45} />
      {scene}
      <g transform={`translate(0,${horizon * 2}) scale(1,-1)`} opacity={0.32}>{scene}</g>
      {Array.from({ length: 18 }, (_, i) => {
        const y = horizon + 20 + i * i * 1.4, w = 80 + i * 12;
        const x = ((i * 397 + f * (0.6 + i * 0.08)) % 2200) - 140;
        return <rect key={i} x={x} y={y} width={w} height={2} fill="#ffd2b0" opacity={0.25 + (i % 3) * 0.08} />;
      })}
      <g transform="translate(-40,-80)">
        <Willow x={0} y={60} color="#141530" frame={f} seed={73} />
      </g>
    </>
  );
};

const Qinling: React.FC<P> = ({ f }) => (
  <>
    <Sky id="ql" stops={[[0, "#2f5470"], [0.6, "#a9c3cc"], [1, "#e6ecdf"]]} />
    <Ridge seed={81} baseY={560} amp={300} freq={0.8} color="#7d97a6" shift={f * 0.15} />
    <Ridge seed={82} baseY={660} amp={260} freq={0.9} color="#5e7a88" shift={f * 0.35} />
    <Mist id="ql-m" y={660} h={130} color="#dfe8e6" opacity={0.65} shift={f * 0.9} />
    <Ridge seed={83} baseY={800} amp={200} color="#3f5a63" shift={f * 0.6} />
    <path fill="#c9dbe0" opacity={0.9}
      d="M880,780 C1000,800 1300,810 1250,850 C1180,900 700,920 820,980 C930,1040 1500,1040 1700,1120 L700,1120 C420,1060 380,980 600,930 C820,880 1040,860 960,820 C930,805 870,795 880,780 Z" />
    <Ridge seed={84} baseY={1120} amp={150} freq={2.5} color="#25363b" shift={f * 1.1} />
  </>
);

const HiTech: React.FC<P> = ({ f }) => (
  <>
    <Sky id="ht" stops={[[0, "#2f6fb4"], [0.6, "#8fc0e6"], [1, "#d6ebf7"]]} />
    {[0, 1, 2].map((i) => (
      <Mist key={i} id={`ht-c${i}`} y={180 + i * 120} h={70} color="#ffffff" opacity={0.55} shift={f * (0.5 + i * 0.3) + i * 500} />
    ))}
    <Skyline seed={91} baseY={900} minH={150} maxH={480} color="#7d9bb8" shift={f * 0.35} spires />
    <Skyline seed={92} baseY={1000} minH={220} maxH={640} color="#3e5a78" shift={f * 0.75} spires windows="#cfe6ff" litRatio={0.25} frame={f} />
    <defs>
      <linearGradient id="ht-sweep" x1="0" x2="1">
        <stop offset="0" stopColor="#fff" stopOpacity={0} />
        <stop offset="0.5" stopColor="#fff" stopOpacity={0.22} />
        <stop offset="1" stopColor="#fff" stopOpacity={0} />
      </linearGradient>
    </defs>
    <rect x={-600 + f * 14} y={-200} width={420} height={1600} fill="url(#ht-sweep)" transform="rotate(18 960 540)" />
    <Skyline seed={93} baseY={1100} minH={60} maxH={160} color="#1f3248" shift={f * 1.3} />
  </>
);

const trail = (d: string, color: string, f: number, speed: number, key: string) => (
  <path key={key} d={d} fill="none" stroke={color} strokeWidth={5} strokeLinecap="round"
    strokeDasharray="60 140" strokeDashoffset={-f * speed} opacity={0.85} />
);

const BellNight: React.FC<P> = ({ f }) => (
  <>
    <Sky id="bn" stops={[[0, "#070b22"], [0.6, "#1d1d4a"], [1, "#3a2450"]]} />
    <Stars seed={101} count={140} maxY={620} frame={f} />
    <Glow id="bn-g" cx={1400} cy={640} r={560} color="#ffb45a" opacity={0.45} />
    <Skyline seed={102} baseY={930} minH={80} maxH={300} color="#1a1734" shift={f * 0.4} windows="#ffcf7a" frame={f} />
    <BellTower cx={1400} baseY={940} s={1.25} color="#2a1c24" accent="#ffc35c" lit />
    <rect x={0} y={930} width={W} height={160} fill="#120f22" />
    {trail("M-100,1060 C500,980 1000,960 2100,1000", "#ff5a4a", f, 9, "t1")}
    {trail("M-100,1000 C600,960 1200,950 2100,970", "#fff1c8", f, -7, "t2")}
    {trail("M-100,1040 C700,1000 1300,990 2100,1030", "#ffb04a", f, 6, "t3")}
  </>
);

const NightEnd: React.FC<P> = ({ f }) => (
  <>
    <Sky id="ne" stops={[[0, "#050819"], [0.65, "#151a44"], [1, "#2f2552"]]} />
    <Stars seed={111} count={200} maxY={700} frame={f} />
    <circle cx={1580} cy={220} r={44} fill="#f6f0dc" />
    <Glow id="ne-moon" cx={1580} cy={220} r={220} color="#f6f0dc" opacity={0.25} />
    <Glow id="ne-city" cx={1100} cy={1000} r={900} color="#ff9a4a" opacity={0.35} />
    <Skyline seed={112} baseY={860} minH={60} maxH={260} color="#1c1a3a" windows="#ffd38a" frame={f} litRatio={0.3} spires />
    <Pagoda cx={1180} baseY={860} s={0.55} color="#1c1a3a" window="#ffc35c" />
    <BellTower cx={1560} baseY={880} s={0.5} color="#1c1a3a" accent="#ffc35c" lit />
    <Skyline seed={113} baseY={1100} minH={80} maxH={240} color="#100e24" windows="#ffbf6a" frame={f} litRatio={0.4} />
  </>
);

export const ART: Record<string, React.FC<P>> = {
  dawn: Dawn,
  panorama: Panorama,
  wall: Wall,
  pagoda: GooseP,
  terracotta: Terracotta,
  lishan: Lishan,
  qujiang: Qujiang,
  qinling: Qinling,
  hitech: HiTech,
  bellNight: BellNight,
  nightEnd: NightEnd,
};

export const Illustration: React.FC<{ art: string; f: number; p: number }> = ({ art, f, p }) => {
  const Art = ART[art] ?? Dawn;
  return (
    <svg viewBox={`0 0 ${W} ${H}`} width="100%" height="100%" preserveAspectRatio="xMidYMid slice">
      <Art f={f} p={p} />
      <Vignette id={`vig-${art}`} />
    </svg>
  );
};
