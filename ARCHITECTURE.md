# 🏗️ ARCHITECTURE.md - Video Automation System

## 🎯 ARQUITECTURA TÉCNICA DETALLADA

Este documento describe la arquitectura técnica del sistema de automatización de videos, incluyendo decisiones de diseño, patrones, y consideraciones de escalabilidad.

---

## 📐 DIAGRAMA DE ARQUITECTURA

```
┌─────────────────────────────────────────────────────────────┐
│                      WINDOWS PC (Local)                      │
│  ViralScout genera guiones → C:\...\VIralit\*.md            │
└─────────────────────────────────────────────────────────────┘
                           │ (WSL2 mount)
                           ▼
┌─────────────────────────────────────────────────────────────┐
│                     VPS (Ubuntu 22.04)                       │
│  ┌───────────────────────────────────────────────────────┐  │
│  │              Docker Network: video-automation         │  │
│  │                                                        │  │
│  │  ┌──────────────┐  ┌──────────────┐  ┌────────────┐ │  │
│  │  │ File Watcher │  │     n8n      │  │ PostgreSQL │ │  │
│  │  │  (Node.js)   │  │ (Orchestrator)│  │   (DB)    │ │  │
│  │  └──────┬───────┘  └──────┬───────┘  └─────▲──────┘ │  │
│  │         │                  │                 │        │  │
│  │         │ Webhook          │                 │        │  │
│  │         └─────────────────►│                 │        │  │
│  │                            │ Persist ────────┘        │  │
│  │                            │                          │  │
│  │  ┌─────────────────────────▼──────────────────────┐  │  │
│  │  │           Remotion Renderer (Node.js)         │  │  │
│  │  │  - FFmpeg                                      │  │  │
│  │  │  - Chromium                                    │  │  │
│  │  │  - React components                            │  │  │
│  │  └────────────────────────────────────────────────┘  │  │
│  └────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────┘
                           │
              ┌────────────┴───────────┐
              ▼                        ▼
    ┌──────────────────┐    ┌──────────────────┐
    │   External APIs  │    │   External APIs  │
    │   (Generation)   │    │   (Storage)      │
    │                  │    │                  │
    │ • Claude API     │    │ • Google Drive   │
    │ • Runway Gen-3   │    │ • YouTube API    │
    │ • ElevenLabs     │    │ • Telegram Bot   │
    │ • Whisper        │    │                  │
    └──────────────────┘    └──────────────────┘
```

---

## 🔧 COMPONENTES PRINCIPALES

### **1. File Watcher (Node.js + Chokidar)**

**Responsabilidad:** Monitorear carpeta de ViralScout y detectar nuevos guiones.

**Tecnología:**
- Node.js 18+
- chokidar (file watching)
- axios (HTTP client)

**Flujo:**
```javascript
1. Watch /mnt/c/Users/gabri/.../VIralit/*.md
2. Detectar nuevo archivo (evento 'add' o 'change')
3. Esperar estabilización (awaitWriteFinish: 2s)
4. Leer contenido del archivo
5. Parser Markdown → JSON
6. POST a n8n webhook
7. Marcar archivo como procesado
8. Persistir lista de procesados en /tmp/processed_files.json
```

**Consideraciones:**
- Debe ignorar archivos ya procesados (evitar duplicados)
- Debe manejar errores de lectura (permisos, encoding)
- Debe reintentar webhook en caso de fallo (max 3 intentos)
- Debe soportar graceful shutdown (SIGTERM, SIGINT)

**Escalabilidad:**
- Actual: 1 instancia, polling cada 30s
- Futuro: Event-based con inotify (Linux native)

---

### **2. Parser de Guiones (parser.js)**

**Responsabilidad:** Convertir Markdown de ViralScout a JSON estructurado.

**Input:** Archivo .md con formato específico
```markdown
# Título
**Hook:** Texto
**Estructura:** ...
**Guion:**
[0-5s] Narración
VISUAL: Descripción
```

**Output:** JSON estructurado
```json
{
  "title": "Título del video",
  "hook": "Texto del hook",
  "scenes": [
    {
      "start": 0,
      "end": 5,
      "duration": 5,
      "narration": "Texto a narrar",
      "visual": "Descripción visual"
    }
  ],
  "totalDuration": 60,
  "sourceFile": "eric_anti-burnout_20260322_164509.md"
}
```

**Algoritmo de parsing:**
```javascript
1. Extraer título: /# (.+)/
2. Extraer hook: /\*\*Hook:\*\* (.+)/
3. Extraer retención: /\*\*Retención estimada:\*\* (.+)/
4. Extraer guion con regex:
   /\[(\d+)-(\d+)s\] (.+?)\nVISUAL: (.+?)(?=\[|$)/gs
5. Calcular duración de cada escena (end - start)
6. Validar que escenas sean consecutivas
7. Retornar objeto JSON
```

**Validaciones:**
- Título no vacío
- Al menos 1 escena
- Escenas ordenadas cronológicamente
- Sin gaps de tiempo entre escenas
- Duración total <= 90 segundos

---

### **3. n8n (Workflow Orchestrator)**

**Responsabilidad:** Orquestar todo el flujo de generación de videos.

**Tecnología:**
- n8n 1.30+
- PostgreSQL 14 (persistence)
- HTTP nodes para APIs externas
- Execute Command para Remotion

**Workflows principales:**

#### **main-pipeline.json**
```
1. Webhook Trigger (recibe JSON del file-watcher)
2. Function: Validate Input
3. HTTP Request: Claude API (análisis)
4. Split Into Items: Loop por cada escena
5. HTTP Request: Runway Gen-3 (generar video si needs_animation)
6. HTTP Request: ElevenLabs (generar voz)
7. HTTP Request: Whisper (transcribir)
8. Execute Command: Remotion render
9. Google Drive: Upload a "Pendientes"
10. Telegram: Notificar con preview
```

#### **telegram-approval.json**
```
1. Telegram Trigger: /aprobar [video_id]
2. Google Drive: Mover de "Pendientes" a "Aprobados"
3. Trigger: youtube-upload workflow
```

#### **youtube-upload.json**
```
1. Webhook Trigger (desde telegram-approval)
2. Google Drive: Download video
3. YouTube: Upload con metadata
4. Telegram: Notificar success
```

**Manejo de errores:**
- Retry automático: 3 intentos con backoff exponencial
- Error handling: Webhook de error a Telegram
- Timeout: 30 minutos por workflow
- State persistence: Cada nodo guarda su output en DB

---

### **4. Remotion Renderer**

**Responsabilidad:** Renderizar video final con React components.

**Tecnología:**
- Remotion 4.0+
- React 18+
- TypeScript 5+
- FFmpeg 6+
- Chromium (headless)

**Arquitectura de componentes:**

```typescript
<VideoComposition>                    // Root
  ├─ <Audio src={audioPath} />        // Audio track
  ├─ <Sequence from={0} duration={150}> // Escena 1
  │   └─ <Scene videoPath={...} />
  ├─ <Sequence from={150} duration={300}> // Escena 2
  │   ├─ <Scene videoPath={...} />
  │   └─ <Transition type="fade" />
  ├─ ...
  └─ <Subtitles words={...} />        // Overlay global
```

**Props dinámicos:**
```typescript
interface VideoProps {
  scenes: SceneData[];    // Videos de Runway
  audioPath: string;      // Audio de ElevenLabs
  subtitles: SubtitleWord[]; // Timestamps de Whisper
}
```

**Render pipeline:**
```bash
1. Bundle proyecto React (webpack)
2. Cargar composición "BurnoutVideo"
3. Inyectar props dinámicos
4. Render frame by frame (30fps × 60s = 1800 frames)
5. FFmpeg encode:
   - Codec: H.264
   - Bitrate: 5000k (alta calidad)
   - Audio: AAC 192k
   - Preset: fast (compromiso velocidad/calidad)
6. Output: /tmp/videos/final/video_TIMESTAMP.mp4
```

**Optimizaciones:**
- Concurrency: 4 threads paralelos
- Cache: Reutilizar escenas idénticas
- Progressive render: Mostrar progreso en logs
- Memory management: Limpiar frames después de encode

---

## 🔄 FLUJO DE DATOS DETALLADO

### **Fase 1: Detección y Parsing (5 segundos)**

```
File Watcher:
  ├─ Detecta: eric_anti-burnout_20260322_164509.md
  ├─ Lee contenido (UTF-8)
  ├─ Parsea Markdown → JSON
  ├─ Valida estructura
  └─ POST http://n8n:5678/webhook/new-script
      Body: { title, hook, scenes, totalDuration }
```

### **Fase 2: Análisis con IA (10 segundos)**

```
n8n → Claude API:
  Request:
    POST https://api.anthropic.com/v1/messages
    Body: {
      model: "claude-sonnet-4-20250514",
      messages: [{
        role: "user",
        content: "Analiza este guion..."
      }]
    }
  
  Response:
    {
      scenes_analysis: [
        {
          scene_id: 1,
          needs_animation: false,  // Imagen estática OK
          optimized_prompt: "...",
          transition: "fade"
        },
        {
          scene_id: 2,
          needs_animation: true,   // Requiere video
          optimized_prompt: "Improved prompt for Runway",
          transition: "dissolve"
        }
      ]
    }
```

### **Fase 3: Generación de Contenido (5-10 minutos)**

**Paralelo A: Videos (Runway Gen-3)**
```
Para cada escena con needs_animation=true:

Request:
  POST https://api.runwayml.com/v1/generate
  Body: {
    prompt: scene.optimized_prompt,
    duration: scene.duration,
    aspect_ratio: "9:16",
    model: "gen3"
  }

Response:
  { task_id: "abc123" }

Poll hasta complete:
  GET https://api.runwayml.com/v1/tasks/abc123
  Response: { status: "completed", video_url: "..." }

Download:
  GET video_url → /tmp/videos/scenes/scene_2.mp4
```

**Paralelo B: Audio (ElevenLabs)**
```
Request:
  POST https://api.elevenlabs.io/v1/text-to-speech/{voice_id}
  Body: {
    text: "Escena 1... Escena 2... Escena 3...",
    model_id: "eleven_multilingual_v2",
    voice_settings: { stability: 0.7, similarity_boost: 0.8 }
  }

Response:
  Binary audio stream (MP3)

Save:
  /tmp/videos/audio/audio_TIMESTAMP.mp3
```

### **Fase 4: Subtítulos (1 minuto)**

```
Request:
  POST https://api.openai.com/v1/audio/transcriptions
  FormData: {
    file: audio_TIMESTAMP.mp3,
    model: "whisper-1",
    response_format: "verbose_json",
    timestamp_granularities: ["word"]
  }

Response:
  {
    words: [
      { word: "Dos", start: 0.0, end: 0.3 },
      { word: "semanas", start: 0.3, end: 0.8 },
      { word: "antes", start: 0.8, end: 1.2 },
      ...
    ]
  }

Save:
  /tmp/videos/subtitles/subs_TIMESTAMP.json
```

### **Fase 5: Render (3-5 minutos)**

```
Execute Command:
  node /app/render-video.js \
    --config /tmp/video-config.json \
    --output /tmp/videos/final/video_TIMESTAMP.mp4

video-config.json:
  {
    "scenes": [
      { "id": 1, "videoPath": "/tmp/videos/scenes/scene_1.mp4", "duration": 5 },
      { "id": 2, "videoPath": "/tmp/videos/scenes/scene_2.mp4", "duration": 10 }
    ],
    "audioPath": "/tmp/videos/audio/audio_TIMESTAMP.mp3",
    "subtitles": [...],
    "outputPath": "/tmp/videos/final/video_TIMESTAMP.mp4"
  }

Remotion Process:
  1. Bundle React project
  2. Load composition
  3. Inject props
  4. Render 1800 frames @ 30fps
  5. FFmpeg encode
  6. Output video

Duration: ~3-5 minutes (depende de CPU)
```

### **Fase 6: Storage y Notificación (30 segundos)**

```
Google Drive Upload:
  POST https://www.googleapis.com/upload/drive/v3/files
  Body: video_TIMESTAMP.mp4
  Metadata: {
    name: "PENDIENTE_titulo_TIMESTAMP.mp4",
    parents: [GDRIVE_PENDING_FOLDER_ID]
  }

Response:
  {
    id: "1a2b3c4d5e",
    webViewLink: "https://drive.google.com/file/d/1a2b3c4d5e/view"
  }

Telegram Notification:
  POST https://api.telegram.org/bot{token}/sendMessage
  Body: {
    chat_id: TELEGRAM_CHAT_ID,
    text: "🎬 Nuevo video...\n✅ /aprobar 1a2b3c4d5e"
  }

  POST https://api.telegram.org/bot{token}/sendVideo
  FormData: {
    chat_id: TELEGRAM_CHAT_ID,
    video: video_TIMESTAMP.mp4,
    caption: "Preview del video"
  }
```

### **Fase 7: Aprobación Manual (Variable)**

```
Usuario envía: /aprobar 1a2b3c4d5e

Telegram Webhook:
  POST http://n8n:5678/webhook/telegram-command
  Body: { command: "aprobar", video_id: "1a2b3c4d5e" }

n8n Workflow:
  1. Google Drive: Move file
     From: GDRIVE_PENDING_FOLDER_ID
     To: GDRIVE_APPROVED_FOLDER_ID
  
  2. Trigger: youtube-upload workflow
     Webhook: http://n8n:5678/webhook/youtube-upload
     Body: { video_id: "1a2b3c4d5e" }
```

### **Fase 8: Upload a YouTube (2-5 minutos)**

```
YouTube Upload:
  POST https://www.googleapis.com/upload/youtube/v3/videos
  Metadata: {
    snippet: {
      title: "Título del video",
      description: "Descripción generada...",
      tags: ["shorts", "salud", "burnout"],
      categoryId: "22"
    },
    status: {
      privacyStatus: "private"
    }
  }
  Body: video_TIMESTAMP.mp4

Response:
  {
    id: "abc123xyz",
    snippet: { title: "..." }
  }

Telegram Notification:
  "✅ Video subido: https://youtube.com/watch?v=abc123xyz"
```

---

## 🔐 SEGURIDAD Y AUTENTICACIÓN

### **Google OAuth2 Flow**

```
1. Setup inicial (una vez):
   - Crear proyecto en Google Cloud Console
   - Habilitar Drive API + YouTube API
   - Crear OAuth2 credentials
   - Obtener client_id + client_secret

2. Obtener refresh_token:
   node scripts/setup-google-auth.js
   - Abre navegador con consent screen
   - Usuario aprueba permisos
   - Script recibe authorization code
   - Exchange code por refresh_token
   - Guardar en .env

3. Uso en runtime:
   - n8n usa refresh_token para obtener access_token
   - Access tokens expiran en 1 hora
   - Refresh automático cuando expira
```

### **API Keys Management**

```
Todas las keys en .env:
  ✅ Nunca en código
  ✅ Nunca en logs
  ✅ .env en .gitignore
  ✅ .env.example sin valores reales

Rotación de keys:
  - Cada 90 días (calendario)
  - Inmediatamente si compromiso sospechado
  - Proceso: Update .env → Restart servicios
```

### **Telegram Bot Security**

```
1. Bot solo responde a TELEGRAM_CHAT_ID específico
2. Comandos requieren video_id válido
3. video_id verificado contra Google Drive
4. Rate limiting: Max 10 comandos/minuto
```

---

## 📊 ESCALABILIDAD Y PERFORMANCE

### **Capacidad Actual**

```
Hardware:
  - VPS: 8GB RAM, 4 vCPU
  - Storage: 160GB SSD

Límites:
  - Videos concurrentes: 1 (Remotion single-threaded)
  - Queue size: Ilimitado (PostgreSQL)
  - Throughput: ~6 videos/hora

Bottlenecks:
  1. Remotion render (3-5 min/video)
  2. Runway Gen-3 (2-3 min/video con polling)
  3. Network I/O (download videos de Runway)
```

### **Optimizaciones Implementadas**

```
1. Paralelización:
   - Runway + ElevenLabs en paralelo
   - Download de múltiples escenas en paralelo

2. Caching:
   - File watcher: processed_files.json
   - Remotion: Reuse identical scenes
   - n8n: Cache de API responses (5 min TTL)

3. Resource management:
   - Cleanup automático de /tmp cada 24h
   - Log rotation (max 100MB)
   - Docker restart policies
```

### **Plan de Escalabilidad**

```
Fase 2 (10-20 videos/día):
  - Upgrade VPS: 16GB RAM
  - Add Redis para queue management
  - Remotion worker pool (2-3 workers)

Fase 3 (50+ videos/día):
  - Kubernetes cluster (3 nodes)
  - Separate Remotion workers (auto-scale)
  - CDN para asset distribution
  - Dedicated database server

Fase 4 (100+ videos/día):
  - Multi-region deployment
  - Load balancer
  - Dedicated queue system (RabbitMQ)
  - Monitoring & alerting (Prometheus + Grafana)
```

---

## 🧪 TESTING STRATEGY

### **Unit Tests**

```
file-watcher/parser.test.js:
  ✓ Parse valid markdown
  ✓ Handle missing sections
  ✓ Validate timestamps
  ✓ Extract all scenes

remotion-project/src/__tests__/Video.test.tsx:
  ✓ Render with all scenes
  ✓ Apply transitions correctly
  ✓ Sync audio
  ✓ Display subtitles
```

### **Integration Tests**

```
scripts/test-system.sh:
  1. Docker health checks
  2. API connectivity tests
  3. End-to-end test con guion de ejemplo
  4. Verify video output quality
```

### **Load Tests**

```
k6 script:
  - Simulate 10 guiones simultáneos
  - Measure throughput
  - Identify bottlenecks
  - Memory leak detection
```

---

## 📈 MONITOREO Y OBSERVABILIDAD

### **Logs**

```
Centralizados con Docker:
  docker-compose logs -f

Levels:
  - ERROR: Fallos críticos
  - WARN: Degradación
  - INFO: Eventos importantes
  - DEBUG: Debugging (solo dev)

Retention:
  - 7 días en disco
  - Rotación automática
```

### **Métricas**

```
Actuales (básicas):
  - Videos generados/día
  - Tiempo promedio de render
  - Tasa de errores

Futuras (Prometheus):
  - API response times
  - Queue depth
  - Resource utilization
  - Error rates por componente
```

### **Alertas**

```
Telegram notifications para:
  - Workflow failures
  - API rate limits exceeded
  - Disk space < 10GB
  - High error rate (>10% en 1h)
```

---

## 🔄 CI/CD (Futuro)

```
GitHub Actions:
  1. On push to main:
     - Run tests
     - Build Docker images
     - Push to registry
     - Deploy to VPS
     - Health check
     - Rollback on failure

  2. On PR:
     - Run tests
     - Lint code
     - Build images (no push)
```

---

## 📚 REFERENCIAS TÉCNICAS

- **Docker Networking:** https://docs.docker.com/network/
- **n8n Webhooks:** https://docs.n8n.io/integrations/builtin/core-nodes/n8n-nodes-base.webhook/
- **Remotion Architecture:** https://www.remotion.dev/docs/architecture
- **FFmpeg Encoding:** https://trac.ffmpeg.org/wiki/Encode/H.264
- **Google OAuth2:** https://developers.google.com/identity/protocols/oauth2

---

Documento actualizado: 2026-03-22
Versión: 1.0.0
