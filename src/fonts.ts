import { continueRender, delayRender, staticFile } from "remotion";
import manifest from "./fonts.json";

// 字体由 scripts/fetch_fonts.py 下载到 public/fonts/，渲染时不依赖外网
// （国内网络常常访问不了 Google Fonts）。清单为空时回退到系统字体。
type Entry = { file: string; weight: string; unicodeRange?: string };

const families = { serif: "XianSerif", sans: "XianSans" } as const;

const load = (family: string, entries: Entry[]) => {
  if (typeof FontFace === "undefined" || entries.length === 0) return;
  const handle = delayRender(`加载字体 ${family}`);
  Promise.all(
    entries.map((e) => {
      const face = new FontFace(family, `url(${staticFile(e.file)})`, {
        weight: e.weight,
        ...(e.unicodeRange ? { unicodeRange: e.unicodeRange } : {}),
      });
      document.fonts.add(face);
      return face.load();
    }),
  )
    .catch((err) => console.error(`字体 ${family} 加载失败，改用系统字体`, err))
    .finally(() => continueRender(handle));
};

const m = manifest as Record<keyof typeof families, Entry[]>;
load(families.serif, m.serif ?? []);
load(families.sans, m.sans ?? []);

export const serif = `${families.serif}, "Source Han Serif SC", "Noto Serif CJK SC", "Songti SC", STSong, serif`;
export const sans = `${families.sans}, "Source Han Sans SC", "Noto Sans CJK SC", "PingFang SC", "Microsoft YaHei", sans-serif`;
