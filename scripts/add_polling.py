import json, urllib.request, urllib.error, os

API_KEY = os.environ["N8N_API_KEY"]
BASE_URL = os.environ.get("N8N_API_URL", "https://noctisiops-n8n.gpsefe.easypanel.host/api/v1")
TELEGRAM_CRED = {"id": "3uQQYkFBx9E4ykyT", "name": "Telegram account"}

def api(method, path, data=None):
    url = BASE_URL + path
    payload = json.dumps(data).encode() if data else None
    req = urllib.request.Request(url, data=payload, method=method,
        headers={"X-N8N-API-KEY": API_KEY, "Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req) as r:
            return json.loads(r.read())
    except urllib.error.HTTPError as e:
        print(f"  ERROR {e.code}: {e.read().decode()[:300]}")
        return None

# ── Polling nodes to inject ──────────────────────────────────────────────────

RUNWAY_POLLING_NODES = [
    {
        "id": "rp1", "name": "Runway - Start Job",
        "type": "n8n-nodes-base.httpRequest", "typeVersion": 4.2,
        "position": [1560, 300],
        "parameters": {
            "method": "POST",
            "url": "https://api.dev.runwayml.com/v1/image_to_video",
            "sendHeaders": True,
            "headerParameters": {"parameters": [
                {"name": "Authorization", "value": '={{ "Bearer " + $env.RUNWAY_API_KEY }}'},
                {"name": "X-Runway-Version", "value": "2024-11-06"},
                {"name": "Content-Type", "value": "application/json"}
            ]},
            "sendBody": True, "specifyBody": "json",
            "jsonBody": '={{ JSON.stringify({promptText:($json.videoScenes||[{}])[0].runwayPrompt||"cinematic vertical video",duration:10,ratio:"720:1280",model:"gen3a_turbo"}) }}'
        }
    },
    {
        "id": "rp2", "name": "Runway - Init Poll Counter",
        "type": "n8n-nodes-base.code", "typeVersion": 2,
        "position": [1780, 300],
        "parameters": {
            "jsCode": (
                "const data = $input.first().json;\n"
                "return [{ json: {\n"
                "  ...data,\n"
                "  _runwayJobId: data.id,\n"
                "  _runwayRetries: 0,\n"
                "  _runwayMaxRetries: 36,\n"
                "  _runwayInterval: 10\n"
                "}}];"
            )
        }
    },
    {
        "id": "rp3", "name": "Runway - Wait 10s",
        "type": "n8n-nodes-base.wait", "typeVersion": 1.1,
        "position": [2000, 300],
        "parameters": {"unit": "seconds", "amount": 10}
    },
    {
        "id": "rp4", "name": "Runway - Check Status",
        "type": "n8n-nodes-base.httpRequest", "typeVersion": 4.2,
        "position": [2220, 300],
        "parameters": {
            "method": "GET",
            "url": '={{ "https://api.dev.runwayml.com/v1/tasks/" + $json._runwayJobId }}',
            "sendHeaders": True,
            "headerParameters": {"parameters": [
                {"name": "Authorization", "value": '={{ "Bearer " + $env.RUNWAY_API_KEY }}'},
                {"name": "X-Runway-Version", "value": "2024-11-06"}
            ]}
        }
    },
    {
        "id": "rp5", "name": "Runway - Eval Status",
        "type": "n8n-nodes-base.code", "typeVersion": 2,
        "position": [2440, 300],
        "parameters": {
            "jsCode": (
                "const status = $input.first().json;\n"
                "const prev = $node['Runway - Init Poll Counter']?.json || {};\n"
                "const retries = (prev._runwayRetries || 0) + 1;\n"
                "const maxRetries = prev._runwayMaxRetries || 36;\n"
                "return [{ json: {\n"
                "  ...prev,\n"
                "  _runwayStatus: status.status,\n"
                "  _runwayOutput: (status.output || [])[0] || '',\n"
                "  _runwayRetries: retries,\n"
                "  _runwayTimedOut: retries >= maxRetries,\n"
                "  _runwayDone: status.status === 'SUCCEEDED',\n"
                "  _runwayFailed: status.status === 'FAILED'\n"
                "}}];"
            )
        }
    },
    {
        "id": "rp6", "name": "Runway - Status Router",
        "type": "n8n-nodes-base.switch", "typeVersion": 3,
        "position": [2660, 300],
        "parameters": {
            "mode": "rules",
            "rules": {"values": [
                {"conditions": {"options": {"caseSensitive": True}, "conditions": [{"id": "c1", "leftValue": "={{ $json._runwayDone }}", "rightValue": True, "operator": {"type": "boolean", "operation": "equals"}}]}, "renameOutput": True, "outputKey": "done"},
                {"conditions": {"options": {"caseSensitive": True}, "conditions": [{"id": "c2", "leftValue": "={{ $json._runwayFailed }}", "rightValue": True, "operator": {"type": "boolean", "operation": "equals"}}]}, "renameOutput": True, "outputKey": "failed"},
                {"conditions": {"options": {"caseSensitive": True}, "conditions": [{"id": "c3", "leftValue": "={{ $json._runwayTimedOut }}", "rightValue": True, "operator": {"type": "boolean", "operation": "equals"}}]}, "renameOutput": True, "outputKey": "timeout"}
            ]}
        }
    },
    {
        "id": "rp7", "name": "Runway - Notify Error",
        "type": "n8n-nodes-base.telegram", "typeVersion": 1.2,
        "position": [2880, 400],
        "parameters": {
            "operation": "sendMessage",
            "chatId": "={{ $env.TELEGRAM_CHAT_ID }}",
            "text": '={{ "ERROR Runway\\nScript: " + ($json.scriptId||"?") + "\\nEstado: " + $json._runwayStatus + "\\nIntentos: " + $json._runwayRetries + "/" + $json._runwayMaxRetries }}',
            "additionalFields": {}
        },
        "credentials": {"telegramApi": TELEGRAM_CRED}
    }
]

ELEVENLABS_POLLING_NODES = [
    {
        "id": "ep1", "name": "ElevenLabs - Request TTS",
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
            "sendBody": True, "specifyBody": "json",
            "jsonBody": '={{ JSON.stringify({text:$json.narration,model_id:$env.ELEVENLABS_MODEL_ID||"eleven_multilingual_v2",voice_settings:{stability:0.5,similarity_boost:0.75,style:0.5,use_speaker_boost:true}}) }}',
            "options": {"response": {"response": {"responseFormat": "file"}}}
        }
    },
    {
        "id": "ep2", "name": "ElevenLabs - Verify Audio",
        "type": "n8n-nodes-base.code", "typeVersion": 2,
        "position": [1340, 300],
        "parameters": {
            "jsCode": (
                "const item = $input.first();\n"
                "const hasAudio = !!(item.binary && Object.keys(item.binary).length > 0);\n"
                "const retries = ($json._elRetries || 0) + 1;\n"
                "const maxRetries = 12;\n"
                "return [{ json: {\n"
                "  ...$json,\n"
                "  _elAudioReady: hasAudio,\n"
                "  _elRetries: retries,\n"
                "  _elTimedOut: retries >= maxRetries && !hasAudio,\n"
                "  _elFailed: !hasAudio && retries >= maxRetries\n"
                "}, binary: item.binary }];"
            )
        }
    },
    {
        "id": "ep3", "name": "ElevenLabs - Audio Ready?",
        "type": "n8n-nodes-base.switch", "typeVersion": 3,
        "position": [1560, 300],
        "parameters": {
            "mode": "rules",
            "rules": {"values": [
                {"conditions": {"options": {"caseSensitive": True}, "conditions": [{"id": "c1", "leftValue": "={{ $json._elAudioReady }}", "rightValue": True, "operator": {"type": "boolean", "operation": "equals"}}]}, "renameOutput": True, "outputKey": "ready"},
                {"conditions": {"options": {"caseSensitive": True}, "conditions": [{"id": "c2", "leftValue": "={{ $json._elFailed }}", "rightValue": True, "operator": {"type": "boolean", "operation": "equals"}}]}, "renameOutput": True, "outputKey": "failed"}
            ]}
        }
    },
    {
        "id": "ep4", "name": "ElevenLabs - Notify Error",
        "type": "n8n-nodes-base.telegram", "typeVersion": 1.2,
        "position": [1780, 400],
        "parameters": {
            "operation": "sendMessage",
            "chatId": "={{ $env.TELEGRAM_CHAT_ID }}",
            "text": '={{ "ERROR ElevenLabs TTS\\nScript: " + ($json.scriptId||"?") + "\\nNo se genero audio despues de " + $json._elRetries + " intentos." }}',
            "additionalFields": {}
        },
        "credentials": {"telegramApi": TELEGRAM_CRED}
    }
]

YOUTUBE_POLLING_NODES = [
    {
        "id": "yp1", "name": "YouTube - Init Poll",
        "type": "n8n-nodes-base.code", "typeVersion": 2,
        "position": [900, 300],
        "parameters": {
            "jsCode": (
                "const upload = $input.first().json;\n"
                "return [{ json: {\n"
                "  ...upload,\n"
                "  _ytVideoId: upload.id,\n"
                "  _ytRetries: 0,\n"
                "  _ytMaxRetries: 40\n"
                "}}];"
            )
        }
    },
    {
        "id": "yp2", "name": "YouTube - Wait 15s",
        "type": "n8n-nodes-base.wait", "typeVersion": 1.1,
        "position": [1120, 300],
        "parameters": {"unit": "seconds", "amount": 15}
    },
    {
        "id": "yp3", "name": "YouTube - Check Processing",
        "type": "n8n-nodes-base.httpRequest", "typeVersion": 4.2,
        "position": [1340, 300],
        "parameters": {
            "method": "GET",
            "url": '={{ "https://www.googleapis.com/youtube/v3/videos?part=status,processingDetails&id=" + $json._ytVideoId }}',
            "sendHeaders": True,
            "headerParameters": {"parameters": [
                {"name": "Authorization", "value": '={{ "Bearer " + $env.GOOGLE_ACCESS_TOKEN }}'}
            ]}
        }
    },
    {
        "id": "yp4", "name": "YouTube - Eval Processing",
        "type": "n8n-nodes-base.code", "typeVersion": 2,
        "position": [1560, 300],
        "parameters": {
            "jsCode": (
                "const resp = $input.first().json;\n"
                "const video = (resp.items || [])[0] || {};\n"
                "const uploadStatus = video.status?.uploadStatus || 'unknown';\n"
                "const retries = ($json._ytRetries || 0) + 1;\n"
                "const maxRetries = $json._ytMaxRetries || 40;\n"
                "const done = uploadStatus === 'processed' || uploadStatus === 'uploaded';\n"
                "const failed = uploadStatus === 'failed' || uploadStatus === 'rejected';\n"
                "return [{ json: {\n"
                "  ...$json,\n"
                "  _ytUploadStatus: uploadStatus,\n"
                "  _ytRetries: retries,\n"
                "  _ytDone: done,\n"
                "  _ytFailed: failed,\n"
                "  _ytTimedOut: !done && !failed && retries >= maxRetries\n"
                "}}];"
            )
        }
    },
    {
        "id": "yp5", "name": "YouTube - Status Router",
        "type": "n8n-nodes-base.switch", "typeVersion": 3,
        "position": [1780, 300],
        "parameters": {
            "mode": "rules",
            "rules": {"values": [
                {"conditions": {"options": {"caseSensitive": True}, "conditions": [{"id": "c1", "leftValue": "={{ $json._ytDone }}", "rightValue": True, "operator": {"type": "boolean", "operation": "equals"}}]}, "renameOutput": True, "outputKey": "done"},
                {"conditions": {"options": {"caseSensitive": True}, "conditions": [{"id": "c2", "leftValue": "={{ $json._ytFailed }}", "rightValue": True, "operator": {"type": "boolean", "operation": "equals"}}]}, "renameOutput": True, "outputKey": "failed"},
                {"conditions": {"options": {"caseSensitive": True}, "conditions": [{"id": "c3", "leftValue": "={{ $json._ytTimedOut }}", "rightValue": True, "operator": {"type": "boolean", "operation": "equals"}}]}, "renameOutput": True, "outputKey": "timeout"}
            ]}
        }
    },
    {
        "id": "yp6", "name": "YouTube - Notify Error",
        "type": "n8n-nodes-base.telegram", "typeVersion": 1.2,
        "position": [2000, 400],
        "parameters": {
            "operation": "sendMessage",
            "chatId": "={{ $env.TELEGRAM_CHAT_ID }}",
            "text": '={{ "ERROR YouTube\\nVideo ID: " + $json._ytVideoId + "\\nEstado: " + $json._ytUploadStatus + "\\nIntentos: " + $json._ytRetries + "/" + $json._ytMaxRetries }}',
            "additionalFields": {}
        },
        "credentials": {"telegramApi": TELEGRAM_CRED}
    },
    {
        "id": "yp7", "name": "YouTube - Notify Success",
        "type": "n8n-nodes-base.telegram", "typeVersion": 1.2,
        "position": [2000, 200],
        "parameters": {
            "operation": "sendMessage",
            "chatId": "={{ $env.TELEGRAM_CHAT_ID }}",
            "text": '={{ "Video publicado en YouTube!\\nID: " + $json._ytVideoId + "\\nhttps://youtube.com/watch?v=" + $json._ytVideoId }}',
            "additionalFields": {}
        },
        "credentials": {"telegramApi": TELEGRAM_CRED}
    }
]

# ── Deploy ────────────────────────────────────────────────────────────────────

print("Adding polling nodes to workflows...\n")

# 1. video_main_pipeline — Runway + ElevenLabs polling
print("[1/2] Updating video_main_pipeline with Runway + ElevenLabs polling...")
wf = api("GET", "/workflows/BtYOMZzqfp3MxSX7")
if wf:
    existing = wf["nodes"]
    # Remove old fixed-wait Runway nodes
    existing = [n for n in existing if n["name"] not in [
        "Runway - Generate Video", "Wait for Runway", "Wait 30s for Runway",
        "Check Runway Status", "ElevenLabs - Generate Voice"
    ]]
    existing += RUNWAY_POLLING_NODES + ELEVENLABS_POLLING_NODES

    # Rebuild connections
    conns = wf["connections"]
    # Wire ElevenLabs
    conns["Extract Claude Analysis"] = {"main": [[{"node": "ElevenLabs - Request TTS", "type": "main", "index": 0}]]}
    conns["ElevenLabs - Request TTS"] = {"main": [[{"node": "ElevenLabs - Verify Audio", "type": "main", "index": 0}]]}
    conns["ElevenLabs - Verify Audio"] = {"main": [[{"node": "ElevenLabs - Audio Ready?", "type": "main", "index": 0}]]}
    conns["ElevenLabs - Audio Ready?"] = {"main": [
        [{"node": "Whisper - Transcribe Audio", "type": "main", "index": 0}],
        [{"node": "ElevenLabs - Notify Error", "type": "main", "index": 0}]
    ]}
    # Wire Runway
    conns["Merge Audio and Subtitles"] = {"main": [[{"node": "Runway - Start Job", "type": "main", "index": 0}]]}
    conns["Runway - Start Job"] = {"main": [[{"node": "Runway - Init Poll Counter", "type": "main", "index": 0}]]}
    conns["Runway - Init Poll Counter"] = {"main": [[{"node": "Runway - Wait 10s", "type": "main", "index": 0}]]}
    conns["Runway - Wait 10s"] = {"main": [[{"node": "Runway - Check Status", "type": "main", "index": 0}]]}
    conns["Runway - Check Status"] = {"main": [[{"node": "Runway - Eval Status", "type": "main", "index": 0}]]}
    conns["Runway - Eval Status"] = {"main": [[{"node": "Runway - Status Router", "type": "main", "index": 0}]]}
    conns["Runway - Status Router"] = {"main": [
        [{"node": "Prepare Render Payload", "type": "main", "index": 0}],
        [{"node": "Runway - Notify Error", "type": "main", "index": 0}],
        [{"node": "Runway - Notify Error", "type": "main", "index": 0}]
    ]}
    # Loop back: still pending → back to Wait
    conns["Runway - Status Router"]["main"].append(
        [{"node": "Runway - Wait 10s", "type": "main", "index": 0}]
    )

    result = api("PUT", "/workflows/BtYOMZzqfp3MxSX7", {
        "name": wf["name"], "nodes": existing,
        "connections": conns, "settings": wf.get("settings", {})
    })
    if result:
        print(f"  OK - {len(result.get('nodes',[]))} nodes")
    else:
        print("  FAILED")

# 2. youtube_auto_upload — YouTube polling
print("\n[2/2] Updating youtube_auto_upload with YouTube polling...")
wf2 = api("GET", "/workflows/C5Ekv0LPSBbyJ1Wd")
if wf2:
    existing2 = wf2["nodes"]
    existing2 = [n for n in existing2 if n["name"] not in ["Notify Upload Success", "Respond OK"]]
    existing2 += YOUTUBE_POLLING_NODES

    conns2 = wf2["connections"]
    conns2["Upload to YouTube"] = {"main": [[{"node": "YouTube - Init Poll", "type": "main", "index": 0}]]}
    conns2["YouTube - Init Poll"] = {"main": [[{"node": "YouTube - Wait 15s", "type": "main", "index": 0}]]}
    conns2["YouTube - Wait 15s"] = {"main": [[{"node": "YouTube - Check Processing", "type": "main", "index": 0}]]}
    conns2["YouTube - Check Processing"] = {"main": [[{"node": "YouTube - Eval Processing", "type": "main", "index": 0}]]}
    conns2["YouTube - Eval Processing"] = {"main": [[{"node": "YouTube - Status Router", "type": "main", "index": 0}]]}
    conns2["YouTube - Status Router"] = {"main": [
        [{"node": "YouTube - Notify Success", "type": "main", "index": 0}],
        [{"node": "YouTube - Notify Error", "type": "main", "index": 0}],
        [{"node": "YouTube - Notify Error", "type": "main", "index": 0}],
        [{"node": "YouTube - Wait 15s", "type": "main", "index": 0}]  # loop back
    ]}

    result2 = api("PUT", "/workflows/C5Ekv0LPSBbyJ1Wd", {
        "name": wf2["name"], "nodes": existing2,
        "connections": conns2, "settings": wf2.get("settings", {})
    })
    if result2:
        print(f"  OK - {len(result2.get('nodes',[]))} nodes")
    else:
        print("  FAILED")

print("\nDone!")
