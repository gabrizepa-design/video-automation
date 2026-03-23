/**
 * test-apis.js — Test all API connections
 * Usage: node scripts/test-apis.js
 */

require("dotenv").config({ path: "./.env" });
const https = require("https");
const http = require("http");

const results = [];
let passed = 0;
let failed = 0;

function makeRequest(options, body = null) {
  return new Promise((resolve, reject) => {
    const protocol = options.port === 443 || options.hostname.startsWith("https") ? https : http;
    const req = protocol.request(options, (res) => {
      let data = "";
      res.on("data", (chunk) => (data += chunk));
      res.on("end", () => {
        resolve({ status: res.statusCode, body: data });
      });
    });
    req.on("error", reject);
    req.setTimeout(10000, () => {
      req.destroy();
      reject(new Error("Timeout after 10s"));
    });
    if (body) req.write(body);
    req.end();
  });
}

async function test(name, fn) {
  const start = Date.now();
  try {
    await fn();
    const ms = Date.now() - start;
    console.log(`  ✅ ${name.padEnd(25)} ${ms}ms`);
    results.push({ name, status: "PASS", ms });
    passed++;
  } catch (err) {
    const ms = Date.now() - start;
    console.log(`  ❌ ${name.padEnd(25)} FAIL — ${err.message}`);
    results.push({ name, status: "FAIL", error: err.message, ms });
    failed++;
  }
}

async function runTests() {
  console.log("\n🔍 Testing API connections...\n");

  // Claude (Anthropic)
  await test("Claude API", async () => {
    const key = process.env.ANTHROPIC_API_KEY;
    if (!key || key === "sk-ant-xxx") throw new Error("ANTHROPIC_API_KEY not set");
    const body = JSON.stringify({
      model: "claude-haiku-4-5-20251001",
      max_tokens: 1,
      messages: [{ role: "user", content: "Hi" }],
    });
    const res = await makeRequest({
      hostname: "api.anthropic.com",
      port: 443,
      path: "/v1/messages",
      method: "POST",
      headers: {
        "x-api-key": key,
        "anthropic-version": "2023-06-01",
        "content-type": "application/json",
        "content-length": Buffer.byteLength(body),
      },
    }, body);
    if (res.status !== 200) throw new Error(`HTTP ${res.status}: ${res.body.substring(0, 100)}`);
  });

  // Runway
  await test("Runway API", async () => {
    const key = process.env.RUNWAY_API_KEY;
    if (!key || key === "xxx") throw new Error("RUNWAY_API_KEY not set");
    const res = await makeRequest({
      hostname: "api.runwayml.com",
      port: 443,
      path: "/v1/organization",
      method: "GET",
      headers: { Authorization: `Bearer ${key}` },
    });
    if (res.status !== 200 && res.status !== 404) throw new Error(`HTTP ${res.status}`);
  });

  // ElevenLabs
  await test("ElevenLabs API", async () => {
    const key = process.env.ELEVENLABS_API_KEY;
    if (!key || key === "xxx") throw new Error("ELEVENLABS_API_KEY not set");
    const res = await makeRequest({
      hostname: "api.elevenlabs.io",
      port: 443,
      path: "/v1/voices",
      method: "GET",
      headers: { "xi-api-key": key },
    });
    if (res.status !== 200) throw new Error(`HTTP ${res.status}`);
    const data = JSON.parse(res.body);
    if (!data.voices) throw new Error("Unexpected response format");
  });

  // OpenAI (Whisper)
  await test("OpenAI / Whisper", async () => {
    const key = process.env.OPENAI_API_KEY;
    if (!key || key === "sk-xxx") throw new Error("OPENAI_API_KEY not set");
    const res = await makeRequest({
      hostname: "api.openai.com",
      port: 443,
      path: "/v1/models",
      method: "GET",
      headers: { Authorization: `Bearer ${key}` },
    });
    if (res.status !== 200) throw new Error(`HTTP ${res.status}`);
    const data = JSON.parse(res.body);
    const hasWhisper = data.data?.some((m) => m.id.includes("whisper"));
    if (!hasWhisper) throw new Error("whisper-1 model not found");
  });

  // Telegram
  await test("Telegram Bot", async () => {
    const token = process.env.TELEGRAM_BOT_TOKEN;
    if (!token || token === "xxx") throw new Error("TELEGRAM_BOT_TOKEN not set");
    const res = await makeRequest({
      hostname: "api.telegram.org",
      port: 443,
      path: `/bot${token}/getMe`,
      method: "GET",
    });
    if (res.status !== 200) throw new Error(`HTTP ${res.status}`);
    const data = JSON.parse(res.body);
    if (!data.ok) throw new Error(data.description || "Bot not found");
    console.log(`     Bot name: @${data.result.username}`);
  });

  // n8n (local)
  await test("n8n (local)", async () => {
    const res = await makeRequest({
      hostname: "localhost",
      port: 5678,
      path: "/healthz",
      method: "GET",
    });
    if (res.status !== 200) throw new Error(`HTTP ${res.status} — is n8n running?`);
  });

  // Remotion renderer (local)
  await test("Remotion Renderer", async () => {
    const res = await makeRequest({
      hostname: "localhost",
      port: 3001,
      path: "/health",
      method: "GET",
    });
    if (res.status !== 200) throw new Error(`HTTP ${res.status} — is remotion-renderer running?`);
  });

  // Summary
  console.log("\n" + "─".repeat(45));
  console.log(`  Results: ${passed} passed, ${failed} failed`);
  if (failed > 0) {
    console.log("\n  ⚠️  Fix the failing APIs before starting the pipeline");
    process.exit(1);
  } else {
    console.log("\n  🎉 All APIs are working!");
  }
}

runTests().catch((err) => {
  console.error("Test runner crashed:", err.message);
  process.exit(1);
});
