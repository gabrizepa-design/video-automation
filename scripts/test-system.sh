#!/usr/bin/env bash
# =============================================================================
# test-system.sh — End-to-end system test
# =============================================================================
set -e

PASS=0
FAIL=0
PROJECT_DIR="$(cd "$(dirname "$0")/.." && pwd)"

echo "================================================"
echo " Video Automation — System Test"
echo "================================================"
echo ""

check() {
  local name="$1"
  local result="$2"
  if [ "$result" = "ok" ]; then
    echo "  ✅ $name"
    ((PASS++))
  else
    echo "  ❌ $name — $result"
    ((FAIL++))
  fi
}

# ---------------------------------------------------------------------------
# 1. Docker services health
# ---------------------------------------------------------------------------
echo "[1/5] Checking Docker services..."
cd "$PROJECT_DIR"

if docker compose ps --format json 2>/dev/null | grep -q '"Status"'; then
  UNHEALTHY=$(docker compose ps --format json 2>/dev/null | python3 -c "
import sys, json
data = sys.stdin.read()
for line in data.strip().split('\n'):
    try:
        s = json.loads(line)
        if 'unhealthy' in s.get('Status','').lower() or 'exit' in s.get('Status','').lower():
            print(s.get('Service','unknown'))
    except: pass
" 2>/dev/null || echo "")

  if [ -z "$UNHEALTHY" ]; then
    check "All Docker services healthy" "ok"
  else
    check "All Docker services healthy" "unhealthy: $UNHEALTHY"
  fi
else
  check "Docker Compose running" "docker compose not accessible"
fi

# ---------------------------------------------------------------------------
# 2. API tests
# ---------------------------------------------------------------------------
echo ""
echo "[2/5] Testing API connections..."
if node "$PROJECT_DIR/scripts/test-apis.js" 2>/dev/null; then
  check "All APIs responding" "ok"
else
  check "All APIs responding" "one or more APIs failed (see above)"
fi

# ---------------------------------------------------------------------------
# 3. Parser test
# ---------------------------------------------------------------------------
echo ""
echo "[3/5] Testing ViralScout parser..."
TEST_MD=$(find /mnt/c/Users/gabri/Desktop/proyectos\ vs\ codes/VIralit/ -name "*.md" 2>/dev/null | head -1)
if [ -n "$TEST_MD" ]; then
  if node "$PROJECT_DIR/file-watcher/parser.js" "$TEST_MD" > /dev/null 2>&1; then
    check "Parser — parse real .md file" "ok"
  else
    check "Parser — parse real .md file" "parser returned error"
  fi
else
  echo "  ⚠️  No .md files found in VIralit folder — skipping parser test"
fi

# ---------------------------------------------------------------------------
# 4. Remotion health
# ---------------------------------------------------------------------------
echo ""
echo "[4/5] Testing Remotion renderer..."
REMOTION_STATUS=$(curl -sf http://localhost:3001/health 2>/dev/null | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('status','unknown'))" 2>/dev/null || echo "unreachable")
check "Remotion renderer HTTP" "$([[ '$REMOTION_STATUS' == 'ok' ]] && echo ok || echo $REMOTION_STATUS)"

# ---------------------------------------------------------------------------
# 5. File watcher
# ---------------------------------------------------------------------------
echo ""
echo "[5/5] Testing file watcher..."
WATCHER_STATUS=$(docker inspect video_automation_watcher --format='{{.State.Status}}' 2>/dev/null || echo "not running")
check "File watcher container" "$([[ '$WATCHER_STATUS' == 'running' ]] && echo ok || echo $WATCHER_STATUS)"

# ---------------------------------------------------------------------------
# Summary
# ---------------------------------------------------------------------------
echo ""
echo "================================================"
echo " Results: $PASS passed, $FAIL failed"
echo "================================================"
echo ""

if [ "$FAIL" -gt 0 ]; then
  echo "  Some tests failed. Check the output above."
  echo "  Common fixes:"
  echo "    - docker compose up -d  (start all services)"
  echo "    - nano .env             (check API keys)"
  echo "    - docker compose logs   (check for errors)"
  exit 1
else
  echo "  🎉 System is healthy and ready!"
fi
