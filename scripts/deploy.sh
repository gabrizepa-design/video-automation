#!/usr/bin/env bash
# =============================================================================
# deploy.sh — Deploy latest code to production
# =============================================================================
set -e

PROJECT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
cd "$PROJECT_DIR"

echo "================================================"
echo " Video Automation — Deploy"
echo "================================================"

# Pull latest code
echo "[1/4] Pulling latest changes..."
git pull origin main

# Rebuild changed services
echo "[2/4] Rebuilding Docker images..."
docker compose build --no-cache file-watcher remotion-renderer

# Restart services
echo "[3/4] Restarting services..."
docker compose up -d --remove-orphans

# Wait for health checks
echo "[4/4] Waiting for services to be healthy..."
sleep 10
docker compose ps

# Run tests
echo ""
echo "Running system tests..."
./scripts/test-system.sh

echo ""
echo "✅ Deploy complete!"
