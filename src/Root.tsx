import React from "react";
import { Composition } from "remotion";
import { XianPromo } from "./XianPromo";
import { timeline, totalFrames } from "./data";

export const RemotionRoot: React.FC = () => (
  <Composition
    id="XianPromo"
    component={XianPromo}
    durationInFrames={totalFrames}
    fps={timeline.fps}
    width={timeline.width}
    height={timeline.height}
  />
);
