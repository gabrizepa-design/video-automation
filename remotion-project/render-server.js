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
const CACHE_DIR = path.join(TEMP_DIR, "cache");
const CHROME_EXECUTABLE = process.env.REMOTION_CHROME_EXECUTABLE || "/usr/bin/google-chrome-stable";

// Ensure cache dir exists
fs.mkdirSync(CACHE_DIR, { recursive: true });

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

// Re-encode video to Chromium-compatible H.264 baseline/yuv420p
function convertVideo(inputPath, outputPath) {
  const { execSync } = require("child_process");
  try {
    // Always re-encode: Runway videos have non-standard MP4 structure
    // that Chromium can't play even after remux
    console.log(`[FFMPEG] Re-encoding ${path.basename(inputPath)}...`);
    const stderr = execSync(
      `ffmpeg -y -i "${inputPath}" -c:v libx264 -profile:v baseline -level 3.1 -preset fast -crf 23 -pix_fmt yuv420p -an -movflags +faststart "${outputPath}"`,
      { timeout: 120000, stdio: ["pipe", "pipe", "pipe"] }
    );
    const stat = fs.statSync(outputPath);
    if (stat.size < 1000) {
      throw new Error(`Output too small: ${stat.size} bytes`);
    }
    console.log(`[FFMPEG] Re-encode OK: ${(stat.size / 1024 / 1024).toFixed(1)}MB`);
    return outputPath;
  } catch (err) {
    // Log stderr for debugging
    if (err.stderr) {
      console.error(`[FFMPEG] stderr: ${err.stderr.toString().slice(-500)}`);
    }
    throw new Error(`FFmpeg re-encode failed: ${err.message}`);
  }
}

// Download all assets (scene videos + audio) to local temp files
async function downloadAssets(config, jobDir) {
  console.log(`[ASSETS] Downloading to ${jobDir}...`);

  // Download scene videos, cache them, and remux for Chromium compatibility
  for (let i = 0; i < config.scenes.length; i++) {
    const scene = config.scenes[i];
    const videoUrl = scene.videoPath;

    // If already a local path (cached), just verify it exists
    if (videoUrl && !videoUrl.startsWith("http")) {
      if (fs.existsSync(videoUrl)) {
        console.log(`[ASSETS] Scene ${i}: using local file ${videoUrl}`);
        continue;
      }
      console.log(`[ASSETS] Scene ${i}: local file not found: ${videoUrl}`);
      continue;
    }

    if (videoUrl && (videoUrl.startsWith("http://") || videoUrl.startsWith("https://"))) {
      // Extract unique ID from URL for cache key (e.g. UUID from cloudfront URL)
      const urlMatch = videoUrl.match(/([a-f0-9-]{36})\.mp4/);
      const cacheKey = urlMatch ? urlMatch[1] : `scene_${Date.now()}_${i}`;
      const cachedPath = path.join(CACHE_DIR, `${cacheKey}.mp4`);

      // Check cache first
      if (fs.existsSync(cachedPath)) {
        const stat = fs.statSync(cachedPath);
        if (stat.size > 10000) {
          console.log(`[CACHE HIT] Scene ${i}: ${cacheKey} (${(stat.size / 1024 / 1024).toFixed(1)}MB)`);
          scene.videoPath = cachedPath;
          continue;
        }
      }

      const rawPath = path.join(jobDir, `scene_${i}_raw.mp4`);
      const convertedPath = path.join(jobDir, `scene_${i}.mp4`);
      console.log(`[ASSETS] Scene ${i}: downloading...`);
      await downloadFile(videoUrl, rawPath);
      const rawStat = fs.statSync(rawPath);
      console.log(`[ASSETS] Scene ${i}: downloaded ${(rawStat.size / 1024 / 1024).toFixed(1)}MB`);
      convertVideo(rawPath, convertedPath);
      fs.unlinkSync(rawPath);

      // Save to cache
      fs.copyFileSync(convertedPath, cachedPath);
      console.log(`[CACHE SAVE] Scene ${i}: ${cacheKey}`);

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
    // Cleanup job dir on error but keep cache intact for retry
    try { fs.rmSync(jobDir, { recursive: true, force: true }); } catch (_) {}
    res.status(500).json({ error: err.message });
  }
});

// GET /health
app.get("/health", (_req, res) => {
  const cacheFiles = fs.existsSync(CACHE_DIR) ? fs.readdirSync(CACHE_DIR).filter(f => f.endsWith(".mp4")) : [];
  res.json({
    status: "ok",
    service: "remotion-renderer",
    version: "4.1-offthread",
    cachedScenes: cacheFiles.length,
  });
});

// DELETE /cache — clear cached scenes
app.delete("/cache", (_req, res) => {
  if (fs.existsSync(CACHE_DIR)) {
    fs.rmSync(CACHE_DIR, { recursive: true, force: true });
    fs.mkdirSync(CACHE_DIR, { recursive: true });
  }
  res.json({ cleared: true });
});

// GET /cache — list cached scene videos
app.get("/cache", (_req, res) => {
  if (!fs.existsSync(CACHE_DIR)) return res.json({ scenes: [] });
  const files = fs.readdirSync(CACHE_DIR).filter(f => f.endsWith(".mp4"));
  const scenes = files.map(f => {
    const stat = fs.statSync(path.join(CACHE_DIR, f));
    return { file: f, sizeMB: (stat.size / 1024 / 1024).toFixed(1), cached: stat.mtime.toISOString() };
  });
  res.json({ scenes, cacheDir: CACHE_DIR });
});

app.listen(PORT, () => {
  console.log(`Remotion render server on port ${PORT}`);
  console.log(`Concurrency: ${CONCURRENCY} | Chrome: ${CHROME_EXECUTABLE}`);
  getBundle().catch((err) => console.error("Pre-warm failed:", err.message));
});
