import json
import urllib.request
import urllib.error
import os

API_KEY = os.environ["N8N_API_KEY"]
BASE_URL = os.environ.get("N8N_API_URL", "https://noctisiops-n8n.gpsefe.easypanel.host/api/v1")
MAIN_PIPELINE_ID = "ziCIBzswAFMyPs1L"

def api_call(method, path, data=None):
    url = BASE_URL + path
    payload = json.dumps(data).encode("utf-8") if data else None
    req = urllib.request.Request(
        url, data=payload, method=method,
        headers={
            "X-N8N-API-KEY": API_KEY,
            "Content-Type": "application/json"
        }
    )
    try:
        with urllib.request.urlopen(req) as r:
            return json.loads(r.read())
    except urllib.error.HTTPError as e:
        body = e.read().decode()[:800]
        print(f"HTTP {e.code}: {body}")
        return None

# ============================================================
# WORKFLOW 1: video_main_pipeline (UPDATE existing)
# ============================================================
main_pipeline = {
    "name": "video_main_pipeline",
    "nodes": [
        {
            "id": "n1", "name": "Webhook - New Script",
            "type": "n8n-nodes-base.webhook", "typeVersion": 2,
            "position": [240, 300],
            "parameters": {
                "path": "new-script",
                "httpMethod": "POST",
                "responseMode": "responseNode"
            }
        },
        {
            "id": "n2", "name": "Parse Script Data",
            "type": "n8n-nodes-base.code", "typeVersion": 2,
            "position": [460, 300],
            "parameters": {
                "jsCode": (
                    "const data = $input.first().json.body || $input.first().json;\n"
                    "if (!data.title) throw new Error('Missing title');\n"
                    "return [{ json: {\n"
                    "  scriptId: 'script_' + Date.now(),\n"
                    "  title: data.title,\n"
                    "  hook: data.hook || '',\n"
                    "  scenes: data.scenes || [],\n"
                    "  narration: data.narration || '',\n"
                    "  filename: data.filename || 'unknown.md',\n"
                    "  timestamp: new Date().toISOString()\n"
                    "}}];"
                )
            }
        },
        {
            "id": "n3", "name": "Claude - Analyze Scenes",
            "type": "n8n-nodes-base.httpRequest", "typeVersion": 4.2,
            "position": [680, 300],
            "parameters": {
                "method": "POST",
                "url": "https://api.anthropic.com/v1/messages",
                "sendHeaders": True,
                "headerParameters": {"parameters": [
                    {"name": "x-api-key", "value": "={{ $env.ANTHROPIC_API_KEY }}"},
                    {"name": "anthropic-version", "value": "2023-06-01"},
                    {"name": "content-type", "value": "application/json"}
                ]},
                "sendBody": True,
                "specifyBody": "json",
                "jsonBody": (
                    '={{ JSON.stringify({'
                    'model:"claude-opus-4-6",'
                    'max_tokens:2048,'
                    'messages:[{role:"user",content:"Analiza este guion YouTube Short. '
                    'Para cada escena responde con JSON: {scenes:[{index,needsVideo,runwayPrompt,duration,visual}]}. '
                    'runwayPrompt en ingles max 512 chars. SOLO JSON sin texto adicional. '
                    'Guion: "+JSON.stringify($json)}]'
                    '}) }}'
                )
            }
        },
        {
            "id": "n4", "name": "Extract Claude Analysis",
            "type": "n8n-nodes-base.code", "typeVersion": 2,
            "position": [900, 300],
            "parameters": {
                "jsCode": (
                    "const resp = $input.first().json;\n"
                    "const text = resp.content[0].text;\n"
                    "let analysis;\n"
                    "try {\n"
                    "  const m = text.match(/```json\\n([\\s\\S]*?)\\n```/) || text.match(/(\\{[\\s\\S]*\\})/);\n"
                    "  analysis = JSON.parse(m ? (m[1] || m[0]) : text);\n"
                    "} catch(e) { analysis = { scenes: [], error: e.message }; }\n"
                    "const src = $node['Parse Script Data'].json;\n"
                    "return [{ json: {\n"
                    "  scriptId: src.scriptId, title: src.title,\n"
                    "  narration: src.narration, filename: src.filename,\n"
                    "  scenes: src.scenes, claudeAnalysis: analysis\n"
                    "}}];"
                )
            }
        },
        {
            "id": "n5", "name": "ElevenLabs - Generate Voice",
            "type": "n8n-nodes-base.httpRequest", "typeVersion": 4.2,
            "position": [1120, 300],
            "parameters": {
                "method": "POST",
                "url": '={{ "https://api.elevenlabs.io/v1/text-to-speech/" + $env.ELEVENLABS_VOICE_ID }}',
                "sendHeaders": True,
                "headerParameters": {"parameters": [
                    {"name": "xi-api-key", "value": "={{ $env.ELEVENLABS_API_KEY }}"},
                    {"name": "Content-Type", "value": "application/json"}
                ]},
                "sendBody": True,
                "specifyBody": "json",
                "jsonBody": (
                    '={{ JSON.stringify({'
                    'text:$json.narration,'
                    'model_id:$env.ELEVENLABS_MODEL_ID||"eleven_multilingual_v2",'
                    'voice_settings:{stability:0.5,similarity_boost:0.75,style:0.5,use_speaker_boost:true}'
                    '}) }}'
                ),
                "options": {"response": {"response": {"responseFormat": "file"}}}
            }
        },
        {
            "id": "n6", "name": "Whisper - Transcribe Audio",
            "type": "n8n-nodes-base.httpRequest", "typeVersion": 4.2,
            "position": [1340, 300],
            "parameters": {
                "method": "POST",
                "url": "https://api.openai.com/v1/audio/transcriptions",
                "sendHeaders": True,
                "headerParameters": {"parameters": [
                    {"name": "Authorization", "value": '={{ "Bearer " + $env.OPENAI_API_KEY }}'}
                ]},
                "sendBody": True,
                "contentType": "multipart-form-data",
                "bodyParameters": {"parameters": [
                    {"name": "file", "value": "={{ $binary.data }}", "parameterType": "formBinaryData"},
                    {"name": "model", "value": "whisper-1"},
                    {"name": "response_format", "value": "verbose_json"},
                    {"name": "timestamp_granularities[]", "value": "word"}
                ]}
            }
        },
        {
            "id": "n7", "name": "Merge Audio and Subtitles",
            "type": "n8n-nodes-base.code", "typeVersion": 2,
            "position": [1560, 300],
            "parameters": {
                "jsCode": (
                    "const whisperData = $input.first().json;\n"
                    "const scriptData = $node['Extract Claude Analysis'].json;\n"
                    "const subtitles = (whisperData.words || []).map(w => ({\n"
                    "  word: w.word, start: w.start, end: w.end\n"
                    "}));\n"
                    "const videoScenes = (scriptData.claudeAnalysis.scenes || []).filter(s => s.needsVideo);\n"
                    "return [{ json: {\n"
                    "  ...scriptData,\n"
                    "  subtitles,\n"
                    "  audioFile: $binary?.data ? 'audio_ready' : 'no_audio',\n"
                    "  videoScenes,\n"
                    "  readyForRunway: videoScenes.length > 0\n"
                    "}}];"
                )
            }
        },
        {
            "id": "n8", "name": "Runway - Generate Video",
            "type": "n8n-nodes-base.httpRequest", "typeVersion": 4.2,
            "position": [1780, 300],
            "parameters": {
                "method": "POST",
                "url": "https://api.dev.runwayml.com/v1/image_to_video",
                "sendHeaders": True,
                "headerParameters": {"parameters": [
                    {"name": "Authorization", "value": '={{ "Bearer " + $env.RUNWAY_API_KEY }}'},
                    {"name": "X-Runway-Version", "value": "2024-11-06"},
                    {"name": "Content-Type", "value": "application/json"}
                ]},
                "sendBody": True,
                "specifyBody": "json",
                "jsonBody": (
                    '={{ JSON.stringify({'
                    'promptText:($json.videoScenes[0]||{}).runwayPrompt||"cinematic video vertical format",'
                    'duration:10,'
                    'ratio:"720:1280",'
                    'model:"gen3a_turbo"'
                    '}) }}'
                )
            }
        },
        {
            "id": "n9", "name": "Wait for Runway",
            "type": "n8n-nodes-base.wait", "typeVersion": 1.1,
            "position": [2000, 300],
            "parameters": {"unit": "seconds", "amount": 30}
        },
        {
            "id": "n10", "name": "Check Runway Status",
            "type": "n8n-nodes-base.httpRequest", "typeVersion": 4.2,
            "position": [2220, 300],
            "parameters": {
                "method": "GET",
                "url": '={{ "https://api.dev.runwayml.com/v1/tasks/" + $json.id }}',
                "sendHeaders": True,
                "headerParameters": {"parameters": [
                    {"name": "Authorization", "value": '={{ "Bearer " + $env.RUNWAY_API_KEY }}'},
                    {"name": "X-Runway-Version", "value": "2024-11-06"}
                ]}
            }
        },
        {
            "id": "n11", "name": "Prepare Render Payload",
            "type": "n8n-nodes-base.code", "typeVersion": 2,
            "position": [2440, 300],
            "parameters": {
                "jsCode": (
                    "const runwayResult = $input.first().json;\n"
                    "const scriptData = $node['Extract Claude Analysis'].json;\n"
                    "const subtitles = $node['Merge Audio and Subtitles'].json.subtitles || [];\n"
                    "return [{ json: {\n"
                    "  scriptId: scriptData.scriptId,\n"
                    "  title: scriptData.title,\n"
                    "  filename: scriptData.filename,\n"
                    "  videoUrl: (runwayResult.output || [])[0] || '',\n"
                    "  runwayStatus: runwayResult.status,\n"
                    "  subtitles,\n"
                    "  renderPayload: {\n"
                    "    title: scriptData.title,\n"
                    "    scenes: scriptData.scenes,\n"
                    "    subtitles,\n"
                    "    videoUrl: (runwayResult.output || [])[0] || '',\n"
                    "    duration: 55,\n"
                    "    fps: 30\n"
                    "  }\n"
                    "}}];"
                )
            }
        },
        {
            "id": "n12", "name": "Telegram - Notify Gabriel",
            "type": "n8n-nodes-base.telegram", "typeVersion": 1.2,
            "position": [2660, 300],
            "parameters": {
                "operation": "sendMessage",
                "chatId": "={{ $env.TELEGRAM_CHAT_ID }}",
                "text": (
                    '={{ "🎬 *Video listo para revisar!*\\n\\n"'
                    '+ "📋 *Título:* " + $json.title + "\\n"'
                    '+ "📁 *Archivo:* " + $json.filename + "\\n\\n"'
                    '+ "✅ Aprobar: /aprobar_" + $json.scriptId + "\\n"'
                    '+ "❌ Rechazar: /rechazar_" + $json.scriptId }}'
                ),
                "additionalFields": {"parse_mode": "Markdown"}
            },
            "credentials": {"telegramApi": {"id": "telegram-bot", "name": "Telegram Bot"}}
        },
        {
            "id": "n13", "name": "Respond to Webhook",
            "type": "n8n-nodes-base.respondToWebhook", "typeVersion": 1.1,
            "position": [2880, 300],
            "parameters": {
                "respondWith": "json",
                "responseBody": '={{ JSON.stringify({status:"processing",scriptId:$node["Parse Script Data"].json.scriptId}) }}'
            }
        }
    ],
    "connections": {
        "Webhook - New Script": {"main": [[{"node": "Parse Script Data", "type": "main", "index": 0}]]},
        "Parse Script Data": {"main": [[{"node": "Claude - Analyze Scenes", "type": "main", "index": 0}]]},
        "Claude - Analyze Scenes": {"main": [[{"node": "Extract Claude Analysis", "type": "main", "index": 0}]]},
        "Extract Claude Analysis": {"main": [[{"node": "ElevenLabs - Generate Voice", "type": "main", "index": 0}]]},
        "ElevenLabs - Generate Voice": {"main": [[{"node": "Whisper - Transcribe Audio", "type": "main", "index": 0}]]},
        "Whisper - Transcribe Audio": {"main": [[{"node": "Merge Audio and Subtitles", "type": "main", "index": 0}]]},
        "Merge Audio and Subtitles": {"main": [[{"node": "Runway - Generate Video", "type": "main", "index": 0}]]},
        "Runway - Generate Video": {"main": [[{"node": "Wait for Runway", "type": "main", "index": 0}]]},
        "Wait for Runway": {"main": [[{"node": "Check Runway Status", "type": "main", "index": 0}]]},
        "Check Runway Status": {"main": [[{"node": "Prepare Render Payload", "type": "main", "index": 0}]]},
        "Prepare Render Payload": {"main": [[{"node": "Telegram - Notify Gabriel", "type": "main", "index": 0}]]},
        "Telegram - Notify Gabriel": {"main": [[{"node": "Respond to Webhook", "type": "main", "index": 0}]]}
    },
    "settings": {"executionOrder": "v1", "saveManualExecutions": True}
}

# ============================================================
# WORKFLOW 2: telegram_approval_handler
# ============================================================
telegram_workflow = {
    "name": "telegram_approval_handler",
    "nodes": [
        {
            "id": "t1", "name": "Telegram Trigger",
            "type": "n8n-nodes-base.telegramTrigger", "typeVersion": 1.1,
            "position": [240, 300],
            "parameters": {
                "updates": ["message"],
                "additionalFields": {}
            },
            "credentials": {"telegramApi": {"id": "telegram-bot", "name": "Telegram Bot"}}
        },
        {
            "id": "t2", "name": "Parse Command",
            "type": "n8n-nodes-base.code", "typeVersion": 2,
            "position": [460, 300],
            "parameters": {
                "jsCode": (
                    "const msg = $input.first().json.message;\n"
                    "const text = msg?.text || '';\n"
                    "const chatId = msg?.chat?.id?.toString() || '';\n"
                    "const allowedChatId = $env.TELEGRAM_CHAT_ID;\n"
                    "if (chatId !== allowedChatId) {\n"
                    "  return [{ json: { authorized: false, action: 'ignore' }}];\n"
                    "}\n"
                    "const approveMatch = text.match(/^\\/aprobar_(.+)$/);\n"
                    "const rejectMatch = text.match(/^\\/rechazar_(.+)$/);\n"
                    "if (approveMatch) {\n"
                    "  return [{ json: { authorized: true, action: 'approve', scriptId: approveMatch[1], chatId }}];\n"
                    "} else if (rejectMatch) {\n"
                    "  return [{ json: { authorized: true, action: 'reject', scriptId: rejectMatch[1], chatId }}];\n"
                    "}\n"
                    "return [{ json: { authorized: true, action: 'unknown', text, chatId }}];"
                )
            }
        },
        {
            "id": "t3", "name": "Check Action",
            "type": "n8n-nodes-base.switch", "typeVersion": 3,
            "position": [680, 300],
            "parameters": {
                "mode": "rules",
                "rules": {
                    "values": [
                        {"conditions": {"options": {"leftValue": "", "caseSensitive": True}, "conditions": [{"id": "c1", "leftValue": "={{ $json.action }}", "rightValue": "approve", "operator": {"type": "string", "operation": "equals"}}]}, "renameOutput": True, "outputKey": "approve"},
                        {"conditions": {"options": {"leftValue": "", "caseSensitive": True}, "conditions": [{"id": "c2", "leftValue": "={{ $json.action }}", "rightValue": "reject", "operator": {"type": "string", "operation": "equals"}}]}, "renameOutput": True, "outputKey": "reject"}
                    ]
                }
            }
        },
        {
            "id": "t4", "name": "Move to Approved Drive",
            "type": "n8n-nodes-base.googleDrive", "typeVersion": 3,
            "position": [900, 200],
            "parameters": {
                "operation": "move",
                "fileId": {"__rl": True, "value": "={{ $json.scriptId }}", "mode": "id"},
                "folderId": {"__rl": True, "value": "={{ $env.GDRIVE_APPROVED_FOLDER_ID }}", "mode": "id"},
                "options": {}
            },
            "credentials": {"googleDriveOAuth2Api": {"id": "google-oauth", "name": "Google OAuth2"}}
        },
        {
            "id": "t5", "name": "Trigger YouTube Upload",
            "type": "n8n-nodes-base.httpRequest", "typeVersion": 4.2,
            "position": [1120, 200],
            "parameters": {
                "method": "POST",
                "url": '={{ $env.WEBHOOK_URL + "webhook/upload-youtube" }}',
                "sendBody": True,
                "specifyBody": "json",
                "jsonBody": '={{ JSON.stringify({scriptId:$json.scriptId,approved:true}) }}'
            }
        },
        {
            "id": "t6", "name": "Confirm Approval to Gabriel",
            "type": "n8n-nodes-base.telegram", "typeVersion": 1.2,
            "position": [1340, 200],
            "parameters": {
                "operation": "sendMessage",
                "chatId": "={{ $env.TELEGRAM_CHAT_ID }}",
                "text": '={{ "✅ Video *" + $node[\"Parse Command\"].json.scriptId + "* aprobado!\\n🚀 Subiendo a YouTube..." }}',
                "additionalFields": {"parse_mode": "Markdown"}
            },
            "credentials": {"telegramApi": {"id": "telegram-bot", "name": "Telegram Bot"}}
        },
        {
            "id": "t7", "name": "Move to Rejected Drive",
            "type": "n8n-nodes-base.googleDrive", "typeVersion": 3,
            "position": [900, 400],
            "parameters": {
                "operation": "move",
                "fileId": {"__rl": True, "value": "={{ $json.scriptId }}", "mode": "id"},
                "folderId": {"__rl": True, "value": "={{ $env.GDRIVE_REJECTED_FOLDER_ID }}", "mode": "id"},
                "options": {}
            },
            "credentials": {"googleDriveOAuth2Api": {"id": "google-oauth", "name": "Google OAuth2"}}
        },
        {
            "id": "t8", "name": "Confirm Rejection to Gabriel",
            "type": "n8n-nodes-base.telegram", "typeVersion": 1.2,
            "position": [1120, 400],
            "parameters": {
                "operation": "sendMessage",
                "chatId": "={{ $env.TELEGRAM_CHAT_ID }}",
                "text": '={{ "❌ Video *" + $node[\"Parse Command\"].json.scriptId + "* rechazado y archivado." }}',
                "additionalFields": {"parse_mode": "Markdown"}
            },
            "credentials": {"telegramApi": {"id": "telegram-bot", "name": "Telegram Bot"}}
        }
    ],
    "connections": {
        "Telegram Trigger": {"main": [[{"node": "Parse Command", "type": "main", "index": 0}]]},
        "Parse Command": {"main": [[{"node": "Check Action", "type": "main", "index": 0}]]},
        "Check Action": {
            "main": [
                [{"node": "Move to Approved Drive", "type": "main", "index": 0}],
                [{"node": "Move to Rejected Drive", "type": "main", "index": 0}]
            ]
        },
        "Move to Approved Drive": {"main": [[{"node": "Trigger YouTube Upload", "type": "main", "index": 0}]]},
        "Trigger YouTube Upload": {"main": [[{"node": "Confirm Approval to Gabriel", "type": "main", "index": 0}]]},
        "Move to Rejected Drive": {"main": [[{"node": "Confirm Rejection to Gabriel", "type": "main", "index": 0}]]}
    },
    "settings": {"executionOrder": "v1", "saveManualExecutions": True}
}

# ============================================================
# WORKFLOW 3: youtube_auto_upload
# ============================================================
youtube_workflow = {
    "name": "youtube_auto_upload",
    "nodes": [
        {
            "id": "y1", "name": "Webhook - Upload Trigger",
            "type": "n8n-nodes-base.webhook", "typeVersion": 2,
            "position": [240, 300],
            "parameters": {
                "path": "upload-youtube",
                "httpMethod": "POST",
                "responseMode": "responseNode"
            }
        },
        {
            "id": "y2", "name": "Get Video from Drive",
            "type": "n8n-nodes-base.googleDrive", "typeVersion": 3,
            "position": [460, 300],
            "parameters": {
                "operation": "download",
                "fileId": {"__rl": True, "value": "={{ $json.body.scriptId }}", "mode": "id"},
                "options": {}
            },
            "credentials": {"googleDriveOAuth2Api": {"id": "google-oauth", "name": "Google OAuth2"}}
        },
        {
            "id": "y3", "name": "Upload to YouTube",
            "type": "n8n-nodes-base.youTube", "typeVersion": 1,
            "position": [680, 300],
            "parameters": {
                "operation": "upload",
                "title": "={{ $node['Webhook - Upload Trigger'].json.body.title || 'New Short' }}",
                "description": "={{ '🤖 Generado automáticamente con IA\\n\\n#Shorts #YouTube #AI' }}",
                "categoryId": "22",
                "privacyStatus": "private",
                "options": {
                    "notifySubscribers": False,
                    "embeddable": True,
                    "publicStatsViewable": False
                }
            },
            "credentials": {"youTubeOAuth2Api": {"id": "youtube-oauth", "name": "YouTube OAuth2"}}
        },
        {
            "id": "y4", "name": "Notify Upload Success",
            "type": "n8n-nodes-base.telegram", "typeVersion": 1.2,
            "position": [900, 300],
            "parameters": {
                "operation": "sendMessage",
                "chatId": "={{ $env.TELEGRAM_CHAT_ID }}",
                "text": (
                    '={{ "🎉 *Video subido a YouTube!*\\n\\n"'
                    '+ "📺 ID: " + $json.id + "\\n"'
                    '+ "🔗 https://youtube.com/watch?v=" + $json.id + "\\n\\n"'
                    '+ "Estado: Privado (revisa antes de publicar)" }}'
                ),
                "additionalFields": {"parse_mode": "Markdown"}
            },
            "credentials": {"telegramApi": {"id": "telegram-bot", "name": "Telegram Bot"}}
        },
        {
            "id": "y5", "name": "Respond OK",
            "type": "n8n-nodes-base.respondToWebhook", "typeVersion": 1.1,
            "position": [1120, 300],
            "parameters": {
                "respondWith": "json",
                "responseBody": '={{ JSON.stringify({status:"uploaded",youtubeId:$node["Upload to YouTube"].json.id}) }}'
            }
        }
    ],
    "connections": {
        "Webhook - Upload Trigger": {"main": [[{"node": "Get Video from Drive", "type": "main", "index": 0}]]},
        "Get Video from Drive": {"main": [[{"node": "Upload to YouTube", "type": "main", "index": 0}]]},
        "Upload to YouTube": {"main": [[{"node": "Notify Upload Success", "type": "main", "index": 0}]]},
        "Notify Upload Success": {"main": [[{"node": "Respond OK", "type": "main", "index": 0}]]}
    },
    "settings": {"executionOrder": "v1", "saveManualExecutions": True}
}

# ============================================================
# DEPLOY
# ============================================================
print("=" * 60)
print("Deploying workflows to n8n...")
print("=" * 60)

# Update workflow 1 (already exists)
print("\n[1/3] Updating video_main_pipeline...")
result = api_call("PATCH", f"/workflows/{MAIN_PIPELINE_ID}", main_pipeline)
if result:
    print(f"  OK - ID: {result.get('id')}, Nodes: {len(result.get('nodes', []))}")
else:
    print("  FAILED - trying to create new...")
    result = api_call("POST", "/workflows", main_pipeline)
    if result:
        print(f"  Created - ID: {result.get('id')}")

# Create workflow 2
print("\n[2/3] Creating telegram_approval_handler...")
result = api_call("POST", "/workflows", telegram_workflow)
if result:
    print(f"  OK - ID: {result.get('id')}, Nodes: {len(result.get('nodes', []))}")
else:
    print("  FAILED")

# Create workflow 3
print("\n[3/3] Creating youtube_auto_upload...")
result = api_call("POST", "/workflows", youtube_workflow)
if result:
    print(f"  OK - ID: {result.get('id')}, Nodes: {len(result.get('nodes', []))}")
else:
    print("  FAILED")

print("\n" + "=" * 60)
print("Done! Check your n8n dashboard.")
print("=" * 60)
