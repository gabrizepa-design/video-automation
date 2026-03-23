# 🤖 CLAUDE.md - Video Automation System

## 🎯 PROPÓSITO DEL PROYECTO

Sistema 100% automatizado que transforma guiones Markdown de **ViralScout** en videos profesionales de YouTube Shorts (50-60s).

**Workflow completo:**
```
ViralScout .md → File Watcher → n8n → Claude API → Runway → ElevenLabs → Whisper → Remotion → Google Drive → Telegram → YouTube
```

---

## 📂 ESTRUCTURA DEL PROYECTO

```
/root/video-automation/
├── docker-compose.yml          ← Orquestación de todos los servicios
├── .env                         ← TODAS las API keys y configuración
├── .env.example                 ← Template de variables de entorno
├── README.md                    ← Documentación principal
├── CLAUDE.md                    ← Este archivo (contexto para Claude)
├── ARCHITECTURE.md              ← Arquitectura técnica detallada
├── SETUP.md                     ← Guía de instalación paso a paso
│
├── n8n_data/                    ← Datos de n8n (workflows, credenciales)
│   └── workflows/
│       ├── main-pipeline.json           # Workflow principal
│       ├── telegram-approval.json       # Sistema de aprobación
│       └── youtube-upload.json          # Upload a YouTube
│
├── file-watcher/                ← Monitor de carpeta ViralScout
│   ├── Dockerfile
│   ├── package.json
│   ├── watcher.js               # Detecta nuevos .md
│   └── parser.js                # Parser de Markdown → JSON
│
├── remotion-project/            ← Render de video con React
│   ├── Dockerfile
│   ├── package.json
│   ├── remotion.config.ts
│   ├── render-video.js          # CLI para render
│   ├── src/
│   │   ├── Root.tsx             # Entry point
│   │   ├── Video.tsx            # Composición principal
│   │   ├── Scene.tsx            # Componente genérico de escena
│   │   ├── Subtitles.tsx        # Subtítulos animados palabra por palabra
│   │   ├── Transition.tsx       # Transiciones (fade, dissolve, wipe)
│   │   └── types.ts             # TypeScript interfaces
│   └── public/
│       └── assets/              # Assets estáticos (fuentes, iconos)
│
├── scripts/                     ← Scripts auxiliares
│   ├── install.sh               # Instalación completa del sistema
│   ├── test-apis.js             # Test de todas las APIs
│   ├── test-system.sh           # Test end-to-end
│   ├── setup-google-auth.js     # OAuth Google (Drive + YouTube)
│   ├── cleanup-temp.sh          # Limpieza de archivos temporales
│   └── deploy.sh                # Deploy a producción
│
├── temp_videos/                 ← Videos temporales (LIMPIABLE)
│   ├── scenes/                  # Escenas individuales de Runway
│   ├── audio/                   # Audio de ElevenLabs
│   ├── subtitles/               # JSON de Whisper
│   └── final/                   # Videos renderizados finales
│
└── postgres_data/               ← Persistencia de PostgreSQL
```

---

## 🔑 VARIABLES DE ENTORNO CRÍTICAS

```bash
# APIs principales
ANTHROPIC_API_KEY=sk-ant-xxx      # Claude para análisis
RUNWAY_API_KEY=xxx                # Runway Gen-3 para videos
ELEVENLABS_API_KEY=xxx            # ElevenLabs para voz
OPENAI_API_KEY=sk-xxx             # Whisper para subtítulos

# Google (Drive + YouTube)
GOOGLE_CLIENT_ID=xxx.apps.googleusercontent.com
GOOGLE_CLIENT_SECRET=xxx
GOOGLE_REFRESH_TOKEN=xxx
GDRIVE_PENDING_FOLDER_ID=xxx      # Carpeta "Videos Pendientes"
GDRIVE_APPROVED_FOLDER_ID=xxx     # Carpeta "Videos Aprobados"

# Telegram
TELEGRAM_BOT_TOKEN=xxx            # Bot para aprobación
TELEGRAM_CHAT_ID=xxx              # ID de Gabriel

# n8n
N8N_PASSWORD=xxx
POSTGRES_PASSWORD=xxx
```

Ver `.env.example` para la lista completa.

---

## 🎬 FLUJO DE DATOS

### **INPUT**
Archivo Markdown en: `C:\Users\gabri\Desktop\proyectos vs codes\VIralit\`

Ejemplo: `eric_anti-burnout_20260322_164509.md`

**Formato del guion:**
```markdown
# Título del Video

**Hook:** Texto del hook

**Estructura:** 
0-8s: Hook
8-30s: Desarrollo
...

**Guion:**

[0-5s] Texto de narración
VISUAL: Descripción visual

[5-15s] Más narración
VISUAL: Otra descripción
```

### **PROCESAMIENTO**

1. **File Watcher** detecta nuevo .md
2. **Parser** convierte MD → JSON estructurado
3. **n8n** recibe JSON via webhook
4. **Claude API** analiza qué escenas necesitan animación
5. **Runway Gen-3** genera videos para cada escena
6. **ElevenLabs** genera voz narrada completa
7. **Whisper** transcribe con timestamps palabra por palabra
8. **Remotion** renderiza video final (escenas + audio + subs)
9. **Google Drive** almacena video
10. **Telegram** notifica a Gabriel con preview
11. **Manual:** Gabriel aprueba/rechaza via Telegram
12. **YouTube** upload automático si aprobado

### **OUTPUT**

Video final:
- Formato: MP4 (H.264)
- Resolución: 1080x1920 (9:16 vertical)
- FPS: 30
- Duración: 50-60 segundos
- Audio: AAC
- Subtítulos: Quemados en video, palabra por palabra

---

## 🛠️ COMANDOS PRINCIPALES

### **Development**
```bash
# Levantar servicios
docker-compose up -d

# Ver logs en tiempo real
docker-compose logs -f

# Reiniciar un servicio específico
docker-compose restart remotion-renderer

# Parar todo
docker-compose down
```

### **Testing**
```bash
# Test completo del sistema
./scripts/test-system.sh

# Test solo APIs
node scripts/test-apis.js

# Test manual con archivo de ejemplo
cp example.md /mnt/c/Users/gabri/Desktop/proyectos\ vs\ codes/VIralit/
```

### **Maintenance**
```bash
# Limpiar videos temporales
./scripts/cleanup-temp.sh

# Ver espacio en disco
df -h

# Backup de datos
tar -czf backup-$(date +%Y%m%d).tar.gz n8n_data/ postgres_data/
```

---

## 🐛 DEBUGGING COMÚN

### **File Watcher no detecta archivos**
```bash
# Ver logs
docker logs video_automation_watcher -f

# Verificar mount
docker exec video_automation_watcher ls -la /watch

# Test manual
touch "/mnt/c/Users/gabri/Desktop/proyectos vs codes/VIralit/test.md"
```

### **n8n workflow falla**
```bash
# Logs de n8n
docker logs video_automation_n8n -f

# Acceder a UI
# http://vps-ip:5678

# Revisar ejecuciones fallidas en:
# Executions → Failed
```

### **Remotion no renderiza**
```bash
# Logs
docker logs video_automation_remotion -f

# Test de render manual
docker exec -it video_automation_remotion \
  node render-video.js --test

# Verificar RAM disponible
free -h
```

### **APIs fallan**
```bash
# Test de APIs
node scripts/test-apis.js

# Verificar API keys
grep API_KEY .env
```

---

## 📚 ARCHIVOS IMPORTANTES PARA CLAUDE

Cuando Claude necesite entender el sistema:

1. **CLAUDE.md** (este archivo) - Overview general
2. **ARCHITECTURE.md** - Detalles técnicos de arquitectura
3. **PROMPT_MAESTRO_VIDEO_AUTOMATION.md** - Documentación completa
4. **file-watcher/parser.js** - Cómo se parsean los guiones
5. **remotion-project/src/Video.tsx** - Lógica de renderizado
6. **n8n_data/workflows/*.json** - Workflows de n8n

---

## 🚨 REGLAS CRÍTICAS

### **NUNCA hacer:**
- ❌ Commitear .env al repo (usar .env.example)
- ❌ Exponer API keys en logs
- ❌ Modificar n8n_data/ manualmente (usar UI de n8n)
- ❌ Borrar temp_videos/ mientras hay renders en proceso

### **SIEMPRE hacer:**
- ✅ Usar docker-compose para gestionar servicios
- ✅ Test con `test-system.sh` después de cambios
- ✅ Revisar logs antes de reportar bugs
- ✅ Backup de n8n_data/ antes de updates grandes

---

## 🎯 TAREAS COMUNES

### **Agregar una nueva escena a Remotion**
1. Crear componente en `remotion-project/src/SceneX.tsx`
2. Importar en `Video.tsx`
3. Agregar en array de `<Sequence>`
4. Test: `docker-compose restart remotion-renderer`

### **Modificar el parser de guiones**
1. Editar `file-watcher/parser.js`
2. Test: `node parser.js test.md`
3. Rebuild: `docker-compose build file-watcher`
4. Restart: `docker-compose restart file-watcher`

### **Cambiar configuración de n8n**
1. Acceder a UI: http://vps-ip:5678
2. Modificar workflow
3. Exportar JSON
4. Guardar en `n8n_data/workflows/`
5. Commit cambios

### **Agregar nueva API**
1. Agregar key a `.env`
2. Agregar key a `.env.example` (sin valor)
3. Agregar test en `scripts/test-apis.js`
4. Documentar en este archivo
5. Update `docker-compose.yml` si es necesario

---

## 💰 COSTOS Y LÍMITES

| Servicio | Límite/mes | Costo estimado |
|----------|-----------|----------------|
| Runway Gen-3 | Sin límite | $21 (30 videos) |
| ElevenLabs | 100k chars | $3 |
| Whisper | Sin límite | $1.50 |
| Claude API | Sin límite | $15 |
| Google Drive | 15GB gratis | $0 |
| YouTube | Sin límite | $0 |

**Total por 30 videos: ~$40-45/mes**

---

## 🔐 SEGURIDAD

- Todas las API keys en `.env` (nunca en código)
- `.env` en `.gitignore`
- OAuth tokens renovados automáticamente
- Telegram bot solo responde a TELEGRAM_CHAT_ID
- Google Drive con permisos limitados
- n8n protegido con HTTP Basic Auth

---

## 📊 MÉTRICAS Y MONITOREO

### **Ver estadísticas de uso**
```bash
# Videos generados hoy
find temp_videos/final -name "*.mp4" -mtime -1 | wc -l

# Espacio usado
du -sh temp_videos/

# Logs de errores en últimas 24h
docker-compose logs --since 24h | grep ERROR
```

### **Health checks**
```bash
# n8n
curl http://localhost:5678/healthz

# File watcher
docker inspect video_automation_watcher | grep Status

# Remotion
docker exec video_automation_remotion remotion --version
```

---

## 🆘 CONTACTO Y SOPORTE

**Creador:** Gabriel
**VPS:** Hostinger (8GB RAM, Ubuntu 22.04)
**Ubicación:** Dublin, Ireland

**Recursos externos:**
- n8n Docs: https://docs.n8n.io/
- Remotion Docs: https://www.remotion.dev/docs/
- Runway API: https://docs.runwayml.com/
- ElevenLabs API: https://elevenlabs.io/docs/

---

## 📝 CHANGELOG

### v1.0.0 (2026-03-22)
- ✅ Sistema inicial completo
- ✅ File watcher funcionando
- ✅ Parser de guiones ViralScout
- ✅ Integración con todas las APIs
- ✅ Render con Remotion
- ✅ Sistema de aprobación por Telegram
- ✅ Upload automático a YouTube

---

## 🔌 INTEGRACIÓN CON MCP PARA CONSTRUCCIÓN DE WORKFLOWS N8N

### **OBJETIVO**
Este proyecto usa **VS Code + Claude Extension + MCP** para construir workflows de n8n de alta calidad directamente desde VS Code, con acceso remoto al VPS donde corre n8n.

### **HERRAMIENTAS MCP DISPONIBLES**

1. **Servidor MCP de n8n**
   - Repositorio: https://github.com/czlonkowski/n8n-mcp.git
   - Propósito: Comunicación directa con la API de n8n
   - Permite: Crear, modificar, ejecutar workflows desde VS Code

2. **Skills de n8n**
   - Repositorio: https://github.com/czlonkowski/n8n-skills.git
   - Propósito: Biblioteca de patrones y mejores prácticas
   - Permite: Generar workflows complejos con patrones probados

### **CONFIGURACIÓN MCP**

Después de instalar el proyecto, configurar en VS Code:

```json
// En configuración de Claude Extension o .vscode/settings.json
{
  "mcp": {
    "n8n": {
      "server": "https://github.com/czlonkowski/n8n-mcp.git",
      "skills": "https://github.com/czlonkowski/n8n-skills.git"
    }
  }
}
```

### **CREDENCIALES NECESARIAS**

Para que Claude pueda crear workflows directamente:

```bash
# Agregar a .env
N8N_API_URL=http://tu-vps-ip:5678/api/v1
N8N_API_KEY=n8n_api_xxxxxxxxxxxxx

# O si usas dominio con HTTPS:
N8N_API_URL=https://tu-dominio.com/api/v1
N8N_API_KEY=n8n_api_xxxxxxxxxxxxx
```

**Obtener API Key de n8n:**
```
1. Acceder a n8n UI: http://vps-ip:5678
2. Settings → API → Create API Key
3. Copiar key a .env → N8N_API_KEY
```

### **CÓMO USAR DESDE VS CODE**

Una vez configurado MCP, puedes pedirle a Claude:

```
"Claude, crea un workflow en n8n que:
1. Detecte nuevos archivos en la carpeta de ViralScout
2. Parse el contenido Markdown
3. Llame a Claude API para análisis
4. Ejecute Runway Gen-3 para generar videos
5. Renderice con Remotion
6. Suba a Google Drive
7. Notifique por Telegram"
```

Claude usará:
- ✅ El servidor MCP para comunicarse con n8n
- ✅ Los skills para aplicar mejores prácticas
- ✅ Tu API key para crear el workflow directamente
- ✅ Este archivo (CLAUDE.md) para entender el contexto del proyecto

### **EJEMPLO DE INTERACCIÓN**

```
Usuario: "Necesito un workflow que llame a Claude API cuando 
         llegue un webhook con datos de ViralScout"

Claude: [Usa MCP n8n]
        ✅ Creado workflow "viralscout-claude-analysis"
        ✅ Nodos agregados:
           - Webhook Trigger (POST /webhook/new-script)
           - HTTP Request (Anthropic Claude API)
           - Function (Parser de respuesta)
        ✅ URL del workflow: http://vps-ip:5678/workflow/123
        
        ¿Quieres que lo active?
```

### **FLUJO DE TRABAJO CON MCP**

```
1. TÚ abres VS Code en el proyecto
2. TÚ escribes: "Claude, crea un workflow para X"
3. CLAUDE lee CLAUDE.md (entiende el contexto)
4. CLAUDE usa MCP n8n server (conecta con tu n8n)
5. CLAUDE usa n8n skills (aplica mejores prácticas)
6. CLAUDE crea el workflow en tu instancia
7. CLAUDE te muestra el resultado
8. TÚ pruebas y refinamos juntos
```

### **VENTAJAS DE ESTE ENFOQUE**

- ✅ No necesitas aprender n8n en profundidad
- ✅ Claude construye workflows complejos en segundos
- ✅ Aplica mejores prácticas automáticamente
- ✅ Puedes iterar rápidamente
- ✅ Todo desde VS Code, sin salir del editor
- ✅ Acceso remoto a tu VPS transparente

### **INSTALACIÓN DE MCP (Pasos siguientes)**

Después de revisar este archivo:

1. Instalar servidor MCP de n8n en el proyecto
2. Instalar skills de n8n en el proyecto
3. Configurar credenciales (N8N_API_URL, N8N_API_KEY)
4. Test de conexión con n8n
5. Crear primer workflow como prueba

### **CONVENCIONES DE NOMBRES PARA WORKFLOWS**

```
Prefijo por categoría:
- video_* : Workflows de generación de video
- telegram_* : Workflows de interacción con Telegram
- youtube_* : Workflows de YouTube
- analysis_* : Workflows de análisis con Claude
- storage_* : Workflows de almacenamiento (Drive)

Ejemplos:
- video_main_pipeline
- telegram_approval_handler
- youtube_auto_upload
- analysis_script_optimizer
- storage_gdrive_sync
```

---

**IMPORTANTE PARA CLAUDE:**

Cuando recibas una petición relacionada con este proyecto:

1. **Lee este archivo primero** para entender el contexto
2. **Consulta ARCHITECTURE.md** para detalles técnicos
3. **Revisa el código relevante** antes de hacer cambios
4. **Test tus cambios** con `test-system.sh`
5. **Documenta** cualquier cambio significativo aquí

**Cuando te pidan crear/modificar workflows de n8n:**

1. **Usa MCP n8n server** para comunicarte con la instancia
2. **Aplica n8n skills** para seguir mejores prácticas
3. **Integra con la arquitectura existente** (no crear workflows aislados)
4. **Usa las APIs y servicios ya configurados** (Claude, Runway, ElevenLabs, etc.)
5. **Sigue las convenciones de nombres** definidas arriba
6. **Test el workflow** antes de confirmar
7. **Documenta** el propósito y funcionamiento del workflow

Este sistema es crítico para la producción de videos de Gabriel. Cualquier cambio debe ser:
- ✅ Probado exhaustivamente
- ✅ Documentado
- ✅ Retrocompatible (cuando sea posible)
- ✅ Optimizado para costos de API
