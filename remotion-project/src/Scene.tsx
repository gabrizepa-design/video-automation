import React from "react";
import { AbsoluteFill, OffthreadVideo, useCurrentFrame, useVideoConfig } from "remotion";
import { TransitionOverlay } from "./Transition";
import type { SceneData } from "./types";

interface SceneProps {
  scene: SceneData;
  nextScene: SceneData | null;
  fps: number;
}

export const SceneComponent: React.FC<SceneProps> = ({ scene, nextScene, fps }) => {
  const frame = useCurrentFrame();
  const { durationInFrames } = useVideoConfig();

  // Transition duration in frames (last 15 frames of the scene)
  const TRANSITION_FRAMES = 15;
  const transitionType = nextScene?.transition || scene.transition || "fade";

  // Show transition overlay near the end of the scene
  const showTransition =
    transitionType !== "cut" &&
    nextScene !== null &&
    frame >= durationInFrames - TRANSITION_FRAMES;

  const transitionProgress = showTransition
    ? (frame - (durationInFrames - TRANSITION_FRAMES)) / TRANSITION_FRAMES
    : 0;

  return (
    <AbsoluteFill>
      {/* Scene video — covers full 1080x1920 frame */}
      <OffthreadVideo
        src={scene.videoPath}
        style={{
          width: "100%",
          height: "100%",
          objectFit: "cover",
        }}
      />

      {/* Transition overlay at scene boundary */}
      {showTransition && (
        <TransitionOverlay
          type={transitionType}
          progress={transitionProgress}
        />
      )}
    </AbsoluteFill>
  );
};
