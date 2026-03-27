/**
 * parser.js — ViralScout 2.0 Markdown Parser
 *
 * Parses the ViralScout .md report format into structured JSON.
 *
 * Input format:
 *   # ViralScout 2.0 — Reporte de Investigación
 *   **Keywords:** kw1, kw2
 *   **Preset:** eric
 *   **Fecha:** 2026-03-22T16:42:34
 *
 *   ## 💡 Ideas de Video (N)
 *   ### Idea 1: Título del Video
 *   **Hook:** texto...
 *   **Estructura:** ...
 *   **Retención estimada:** 72-78%
 *   **Miniatura:** descripción
 *   **Guion:**
 *   ```
 *   [0-5s] Narración
 *   VISUAL: Descripción
 *   ```
 *
 * Usage (standalone test):
 *   node parser.js path/to/file.md
 */

const fs = require("fs");

// ---------------------------------------------------------------------------
// Extract header metadata
// ---------------------------------------------------------------------------
function extractHeader(content) {
  const keywords = (content.match(/\*\*Keywords:\*\*\s*(.+)/)?.[1] || "")
    .split(",")
    .map((k) => k.trim())
    .filter(Boolean);

  const preset = content.match(/\*\*Preset:\*\*\s*(.+)/)?.[1]?.trim() || "";
  const fecha = content.match(/\*\*Fecha:\*\*\s*(.+)/)?.[1]?.trim() || "";

  return { keywords, preset, fecha };
}

// ---------------------------------------------------------------------------
// Parse scenes from a script block (the content inside ```)
// ---------------------------------------------------------------------------
function parseScenes(scriptContent) {
  const scenes = [];
  // Match patterns like [0-5s], **[0-5s]**, **[0-5s]**\n etc.
  // Strips optional markdown bold markers around timestamps
  const sceneRegex =
    /\*{0,2}\[(\d+)(?:-(\d+))?s\]\*{0,2}\s*([\s\S]+?)(?=\n\*{0,2}\[|\n```|$)/g;

  let match;
  while ((match = sceneRegex.exec(scriptContent)) !== null) {
    const start = parseInt(match[1], 10);
    const end = match[2] ? parseInt(match[2], 10) : start + 5;
    const block = match[3].trim();

    // Split narration from VISUAL line (supports VISUAL: and **VISUAL:**)
    const visualMatch = block.match(/^([\s\S]+?)\n\*{0,2}VISUAL:\*{0,2}\s*(.+?)$/m);
    let narration = block;
    let visual = "";

    if (visualMatch) {
      narration = visualMatch[1].trim();
      visual = visualMatch[2].replace(/\*{1,2}/g, "").replace(/`/g, "").trim();
    } else {
      // VISUAL might be missing — use narration as visual description fallback
      narration = block.replace(/\*{0,2}VISUAL:\*{0,2}.*$/m, "").trim();
      const visualLine = block.match(/\*{0,2}VISUAL:\*{0,2}\s*(.+)/)?.[1]?.trim();
      visual = visualLine || "";
    }

    // Clean narration: remove VISUAL lines, markdown separators, title, section labels
    narration = narration.replace(/\*{0,2}VISUAL:\*{0,2}.*$/gm, "").trim();
    narration = narration.replace(/^---$/gm, "").trim();
    narration = narration.replace(/^#\s+.+$/gm, "").trim();
    // Remove section labels: HOOK:, DESARROLLO N:, CLÍMAX:, CLIMAX:, LOOP:, CIERRE:
    narration = narration.replace(/^(?:HOOK|DESARROLLO\s*\d*|CL[IÍ]MAX|LOOP|CIERRE)\s*:\s*/im, "").trim();
    // Strip any remaining markdown bold/italic markers
    narration = narration.replace(/\*{1,2}/g, "").trim();

    if (narration) {
      scenes.push({
        start,
        end,
        duration: end - start,
        narration,
        visual: visual || narration,
      });
    }
  }

  // Sort scenes chronologically
  scenes.sort((a, b) => a.start - b.start);

  return scenes;
}

// ---------------------------------------------------------------------------
// Extract fenced code block content (```)
// ---------------------------------------------------------------------------
function extractCodeBlock(text) {
  const match = text.match(/```[\w]*\n?([\s\S]+?)```/);
  return match ? match[1] : null;
}

// ---------------------------------------------------------------------------
// Parse a single idea block
// ---------------------------------------------------------------------------
function parseIdea(ideaBlock, index) {
  // Title from the ### Idea N: line
  const titleMatch = ideaBlock.match(/###\s+Idea\s+\d+:\s*(.+)/);
  const title = titleMatch ? titleMatch[1].trim() : `Idea ${index + 1}`;

  const hook = ideaBlock.match(/\*\*Hook:\*\*\s*(.+)/)?.[1]?.trim() || "";
  const estructura =
    ideaBlock.match(/\*\*Estructura:\*\*\s*([\s\S]+?)(?=\*\*Retención|\*\*Miniatura|\*\*Guion)/)?.[1]?.trim() || "";
  const retentionEstimate =
    ideaBlock.match(/\*\*Retención estimada:\*\*\s*(.+)/)?.[1]?.trim() || "";
  const thumbnail =
    ideaBlock.match(/\*\*Miniatura:\*\*\s*([\s\S]+?)(?=\*\*Guion|```)/)?.[1]?.trim() || "";

  // Extract script from fenced code block after **Guion:**
  const guionSection = ideaBlock.match(/\*\*Guion:\*\*\s*([\s\S]+)/)?.[1] || "";
  const scriptContent = extractCodeBlock(guionSection);

  if (!scriptContent) {
    return null;
  }

  const scenes = parseScenes(scriptContent);

  if (scenes.length === 0) {
    return null;
  }

  // Build full narration text
  const fullNarration = scenes.map((s) => s.narration).join(" ");

  // Total duration = last scene end time
  const duration = scenes[scenes.length - 1]?.end || 60;

  return {
    title,
    hook,
    estructura,
    retentionEstimate,
    thumbnail,
    duration,
    scenes,
    fullNarration,
  };
}

// ---------------------------------------------------------------------------
// Parse a standalone script file (just [0-5s] lines, no ViralScout wrapper)
// ---------------------------------------------------------------------------
function parseStandaloneScript(content, filename) {
  // Strip verification/metadata section at the end (## ✅ VERIFICACIÓN, ## VERIFICACIÓN, etc.)
  const cleanContent = content.replace(/\n##\s+.*VERIFICACI[OÓ]N[\s\S]*$/i, "");
  const scenes = parseScenes(cleanContent);

  if (scenes.length === 0) {
    throw new Error("No scenes found in standalone script");
  }

  // Try to extract title from "# GUION: Title" header
  const guionTitle = content.match(/^#\s+(?:🎬\s+)?(?:GUION|GUIÓN):\s*(.+)/im)?.[1]?.trim();

  // Fallback: derive title from filename
  const rawTitle = guionTitle || filename
    .replace(/\.md$/i, "")
    .replace(/_+/g, " ")
    .trim();

  // Try to extract tone from content (e.g. keywords in filename or content)
  const toneMatch = content.match(/\*{0,2}Tono?:\*{0,2}\s*(.+)/i)?.[1]?.trim() || "";

  // Use first scene narration as hook
  const hook = scenes[0]?.narration || "";
  const fullNarration = scenes.map((s) => s.narration).join(" ");
  const duration = scenes[scenes.length - 1]?.end || 60;

  return {
    title: rawTitle.length > 100 ? rawTitle.substring(0, 97) + "..." : rawTitle,
    hook,
    tone: toneMatch,
    estructura: "",
    retentionEstimate: "",
    thumbnail: "",
    duration,
    scenes,
    fullNarration,
  };
}

// ---------------------------------------------------------------------------
// Detect if content is a standalone script (has [Ns] timestamp patterns)
// ---------------------------------------------------------------------------
function isStandaloneScript(content) {
  const trimmed = content.trim();
  // Direct start: [0-5s] or **[0-5s]**
  if (/^\[\d+(-\d+)?s\]/.test(trimmed) || /^\*{2}\[\d+(-\d+)?s\]/.test(trimmed)) {
    return true;
  }
  // "# GUION:" or "# 🎬 GUION:" header format — has timestamps inside but starts with title
  if (/^#\s+(?:🎬\s+)?(?:GUION|GUIÓN)/i.test(trimmed) && /\*{0,2}\[\d+(-\d+)?s\]/.test(content)) {
    return true;
  }
  return false;
}

// ---------------------------------------------------------------------------
// Main parser function
// ---------------------------------------------------------------------------
function parseViralScoutFile(content, filename) {
  // Handle standalone scripts (just [0-5s] narration + VISUAL lines)
  if (isStandaloneScript(content)) {
    const idea = parseStandaloneScript(content, filename);
    return {
      sourceFile: filename,
      preset: "",
      keywords: [],
      fecha: new Date().toISOString(),
      ideas: [idea],
    };
  }

  const header = extractHeader(content);

  // Find the "Ideas de Video" section
  const ideasSectionMatch = content.match(
    /## 💡 Ideas de Video[\s\S]+/
  );
  if (!ideasSectionMatch) {
    throw new Error("No '## 💡 Ideas de Video' section found");
  }

  const ideasSection = ideasSectionMatch[0];

  // Split into individual idea blocks by "### Idea N:"
  const ideaBlocks = ideasSection
    .split(/(?=###\s+Idea\s+\d+:)/)
    .filter((block) => /###\s+Idea\s+\d+:/.test(block));

  if (ideaBlocks.length === 0) {
    throw new Error("No idea blocks found in ideas section");
  }

  const ideas = ideaBlocks
    .map((block, i) => parseIdea(block, i))
    .filter(Boolean);

  if (ideas.length === 0) {
    throw new Error("All ideas failed to parse");
  }

  return {
    sourceFile: filename,
    preset: header.preset,
    keywords: header.keywords,
    fecha: header.fecha,
    ideas,
  };
}

module.exports = { parseViralScoutFile };

// ---------------------------------------------------------------------------
// Standalone CLI test: node parser.js <file.md>
// ---------------------------------------------------------------------------
if (require.main === module) {
  const filePath = process.argv[2];
  if (!filePath) {
    console.error("Usage: node parser.js <path-to-viralscout.md>");
    process.exit(1);
  }

  const content = fs.readFileSync(filePath, "utf-8");
  const result = parseViralScoutFile(content, require("path").basename(filePath));

  console.log(JSON.stringify(result, null, 2));
  console.log(`\n✅ Parsed ${result.ideas.length} ideas`);
  result.ideas.forEach((idea, i) => {
    console.log(`   Idea ${i + 1}: "${idea.title}" — ${idea.scenes.length} scenes, ${idea.duration}s`);
  });
}
