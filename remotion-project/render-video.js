/**
 * render-video.js — CLI wrapper for manual renders
 *
 * Usage:
 *   node render-video.js --config /tmp/video-config.json
 *   node render-video.js --config /tmp/video-config.json --output /tmp/out.mp4
 */

const path = require("path");
const fs = require("fs");
const { bundle } = require("@remotion/bundler");
const { renderMedia, selectComposition } = require("@remotion/renderer");

async function main() {
  const args = process.argv.slice(2);
  const configIdx = args.indexOf("--config");
  const outputIdx = args.indexOf("--output");

  if (configIdx === -1 || !args[configIdx + 1]) {
    console.error("Usage: node render-video.js --config <path> [--output <path>]");
    process.exit(1);
  }

  const configPath = args[configIdx + 1];
  const config = JSON.parse(fs.readFileSync(configPath, "utf-8"));

  if (outputIdx !== -1 && args[outputIdx + 1]) {
    config.outputPath = args[outputIdx + 1];
  }

  if (!config.outputPath) {
    config.outputPath = `/tmp/videos/final/video_${Date.now()}.mp4`;
  }

  console.log(`Rendering: "${config.title}"`);
  console.log(`Output: ${config.outputPath}`);
  console.log(`Scenes: ${config.scenes.length}`);

  const CHROME = process.env.REMOTION_CHROME_EXECUTABLE || "/usr/bin/chromium";
  const CONCURRENCY = parseInt(process.env.REMOTION_CONCURRENCY || "4", 10);

  const bundledPath = await bundle({
    entryPoint: path.resolve(__dirname, "src/index.ts"),
    webpackOverride: (config) => config,
  });

  const composition = await selectComposition({
    serveUrl: bundledPath,
    id: "VideoShort",
    inputProps: config,
  });

  const start = Date.now();

  await renderMedia({
    composition,
    serveUrl: bundledPath,
    codec: "h264",
    outputLocation: config.outputPath,
    inputProps: config,
    concurrency: CONCURRENCY,
    chromiumOptions: {
      executablePath: CHROME,
      openGlRenderer: "swangle",
    },
    onProgress: ({ progress }) => {
      process.stdout.write(`\rProgress: ${Math.round(progress * 100)}%`);
    },
  });

  const elapsed = ((Date.now() - start) / 1000).toFixed(1);
  console.log(`\nDone in ${elapsed}s → ${config.outputPath}`);
}

main().catch((err) => {
  console.error("Render failed:", err.message);
  process.exit(1);
});
