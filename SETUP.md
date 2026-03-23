# 🚀 SETUP.md - Guía de Instalación

## 📋 PREREQUISITOS

Antes de empezar, asegúrate de tener:

### **Hardware**
- ✅ VPS con mínimo 8GB RAM
- ✅ 4 vCPU o más
- ✅ 160GB de almacenamiento SSD
- ✅ Conexión estable a internet (100+ Mbps)

### **Software**
- ✅ Ubuntu 22.04 LTS (recomendado)
- ✅ Acceso SSH al VPS
- ✅ Dominio (opcional, para HTTPS)

### **API Keys** (obtener antes de instalar)
- ✅ Anthropic API (Claude)
- ✅ Runway Gen-3 API
- ✅ ElevenLabs API
- ✅ OpenAI API (Whisper)
- ✅ Google OAuth2 credentials (Drive + YouTube)
- ✅ Telegram Bot Token

---

## 🎯 INSTALACIÓN RÁPIDA (10 minutos)

```bash
# 1. Conectar al VPS
ssh root@tu-vps-ip

# 2. Clonar repositorio
git clone https://github.com/tu-usuario/video-automation.git
cd video-automation

# 3. Ejecutar script de instalación
chmod +x scripts/install.sh
./scripts/install.sh

# 4. Configurar variables de entorno
cp .env.example .env
nano .env  # Editar con tus API keys

# 5. Levantar servicios
docker-compose up -d

# 6. Verificar instalación
./scripts/test-system.sh
```

---

## 📝 INSTALACIÓN PASO A PASO

### **PASO 1: Preparar el VPS**

```bash
# Actualizar sistema
sudo apt-get update
sudo apt-get upgrade -y

# Instalar dependencias básicas
sudo apt-get install -y \
    curl \
    git \
    wget \
    vim \
    htop \
    ca-certificates \
    gnupg \
    lsb-release
```

---

### **PASO 2: Instalar Docker**

```bash
# Instalar Docker
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh

# Iniciar Docker
sudo systemctl start docker
sudo systemctl enable docker

# Verificar
docker --version
# Output: Docker version 24.0.x

# Agregar usuario al grupo docker (opcional)
sudo usermod -aG docker $USER
newgrp docker
```

---

### **PASO 3: Instalar Docker Compose**

```bash
# Descargar Docker Compose
sudo curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" \
    -o /usr/local/bin/docker-compose

# Dar permisos de ejecución
sudo chmod +x /usr/local/bin/docker-compose

# Verificar
docker-compose --version
# Output: Docker Compose version v2.x.x
```

---

### **PASO 4: Clonar el Proyecto**

```bash
# Crear directorio
mkdir -p /root/video-automation
cd /root/video-automation

# Clonar repositorio
git clone https://github.com/tu-usuario/video-automation.git .

# Verificar estructura
ls -la
# Deberías ver: docker-compose.yml, .env.example, scripts/, etc.
```

---

### **PASO 5: Configurar Variables de Entorno**

```bash
# Copiar template
cp .env.example .env

# Editar con tus credenciales
nano .env
```

**Completar TODAS estas variables:**

```bash
# ============================================
# n8n
# ============================================
N8N_PASSWORD=CREAR_PASSWORD_SEGURO_AQUI
POSTGRES_PASSWORD=CREAR_PASSWORD_POSTGRES_AQUI
N8N_ENCRYPTION_KEY=GENERAR_RANDOM_32_CHARS
DOMAIN=tu-dominio.com

# ============================================
# API Keys - CRÍTICO: Obtener antes de continuar
# ============================================

# Anthropic Claude API
# Obtener en: https://console.anthropic.com/
ANTHROPIC_API_KEY=sk-ant-api03-xxxxx

# Runway Gen-3 API
# Obtener en: https://runwayml.com/
RUNWAY_API_KEY=xxxxx

# ElevenLabs API
# Obtener en: https://elevenlabs.io/
ELEVENLABS_API_KEY=xxxxx
ELEVENLABS_VOICE_ID=21m00Tcm4TlvDq8ikWAM  # Rachel voice

# OpenAI Whisper API
# Obtener en: https://platform.openai.com/
OPENAI_API_KEY=sk-xxxxx

# ============================================
# Google OAuth2 - Ver sección "PASO 6" abajo
# ============================================
GOOGLE_CLIENT_ID=xxxxx.apps.googleusercontent.com
GOOGLE_CLIENT_SECRET=GOCSPX-xxxxx
GOOGLE_REFRESH_TOKEN=1//xxxxx

# Google Drive Folders - Ver "PASO 7"
GDRIVE_PENDING_FOLDER_ID=xxxxx
GDRIVE_APPROVED_FOLDER_ID=xxxxx
GDRIVE_REJECTED_FOLDER_ID=xxxxx

# YouTube
YOUTUBE_CHANNEL_ID=UCxxxxx

# ============================================
# Telegram Bot - Ver "PASO 8"
# ============================================
TELEGRAM_BOT_TOKEN=1234567890:ABCdefGHI
TELEGRAM_CHAT_ID=123456789

# ============================================
# Paths
# ============================================
VIRALSCOUT_WATCH_DIR=/watch
TEMP_VIDEOS_DIR=/tmp/videos

# ============================================
# Remotion
# ============================================
REMOTION_CONCURRENCY=4
```

**Guardar:** `Ctrl+O`, `Enter`, `Ctrl+X`

---

### **PASO 6: Configurar Google OAuth2**

Este paso es crítico para Google Drive y YouTube.

#### **6.1. Crear Proyecto en Google Cloud**

```
1. Ir a: https://console.cloud.google.com/
2. Click "Select a project" → "New Project"
3. Nombre: "Video Automation"
4. Click "Create"
```

#### **6.2. Habilitar APIs**

```
1. En el menú lateral: "APIs & Services" → "Library"
2. Buscar y habilitar:
   - Google Drive API
   - YouTube Data API v3
3. Click "Enable" en cada una
```

#### **6.3. Crear OAuth2 Credentials**

```
1. "APIs & Services" → "Credentials"
2. Click "Create Credentials" → "OAuth client ID"
3. Application type: "Desktop app"
4. Name: "Video Automation Client"
5. Click "Create"
6. Copiar:
   - Client ID → GOOGLE_CLIENT_ID en .env
   - Client secret → GOOGLE_CLIENT_SECRET en .env
```

#### **6.4. Obtener Refresh Token**

```bash
# Ejecutar script de autenticación
node scripts/setup-google-auth.js

# Seguir las instrucciones:
# 1. Se abrirá una URL en el navegador
# 2. Loguearte con tu cuenta de Google
# 3. Aprobar permisos (Drive + YouTube)
# 4. El script mostrará el refresh_token
# 5. Copiar el token a .env → GOOGLE_REFRESH_TOKEN
```

---

### **PASO 7: Crear Carpetas en Google Drive**

```
1. Ir a: https://drive.google.com/
2. Crear 3 carpetas:
   - "Videos Pendientes de Aprobación"
   - "Videos Aprobados"
   - "Videos Rechazados"

3. Para cada carpeta:
   - Click derecho → "Get link" → "Anyone with the link"
   - Copiar URL: https://drive.google.com/drive/folders/1a2b3c4d5e
   - El ID es la parte final: 1a2b3c4d5e
   
4. Agregar a .env:
   GDRIVE_PENDING_FOLDER_ID=1a2b3c4d5e
   GDRIVE_APPROVED_FOLDER_ID=9i8h7g6f5e
   GDRIVE_REJECTED_FOLDER_ID=a1b2c3d4e5
```

---

### **PASO 8: Crear Telegram Bot**

#### **8.1. Crear Bot con BotFather**

```
1. Abrir Telegram
2. Buscar: @BotFather
3. Enviar: /newbot
4. Nombre: "Video Automation Bot"
5. Username: "tu_video_bot" (debe terminar en 'bot')
6. BotFather te dará el token
7. Copiar a .env → TELEGRAM_BOT_TOKEN
```

#### **8.2. Obtener tu Chat ID**

```
1. Buscar en Telegram: @userinfobot
2. Enviar: /start
3. El bot te dará tu user ID
4. Copiar a .env → TELEGRAM_CHAT_ID
```

#### **8.3. Configurar Comandos del Bot**

```
1. En Telegram, enviar a @BotFather: /setcommands
2. Seleccionar tu bot
3. Enviar esta lista:
aprobar - Aprobar video para YouTube
rechazar - Rechazar video
regenerar - Regenerar video

4. Esto crea botones de comando en Telegram
```

---

### **PASO 9: Levantar Servicios**

```bash
# Verificar configuración
cat .env | grep API_KEY
# Debe mostrar todas tus API keys (sin mostrar valores completos)

# Levantar servicios en background
docker-compose up -d

# Ver logs en tiempo real
docker-compose logs -f

# Verificar que todos los servicios estén corriendo
docker-compose ps
# Deberías ver:
# - video_automation_n8n          (healthy)
# - video_automation_postgres      (healthy)
# - video_automation_remotion      (healthy)
# - video_automation_watcher       (healthy)
```

---

### **PASO 10: Configurar n8n**

```bash
# 1. Acceder a n8n UI
# http://tu-vps-ip:5678

# 2. Login con credenciales de .env
# Username: admin
# Password: N8N_PASSWORD (del .env)

# 3. Importar workflows
# Settings → Import from file
# Importar cada archivo de n8n_data/workflows/:
#   - main-pipeline.json
#   - telegram-approval.json
#   - youtube-upload.json

# 4. Configurar credenciales
# Credentials → Add Credential
# Agregar:
#   - Anthropic API (HTTP Header Auth)
#   - Runway API (HTTP Header Auth)
#   - ElevenLabs API (HTTP Header Auth)
#   - OpenAI API (HTTP Header Auth)
#   - Google OAuth2 (usar datos del .env)
#   - Telegram Bot (usar token del .env)

# 5. Activar workflows
# Click en cada workflow → Click "Active" (toggle on)
```

---

### **PASO 11: Test del Sistema**

```bash
# Test completo
./scripts/test-system.sh

# Si todo está OK, verás:
# ✅ Docker OK
# ✅ n8n OK
# ✅ APIs OK
# ✅ File watcher OK
# ✅ Remotion OK
# ✅ All tests passed!

# Test manual con archivo de ejemplo
cp example-script.md "/mnt/c/Users/gabri/Desktop/proyectos vs codes/VIralit/"

# Verificar logs
docker logs video_automation_watcher -f
# Deberías ver: "New file detected: example-script.md"

# Verificar ejecución en n8n
# http://tu-vps-ip:5678/executions
# Deberías ver la ejecución del workflow
```

---

## 🔧 CONFIGURACIÓN AVANZADA (Opcional)

### **HTTPS con Let's Encrypt**

```bash
# Instalar Nginx
sudo apt-get install -y nginx

# Instalar Certbot
sudo apt-get install -y certbot python3-certbot-nginx

# Obtener certificado
sudo certbot --nginx -d tu-dominio.com

# Configurar Nginx como reverse proxy para n8n
sudo nano /etc/nginx/sites-available/n8n

# Agregar:
server {
    listen 80;
    server_name tu-dominio.com;
    return 301 https://$server_name$request_uri;
}

server {
    listen 443 ssl;
    server_name tu-dominio.com;

    ssl_certificate /etc/letsencrypt/live/tu-dominio.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/tu-dominio.com/privkey.pem;

    location / {
        proxy_pass http://localhost:5678;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection 'upgrade';
        proxy_set_header Host $host;
        proxy_cache_bypass $http_upgrade;
    }
}

# Habilitar sitio
sudo ln -s /etc/nginx/sites-available/n8n /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl restart nginx

# Actualizar .env
DOMAIN=tu-dominio.com
WEBHOOK_URL=https://tu-dominio.com/

# Restart n8n
docker-compose restart n8n
```

---

### **Monitoreo con Healthchecks**

```bash
# Agregar a crontab
crontab -e

# Agregar línea:
*/5 * * * * curl -fsS --retry 3 http://localhost:5678/healthz > /dev/null || echo "n8n down" | mail -s "Alert" tu-email@example.com
```

---

### **Backup Automático**

```bash
# Crear script de backup
nano /root/backup.sh

#!/bin/bash
DATE=$(date +%Y%m%d_%H%M%S)
tar -czf /root/backups/backup_$DATE.tar.gz \
    /root/video-automation/n8n_data/ \
    /root/video-automation/postgres_data/ \
    /root/video-automation/.env

# Limpiar backups antiguos (> 30 días)
find /root/backups/ -name "backup_*.tar.gz" -mtime +30 -delete

# Dar permisos
chmod +x /root/backup.sh

# Agregar a crontab (backup diario a las 3am)
crontab -e
0 3 * * * /root/backup.sh
```

---

## 🐛 TROUBLESHOOTING COMÚN

### **Error: "Cannot connect to Docker daemon"**

```bash
# Verificar que Docker esté corriendo
sudo systemctl status docker

# Si no está corriendo
sudo systemctl start docker

# Verificar permisos
sudo usermod -aG docker $USER
newgrp docker
```

---

### **Error: "Port 5678 already in use"**

```bash
# Ver qué está usando el puerto
sudo lsof -i :5678

# Matar el proceso
sudo kill -9 <PID>

# O cambiar puerto en docker-compose.yml
ports:
  - "5679:5678"  # Usa 5679 externamente
```

---

### **Error: File Watcher no detecta archivos**

```bash
# Verificar mount point
docker exec video_automation_watcher ls -la /watch

# Si está vacío, verificar path en docker-compose.yml
volumes:
  - /mnt/c/Users/gabri/Desktop/proyectos vs codes/VIralit:/watch:ro

# Verificar permisos
chmod -R 755 "/mnt/c/Users/gabri/Desktop/proyectos vs codes/VIralit"
```

---

### **Error: "API rate limit exceeded"**

```bash
# Verificar uso de APIs
node scripts/test-apis.js

# Si excediste límite, esperar o upgradeaar plan
# Mientras tanto, deshabilitar workflow en n8n
```

---

### **Error: Remotion render falla**

```bash
# Ver logs
docker logs video_automation_remotion

# Errores comunes:
# 1. Falta memoria → Upgrade VPS a 16GB
# 2. Chromium crash → Restart container
docker-compose restart remotion-renderer

# 3. FFmpeg error → Verificar video inputs
ls -la /tmp/videos/scenes/
```

---

## 📚 RECURSOS ADICIONALES

- **Docker Docs:** https://docs.docker.com/
- **n8n Docs:** https://docs.n8n.io/
- **Remotion Docs:** https://www.remotion.dev/docs/
- **Google Cloud Console:** https://console.cloud.google.com/
- **Telegram Bot API:** https://core.telegram.org/bots/api

---

## ✅ CHECKLIST POST-INSTALACIÓN

Después de completar la instalación, verificar:

- [ ] Docker y Docker Compose instalados
- [ ] Todos los servicios corriendo (docker-compose ps)
- [ ] n8n accesible en http://vps-ip:5678
- [ ] Workflows importados y activos
- [ ] Todas las API keys configuradas
- [ ] Google OAuth funcionando
- [ ] Telegram bot respondiendo
- [ ] File watcher monitoreando carpeta
- [ ] Test system pasando (./scripts/test-system.sh)
- [ ] Test manual con archivo .md funcionando
- [ ] Video final generado y subido a Drive
- [ ] Notificación recibida en Telegram

---

## 🎉 ¡INSTALACIÓN COMPLETA!

Si llegaste hasta aquí, tu sistema está listo para generar videos automáticamente.

**Próximo paso:**
Copia un guion de ViralScout a la carpeta watcheada y observa la magia ocurrir. 🚀

**Soporte:**
Si tienes problemas, revisa primero los logs:
```bash
docker-compose logs -f
```

---

Documento actualizado: 2026-03-22
Versión: 1.0.0
