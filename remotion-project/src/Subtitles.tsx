import React from "react";
import { AbsoluteFill, useCurrentFrame, useVideoConfig } from "remotion";
import type { SubtitleWord } from "./types";

interface SubtitlesProps {
  subtitles: SubtitleWord[];
}

// Group words into chunks of ~6-8 words for readable display
function groupWords(subtitles: SubtitleWord[], wordsPerGroup = 7): { words: SubtitleWord[]; start: number; end: number }[] {
  const groups: { words: SubtitleWord[]; start: number; end: number }[] = [];
  for (let i = 0; i < subtitles.length; i += wordsPerGroup) {
    const chunk = subtitles.slice(i, i + wordsPerGroup);
    groups.push({
      words: chunk,
      start: chunk[0].start,
      end: chunk[chunk.length - 1].end,
    });
  }
  return groups;
}

export const SubtitlesOverlay: React.FC<SubtitlesProps> = ({ subtitles }) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();

  if (!subtitles || subtitles.length === 0) return null;

  const currentTime = frame / fps;
  const groups = groupWords(subtitles, 7);

  // Find current group
  const activeGroup = groups.find(
    (g) => currentTime >= g.start && currentTime <= g.end + 0.3
  );

  if (!activeGroup) return null;

  // Find active word within the group
  const activeWordIndex = activeGroup.words.findIndex(
    (w) => currentTime >= w.start && currentTime <= w.end
  );

  return (
    <AbsoluteFill
      style={{
        justifyContent: "flex-end",
        alignItems: "center",
        paddingBottom: 140,
      }}
    >
      <div
        style={{
          display: "flex",
          flexWrap: "wrap",
          justifyContent: "center",
          alignItems: "center",
          gap: 10,
          maxWidth: "85%",
          padding: "16px 24px",
          borderRadius: 12,
          backgroundColor: "rgba(0,0,0,0.5)",
        }}
      >
        {activeGroup.words.map((word, i) => {
          const isActive = i === activeWordIndex;

          return (
            <span
              key={`${word.start}-${i}`}
              style={{
                fontFamily: "'Montserrat', 'Arial Black', sans-serif",
                fontWeight: 900,
                fontSize: isActive ? 56 : 48,
                color: isActive ? "#FFD700" : "#FFFFFF",
                textShadow: "2px 2px 4px rgba(0,0,0,0.8)",
                transform: isActive ? "scale(1.05)" : "scale(1)",
                letterSpacing: "0.5px",
                lineHeight: 1.3,
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
