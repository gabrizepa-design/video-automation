import React from "react";
import { AbsoluteFill, Audio, Sequence, useVideoConfig } from "remotion";
import { SceneComponent } from "./Scene";
import { SubtitlesOverlay } from "./Subtitles";
import type { VideoConfig } from "./types";

export const VideoComposition: React.FC<VideoConfig> = (config) => {
  const { fps } = useVideoConfig();
  const { scenes, audioPath, audioUrl, bgMusicPath, bgMusicUrl, subtitles } = config;

  const audioSrc = audioPath || audioUrl || "";
  const bgMusicSrc = bgMusicPath || bgMusicUrl || "";

  return (
    <AbsoluteFill style={{ backgroundColor: "#000" }}>
      {scenes.map((scene, i) => {
        const fromFrame = Math.round(scene.start * fps);
        const durationFrames = Math.round(scene.duration * fps);
        const nextScene = scenes[i + 1];

        return (
          <Sequence
            key={scene.id}
            from={fromFrame}
            durationInFrames={durationFrames}
            name={`Scene ${scene.id}`}
          >
            <SceneComponent
              scene={scene}
              nextScene={nextScene || null}
              fps={fps}
            />
          </Sequence>
        );
      })}

      {audioSrc && <Audio src={audioSrc} />}
      {bgMusicSrc && <Audio src={bgMusicSrc} volume={0.12} loop />}

      {subtitles && subtitles.length > 0 && (
        <SubtitlesOverlay subtitles={subtitles} />
      )}
    </AbsoluteFill>
  );
};
