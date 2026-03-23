require("dotenv").config({ path: "../.env" });

const chokidar = require("chokidar");
const axios = require("axios");
const fs = require("fs");
const path = require("path");
const winston = require("winston");
const { parseViralScoutFile } = require("./parser");

// ---------------------------------------------------------------------------
// Logger
// ---------------------------------------------------------------------------
const logger = winston.createLogger({
  level: "info",
  format: winston.format.combine(
    winston.format.timestamp(),
    winston.format.printf(({ timestamp, level, message }) => {
      return `${timestamp} [${level.toUpperCase()}] ${message}`;
    })
  ),
  transports: [new winston.transports.Console()],
});

// ---------------------------------------------------------------------------
// Config
// ---------------------------------------------------------------------------
const WATCH_DIR = process.env.VIRALSCOUT_WATCH_DIR || path.join(__dirname, "..", "..", "VIralit");
const WEBHOOK_URL =
  process.env.N8N_WEBHOOK_URL || "https://noctisiops-n8n.gpsefe.easypanel.host/webhook/new-script";
const POLL_INTERVAL = parseInt(process.env.WATCH_POLL_INTERVAL || "5000", 10);
const PROCESSED_FILE = path.join(__dirname, "processed_files.json");
const MAX_RETRIES = 3;

// ---------------------------------------------------------------------------
// Processed files tracking (persisted to disk)
// ---------------------------------------------------------------------------
function loadProcessed() {
  try {
    if (fs.existsSync(PROCESSED_FILE)) {
      const data = JSON.parse(fs.readFileSync(PROCESSED_FILE, "utf-8"));
      return new Set(data);
    }
  } catch {
    logger.warn("Could not load processed files list, starting fresh");
  }
  return new Set();
}

function saveProcessed(set) {
  try {
    fs.writeFileSync(PROCESSED_FILE, JSON.stringify([...set]), "utf-8");
  } catch (err) {
    logger.error(`Failed to persist processed list: ${err.message}`);
  }
}

const processedFiles = loadProcessed();

// ---------------------------------------------------------------------------
// Send to n8n with retry
// ---------------------------------------------------------------------------
async function sendToN8n(payload, retries = 0) {
  try {
    const response = await axios.post(WEBHOOK_URL, payload, {
      timeout: 15000,
      headers: { "Content-Type": "application/json" },
    });
    logger.info(`Webhook sent OK [${response.status}] — ${payload.sourceFile}`);
    return true;
  } catch (err) {
    if (retries < MAX_RETRIES) {
      const delay = Math.pow(2, retries) * 5000;
      logger.warn(
        `Webhook failed (attempt ${retries + 1}/${MAX_RETRIES}), retrying in ${delay / 1000}s — ${err.message}`
      );
      await new Promise((r) => setTimeout(r, delay));
      return sendToN8n(payload, retries + 1);
    }
    logger.error(
      `Webhook permanently failed after ${MAX_RETRIES} attempts: ${err.message}`
    );
    return false;
  }
}

// ---------------------------------------------------------------------------
// Handle new .md file
// ---------------------------------------------------------------------------
async function handleNewFile(filePath) {
  const filename = path.basename(filePath);

  if (processedFiles.has(filePath)) {
    logger.info(`Skipping already processed: ${filename}`);
    return;
  }

  if (!filename.endsWith(".md")) return;

  logger.info(`New file detected: ${filename}`);

  let content;
  try {
    content = fs.readFileSync(filePath, "utf-8");
  } catch (err) {
    logger.error(`Cannot read file ${filename}: ${err.message}`);
    return;
  }

  let parsed;
  try {
    parsed = parseViralScoutFile(content, filename);
  } catch (err) {
    logger.error(`Parse error for ${filename}: ${err.message}`);
    return;
  }

  if (!parsed || !parsed.ideas || parsed.ideas.length === 0) {
    logger.warn(`No ideas found in ${filename}, skipping`);
    return;
  }

  logger.info(
    `Parsed ${parsed.ideas.length} ideas from ${filename} — sending to n8n`
  );

  const ok = await sendToN8n(parsed);
  if (ok) {
    processedFiles.add(filePath);
    saveProcessed(processedFiles);
  }
}

// ---------------------------------------------------------------------------
// Start watcher
// ---------------------------------------------------------------------------
logger.info(`Starting file watcher on: ${WATCH_DIR}`);
logger.info(`Webhook target: ${WEBHOOK_URL}`);
logger.info(`Poll interval: ${POLL_INTERVAL}ms`);

const watcher = chokidar.watch(`${WATCH_DIR}/*.md`, {
  // usePolling is REQUIRED on WSL2/NTFS mounts — inotify doesn't work
  usePolling: true,
  interval: POLL_INTERVAL,
  awaitWriteFinish: {
    stabilityThreshold: 2000,
    pollInterval: 500,
  },
  ignoreInitial: false,
  persistent: true,
});

watcher
  .on("add", (filePath) => handleNewFile(filePath))
  .on("error", (err) => logger.error(`Watcher error: ${err.message}`))
  .on("ready", () => logger.info("Initial scan complete. Watching for new files..."));

// ---------------------------------------------------------------------------
// Graceful shutdown
// ---------------------------------------------------------------------------
function shutdown(signal) {
  logger.info(`Received ${signal}, shutting down...`);
  saveProcessed(processedFiles);
  watcher.close().then(() => {
    logger.info("Watcher closed.");
    process.exit(0);
  });
}

process.on("SIGTERM", () => shutdown("SIGTERM"));
process.on("SIGINT", () => shutdown("SIGINT"));
