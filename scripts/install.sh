#!/usr/bin/env bash
# =============================================================================
# install.sh — Video Automation System VPS Bootstrap
# Ubuntu 22.04 LTS | Run as root or with sudo
# =============================================================================
set -e

echo "================================================"
echo " Video Automation System — VPS Installation"
echo "================================================"

# ---------------------------------------------------------------------------
# 1. System update
# ---------------------------------------------------------------------------
echo "[1/8] Updating system packages..."
apt-get update -qq
apt-get install -y -qq curl git vim htop unzip

# ---------------------------------------------------------------------------
# 2. Install Docker
# ---------------------------------------------------------------------------
echo "[2/8] Installing Docker..."
if ! command -v docker &> /dev/null; then
  curl -fsSL https://get.docker.com | sh
  systemctl enable docker
  systemctl start docker
  echo "Docker installed: $(docker --version)"
else
  echo "Docker already installed: $(docker --version)"
fi

# ---------------------------------------------------------------------------
# 3. Install Docker Compose (v2 plugin)
# ---------------------------------------------------------------------------
echo "[3/8] Installing Docker Compose..."
if ! docker compose version &> /dev/null 2>&1; then
  apt-get install -y -qq docker-compose-plugin
  echo "Docker Compose installed: $(docker compose version)"
else
  echo "Docker Compose already installed: $(docker compose version)"
fi

# ---------------------------------------------------------------------------
# 4. Clone repository
# ---------------------------------------------------------------------------
echo "[4/8] Setting up project..."
PROJECT_DIR="/root/video-automation"

if [ -d "$PROJECT_DIR" ]; then
  echo "Project directory already exists at $PROJECT_DIR"
  echo "Pulling latest changes..."
  cd "$PROJECT_DIR" && git pull origin main 2>/dev/null || true
else
  echo "Cloning project to $PROJECT_DIR..."
  echo ""
  echo "  NOTE: Replace the URL below with your actual repository URL"
  echo "  git clone https://github.com/YOUR_USER/video-automation.git $PROJECT_DIR"
  echo ""
  # git clone https://github.com/YOUR_USER/video-automation.git "$PROJECT_DIR"
  mkdir -p "$PROJECT_DIR"
  echo "  Created empty directory. Copy your project files here."
fi

cd "$PROJECT_DIR"

# ---------------------------------------------------------------------------
# 5. Configure environment
# ---------------------------------------------------------------------------
echo "[5/8] Setting up environment..."
if [ ! -f ".env" ]; then
  if [ -f ".env.example" ]; then
    cp .env.example .env
    echo ""
    echo "  ⚠️  IMPORTANT: Edit .env and fill in your API keys!"
    echo "  nano .env"
    echo ""
  else
    echo "  ⚠️  No .env.example found. Create .env manually."
  fi
else
  echo ".env already exists — skipping"
fi

# ---------------------------------------------------------------------------
# 6. Create required directories
# ---------------------------------------------------------------------------
echo "[6/8] Creating directories..."
mkdir -p temp_videos/{scenes,audio,subtitles,final}
mkdir -p postgres_data
mkdir -p n8n_data/workflows
echo "Directories created."

# ---------------------------------------------------------------------------
# 7. Pre-pull Docker images
# ---------------------------------------------------------------------------
echo "[7/8] Pre-pulling Docker images (this may take a few minutes)..."
docker pull postgres:14-alpine
docker pull n8nio/n8n:1.30.1
echo "Base images pulled."

# ---------------------------------------------------------------------------
# 8. Done
# ---------------------------------------------------------------------------
echo ""
echo "================================================"
echo " Installation complete!"
echo "================================================"
echo ""
echo "Next steps:"
echo "  1. Edit your .env file:       nano $PROJECT_DIR/.env"
echo "  2. Setup Google OAuth2:       node scripts/setup-google-auth.js"
echo "  3. Start services:            docker compose up -d"
echo "  4. Check service health:      docker compose ps"
echo "  5. Access n8n UI:             http://$(hostname -I | awk '{print $1}'):5678"
echo "  6. Import n8n workflows from: n8n_data/workflows/"
echo "  7. Run system tests:          ./scripts/test-system.sh"
echo ""
