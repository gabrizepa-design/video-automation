import { Composition } from "remotion";
import { VideoComposition } from "./Video";
import type { VideoConfig } from "./types";

// Default config for Remotion Studio preview
const defaultConfig: VideoConfig = {
  title: "Preview",
  scenes: [],
  audioPath: "",
  subtitles: [],
  outputPath: "/tmp/preview.mp4",
  fps: 30,
  width: 1080,
  height: 1920,
};

export const RemotionRoot: React.FC = () => {
  return (
    <Composition
      id="VideoShort"
      component={VideoComposition}
      durationInFrames={60 * 30} // 60s × 30fps = 1800 frames
      fps={30}
      width={1080}
      height={1920}
      defaultProps={defaultConfig}
    />
  );
};
