import React from "react";
import { AbsoluteFill, interpolate } from "remotion";

interface TransitionProps {
  type: "fade" | "dissolve" | "wipe" | "cut";
  progress: number; // 0 to 1
}

export const TransitionOverlay: React.FC<TransitionProps> = ({ type, progress }) => {
  if (type === "cut" || progress <= 0) return null;

  if (type === "fade" || type === "dissolve") {
    const opacity = interpolate(progress, [0, 1], [0, 1]);
    return (
      <AbsoluteFill
        style={{
          backgroundColor: "#000",
          opacity,
        }}
      />
    );
  }

  if (type === "wipe") {
    // Wipe from right to left
    const clipPercent = interpolate(progress, [0, 1], [100, 0]);
    return (
      <AbsoluteFill
        style={{
          backgroundColor: "#000",
          clipPath: `inset(0 0 0 ${clipPercent}%)`,
        }}
      />
    );
  }

  return null;
};
