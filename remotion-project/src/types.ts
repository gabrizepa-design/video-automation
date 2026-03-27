export interface SceneData {
  id: number;
  videoPath: string;   // URL or local path to video
  start: number;       // seconds from video start
  end: number;         // seconds from video start
  duration: number;    // seconds (end - start)
  narration: string;
  visual: string;
  transition?: "fade" | "dissolve" | "wipe" | "cut";
}

export interface SubtitleWord {
  word: string;
  start: number;  // seconds
  end: number;    // seconds
}

export interface VideoConfig {
  title: string;
  scenes: SceneData[];
  audioUrl?: string;            // URL to audio file
  audioPath?: string;           // Local path to audio (legacy)
  subtitles: SubtitleWord[];
  outputPath: string;
  totalVideoDuration?: number;  // Total video length in seconds
  fps?: number;                 // Default: 30
  width?: number;               // Default: 1080
  height?: number;              // Default: 1920
}
