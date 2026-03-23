/**
 * render-server.js — HTTP API for Remotion renders
 *
 * Accepts VideoConfig with URLs for scenes and audio.
 * Downloads all assets to /tmp before rendering.
 */

const express = require("express");
const path = require("path");
const fs = require("fs");
const https = require("https");
const http = require("http");
const { bundle } = require("@remotion/bundler");
const { renderMedia, selectComposition } = require("@remotion/renderer");

const app = express();
app.use(express.json({ limit: "50mb" }));

const PORT = parseInt(process.env.REMOTION_PORT || "3001", 10);
const CONCURRENCY = parseInt(process.env.REMOTION_CONCURRENCY || "2", 10);
const TEMP_DIR = process.env.TEMP_VIDEOS_DIR || "/tmp/videos";
const CHROME_EXECUTABLE = process.env.REMOTION_CHROME_EXECUTABLE || "/usr/bin/chromium";

let bundledPath = null;

async function getBundle() {
  if (!bundledPath) {
    console.log("Bundling Remotion project (first render only)...");
    bundledPath = await bundle({
      entryPoint: path.resolve(__dirname, "src/index.ts"),
      webpackOverride: (config) => config,
    });
    console.log("Bundle complete:", bundledPath);
  }
  return bundledPath;
}

// Download a URL to a local file
function downloadFile(url, destPath) {
  return new Promise((resolve, reject) => {
    const dir = path.dirname(destPath);
    fs.mkdirSync(dir, { recursive: true });

    const proto = url.startsWith("https") ? https : http;
    const file = fs.createWriteStream(destPath);

    proto.get(url, (response) => {
      if (response.statusCode >= 300 && response.statusCode < 400 && response.headers.location) {
        // Follow redirect
        downloadFile(response.headers.location, destPath).then(resolve).catch(reject);
        return;
      }
      if (response.statusCode !== 200) {
        reject(new Error(`Download failed: ${response.statusCode} for ${url.substring(0, 80)}`));
        return;
      }
      response.pipe(file);
      file.on("finish", () => { file.close(); resolve(destPath); });
      file.on("error", (err) => { fs.unlink(destPath, () => {}); reject(err); });
    }).on("error", reject);
  });
}

// Convert video to Chromium-compatible format using FFmpeg
function convertVideo(inputPath, outputPath) {
  const { execSync } = require("child_process");
  return new Promise((resolve, reject) => {
    try {
      console.log(`[FFMPEG] Converting ${path.basename(inputPath)}...`);
      execSync(`ffmpeg -y -i "${inputPath}" -c:v libx264 -preset fast -crf 23 -c:a aac -movflags +faststart "${outputPath}"`, {
        timeout: 60000,
        stdio: "pipe"
      });
      resolve(outputPath);
    } catch (err) {
      reject(new Error(`FFmpeg conversion failed: ${err.message}`));
    }
  });
}

// Download all assets (scene videos + audio) to local temp files
async function downloadAssets(config, jobDir) {
  console.log(`[ASSETS] Downloading to ${jobDir}...`);

  // Download scene videos and convert to Chromium-compatible format
  for (let i = 0; i < config.scenes.length; i++) {
    const scene = config.scenes[i];
    const videoUrl = scene.videoPath;
    if (videoUrl && (videoUrl.startsWith("http://") || videoUrl.startsWith("https://"))) {
      const rawPath = path.join(jobDir, `scene_${i}_raw.mp4`);
      const convertedPath = path.join(jobDir, `scene_${i}.mp4`);
      console.log(`[ASSETS] Scene ${i}: downloading...`);
      await downloadFile(videoUrl, rawPath);
      await convertVideo(rawPath, convertedPath);
      fs.unlinkSync(rawPath); // Remove raw file
      scene.videoPath = convertedPath;
      console.log(`[ASSETS] Scene ${i}: ready at ${convertedPath}`);
    }
  }

  // Download audio
  if (config.audioUrl && (config.audioUrl.startsWith("http://") || config.audioUrl.startsWith("https://"))) {
    const audioPath = path.join(jobDir, "audio.mp3");
    console.log("[ASSETS] Audio: downloading...");
    await downloadFile(config.audioUrl, audioPath);
    config.audioPath = audioPath;
    console.log(`[ASSETS] Audio: saved to ${audioPath}`);
  }

  return config;
}

// POST /render
app.post("/render", async (req, res) => {
  const config = req.body;

  if (!config || !config.scenes || !Array.isArray(config.scenes) || config.scenes.length === 0) {
    return res.status(400).json({ error: "Invalid VideoConfig: scenes array required" });
  }

  const jobId = `job_${Date.now()}`;
  const jobDir = path.join(TEMP_DIR, jobId);
  fs.mkdirSync(jobDir, { recursive: true });

  if (!config.outputPath) {
    config.outputPath = path.join(jobDir, "final.mp4");
  }

  console.log(`[RENDER] Job ${jobId}: "${config.title}" — ${config.scenes.length} scenes`);
  const startTime = Date.now();

  try {
    // Download all remote assets
    await downloadAssets(config, jobDir);

    const bundlePath = await getBundle();

    // Calculate total duration from scenes
    const totalDuration = config.scenes.reduce((max, s) => Math.max(max, s.end || 0), 0);
    const fps = config.fps || 30;
    const totalFrames = Math.round(totalDuration * fps);

    const composition = await selectComposition({
      serveUrl: bundlePath,
      id: "VideoShort",
      inputProps: config,
    });

    // Override duration based on actual scene data
    composition.durationInFrames = totalFrames || composition.durationInFrames;

    await renderMedia({
      composition,
      serveUrl: bundlePath,
      codec: "h264",
      outputLocation: config.outputPath,
      inputProps: config,
      concurrency: CONCURRENCY,
      chromiumOptions: {
        executablePath: CHROME_EXECUTABLE,
        openGlRenderer: "swangle",
        disableWebSecurity: true,
      },
      onProgress: ({ progress }) => {
        const pct = Math.round(progress * 100);
        if (pct % 20 === 0) {
          console.log(`[RENDER] Job ${jobId}: ${pct}%`);
        }
      },
    });

    const elapsed = ((Date.now() - startTime) / 1000).toFixed(1);
    console.log(`[RENDER] Job ${jobId}: Complete in ${elapsed}s`);

    // Return the video file as binary response
    const videoBuffer = fs.readFileSync(config.outputPath);
    res.set({
      "Content-Type": "video/mp4",
      "Content-Disposition": `attachment; filename="${jobId}.mp4"`,
      "X-Render-Duration": elapsed,
    });
    res.send(videoBuffer);

    // Cleanup job directory after sending
    setTimeout(() => {
      fs.rmSync(jobDir, { recursive: true, force: true });
      console.log(`[CLEANUP] Job ${jobId} removed`);
    }, 5000);

  } catch (err) {
    console.error(`[RENDER] Job ${jobId} Error: ${err.message}`);
    // Cleanup on error too
    fs.rmSync(jobDir, { recursive: true, force: true });
    res.status(500).json({ error: err.message });
  }
});

// GET /health
app.get("/health", (_req, res) => {
  res.json({ status: "ok", service: "remotion-renderer" });
});

app.listen(PORT, () => {
  console.log(`Remotion render server on port ${PORT}`);
  console.log(`Concurrency: ${CONCURRENCY} | Chrome: ${CHROME_EXECUTABLE}`);
  getBundle().catch((err) => console.error("Pre-warm failed:", err.message));
});
