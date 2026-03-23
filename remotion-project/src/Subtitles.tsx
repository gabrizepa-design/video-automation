import React from "react";
import { AbsoluteFill, useCurrentFrame, useVideoConfig } from "remotion";
import type { SubtitleWord } from "./types";

interface SubtitlesProps {
  subtitles: SubtitleWord[];
}

export const SubtitlesOverlay: React.FC<SubtitlesProps> = ({ subtitles }) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();

  const currentTime = frame / fps;

  // Find current word index
  const activeIndex = subtitles.findIndex(
    (w) => currentTime >= w.start && currentTime <= w.end
  );

  if (activeIndex === -1) return null;

  // Show a window of words around the active word (for context)
  const windowStart = Math.max(0, activeIndex - 2);
  const windowEnd = Math.min(subtitles.length - 1, activeIndex + 2);
  const visibleWords = subtitles.slice(windowStart, windowEnd + 1);

  return (
    <AbsoluteFill
      style={{
        justifyContent: "flex-end",
        alignItems: "center",
        paddingBottom: 120,
      }}
    >
      <div
        style={{
          display: "flex",
          flexWrap: "wrap",
          justifyContent: "center",
          alignItems: "center",
          gap: 8,
          maxWidth: "90%",
          paddingHorizontal: 20,
        }}
      >
        {visibleWords.map((word, i) => {
          const globalIndex = windowStart + i;
          const isActive = globalIndex === activeIndex;

          return (
            <span
              key={globalIndex}
              style={{
                fontFamily: "'Montserrat', 'Arial Black', sans-serif",
                fontWeight: 900,
                fontSize: isActive ? 64 : 52,
                color: isActive ? "#FFD700" : "#FFFFFF",
                textShadow: "3px 3px 6px rgba(0,0,0,0.9), -1px -1px 3px rgba(0,0,0,0.9)",
                transform: isActive ? "scale(1.1)" : "scale(1)",
                transition: "all 0.05s ease",
                letterSpacing: "0.5px",
                lineHeight: 1.2,
                display: "inline-block",
                textTransform: "uppercase",
              }}
            >
              {word.word}
            </span>
          );
        })}
      </div>
    </AbsoluteFill>
  );
};
