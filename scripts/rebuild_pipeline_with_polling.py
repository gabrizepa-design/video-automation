"""Rebuild pipeline with proper polling loop pattern (like Nano Banana Pro)."""
import json, requests, sys, uuid
sys.stdout.reconfigure(encoding='utf-8')

import os
N8N_KEY = os.environ["N8N_API_KEY"]
BASE = os.environ.get("N8N_API_URL", "https://noctisiops-n8n.gpsefe.easypanel.host/api/v1")
headers = {"X-N8N-API-KEY": N8N_KEY, "Content-Type": "application/json"}

OPENAI_KEY = os.environ["OPENAI_API_KEY"]
RUNWAY_KEY = os.environ["RUNWAY_API_KEY"]

requests.post(f"{BASE}/workflows/BtYOMZzqfp3MxSX7/deactivate", headers=headers)
r = requests.get(f"{BASE}/workflows/BtYOMZzqfp3MxSX7", headers=headers)
wf = r.json()

# Keep nodes up to Merge Audio
keep = {
    "Webhook - New Script", "Parse Script Data",
    "Prepare Refinement Body", "Claude - Refine Script", "Parse Refined Script",
    "Claude - Analyze Scenes", "Extract Claude Analysis",
    "Prepare TTS Body", "OpenAI TTS - Generate Voice",
    "Whisper - Transcribe Audio", "Merge Audio and Subtitles"
}
wf["nodes"] = [n for n in wf["nodes"] if n["name"] in keep]
valid = {n["name"] for n in wf["nodes"]}
wf["connections"] = {k: v for k, v in wf["connections"].items() if k in valid}
print(f"Kept {len(wf['nodes'])} base nodes")

# ============================================================
# NEW NODES: Scene-by-scene generation with polling
# Pattern: SplitInBatches → DALL-E → Runway Submit → Wait → Check → Switch (loop)
# ============================================================

Y = 304  # base Y position

new_nodes = [
    # 1. Prepare Scenes Array - split scenes into individual items
    {
        "id": "s1", "name": "Prepare Scenes", "type": "n8n-nodes-base.code", "typeVersion": 2,
        "position": [1900, Y],
        "parameters": {"jsCode":
            "const data = $input.first().json;\n"
            "const scenes = data.scenes || [];\n"
            "return scenes.map((scene, i) => ({json: {\n"
            "  sceneIndex: i,\n"
            "  visual: scene.visual || 'cinematic scene',\n"
            "  narration: scene.narration || '',\n"
            "  start: scene.start,\n"
            "  end: scene.end,\n"
            "  duration: scene.duration,\n"
            "  _title: data.title,\n"
            "  _scriptId: data.scriptId,\n"
            "  _filename: data.filename,\n"
            "  _subtitles: data.subtitles || [],\n"
            "  _totalScenes: scenes.length\n"
            "}}));"
        }
    },
    # 2. SplitInBatches - process one scene at a time
    {
        "id": "s2", "name": "Process Each Scene", "type": "n8n-nodes-base.splitInBatches", "typeVersion": 3,
        "position": [2100, Y],
        "parameters": {"batchSize": 1, "options": {}}
    },
    # 3. DALL-E Generate Image
    {
        "id": "s3", "name": "DALL-E Image", "type": "n8n-nodes-base.httpRequest", "typeVersion": 4.2,
        "position": [2300, Y],
        "parameters": {
            "method": "POST",
            "url": "https://api.openai.com/v1/images/generations",
            "sendHeaders": True,
            "headerParameters": {"parameters": [
                {"name": "Authorization", "value": f"Bearer {OPENAI_KEY}"},
                {"name": "Content-Type", "value": "application/json"}
            ]},
            "sendBody": True,
            "specifyBody": "json",
            "jsonBody": "={{ JSON.stringify({model:'dall-e-3',prompt:'Vertical 9:16. '+$json.visual+'. Photorealistic, cinematic, no text.',size:'1024x1792',quality:'standard',n:1}) }}",
            "options": {"timeout": 60000}
        }
    },
    # 4. Extract Image URL + Submit Runway
    {
        "id": "s4", "name": "Submit to Runway", "type": "n8n-nodes-base.httpRequest", "typeVersion": 4.2,
        "position": [2500, Y],
        "parameters": {
            "method": "POST",
            "url": "https://api.dev.runwayml.com/v1/image_to_video",
            "sendHeaders": True,
            "headerParameters": {"parameters": [
                {"name": "Authorization", "value": f"Bearer {RUNWAY_KEY}"},
                {"name": "X-Runway-Version", "value": "2024-11-06"},
                {"name": "Content-Type", "value": "application/json"}
            ]},
            "sendBody": True,
            "specifyBody": "json",
            "jsonBody": "={{ JSON.stringify({promptImage:$json.data[0].url,promptText:$node['Process Each Scene'].json.visual.substring(0,200),model:'gen3a_turbo',duration:5,ratio:'768:1280'}) }}",
            "options": {"timeout": 30000}
        }
    },
    # 5. Wait 15s
    {
        "id": "s5", "name": "Wait Runway", "type": "n8n-nodes-base.wait", "typeVersion": 1.1,
        "position": [2700, Y],
        "parameters": {"amount": 15, "unit": "seconds"}
    },
    # 6. Check Runway Status
    {
        "id": "s6", "name": "Check Runway", "type": "n8n-nodes-base.httpRequest", "typeVersion": 4.2,
        "position": [2900, Y],
        "parameters": {
            "method": "GET",
            "url": "={{ 'https://api.dev.runwayml.com/v1/tasks/' + $json.id }}",
            "sendHeaders": True,
            "headerParameters": {"parameters": [
                {"name": "Authorization", "value": f"Bearer {RUNWAY_KEY}"},
                {"name": "X-Runway-Version", "value": "2024-11-06"}
            ]},
            "options": {"timeout": 15000}
        }
    },
    # 7. Switch - exactly like Nano Banana Pro
    {
        "id": "s7", "name": "Runway Status", "type": "n8n-nodes-base.switch", "typeVersion": 3,
        "position": [3100, Y],
        "parameters": {
            "mode": "rules",
            "rules": {"values": [
                {
                    "conditions": {"options": {"caseSensitive": True}, "conditions": [
                        {"id": "r1", "leftValue": "={{ $json.status }}", "rightValue": "SUCCEEDED",
                         "operator": {"type": "string", "operation": "equals"}}
                    ]},
                    "renameOutput": True, "outputKey": "success"
                },
                {
                    "conditions": {"options": {"caseSensitive": True}, "conditions": [
                        {"id": "r2", "leftValue": "={{ $json.status }}", "rightValue": "RUNNING",
                         "operator": {"type": "string", "operation": "equals"}}
                    ]},
                    "renameOutput": True, "outputKey": "generating"
                },
                {
                    "conditions": {"options": {"caseSensitive": True}, "conditions": [
                        {"id": "r3", "leftValue": "={{ $json.status }}", "rightValue": "FAILED",
                         "operator": {"type": "string", "operation": "equals"}}
                    ]},
                    "renameOutput": True, "outputKey": "fail"
                }
            ]},
            "options": {}
        }
    },
    # 8. Save Scene Result
    {
        "id": "s8", "name": "Save Scene Result", "type": "n8n-nodes-base.code", "typeVersion": 2,
        "position": [3300, Y],
        "parameters": {"jsCode":
            "const runway = $input.first().json;\n"
            "const batch = $node['Process Each Scene'].json;\n"
            "return [{json: {\n"
            "  ...batch,\n"
            "  videoUrl: (runway.output || [])[0] || '',\n"
            "  runwayStatus: runway.status\n"
            "}}];"
        }
    },
    # 9. Collect All Results
    {
        "id": "s9", "name": "Collect Results", "type": "n8n-nodes-base.code", "typeVersion": 2,
        "position": [2100, Y + 200],
        "parameters": {"jsCode":
            "const items = $input.all();\n"
            "const scenes = items.map(item => item.json);\n"
            "const first = scenes[0] || {};\n"
            "const remotionScenes = scenes.filter(s => s.videoUrl).map((s, i) => ({\n"
            "  id: i + 1,\n"
            "  videoPath: s.videoUrl,\n"
            "  start: s.start,\n"
            "  end: s.end,\n"
            "  duration: s.duration || (s.end - s.start),\n"
            "  narration: s.narration || '',\n"
            "  visual: s.visual || '',\n"
            "  transition: 'fade'\n"
            "}));\n"
            "return [{json: {\n"
            "  title: first._title || '',\n"
            "  scriptId: first._scriptId || '',\n"
            "  filename: first._filename || '',\n"
            "  subtitles: first._subtitles || [],\n"
            "  successCount: remotionScenes.length,\n"
            "  totalScenes: first._totalScenes || 0,\n"
            "  _remotionConfig: JSON.stringify({\n"
            "    title: first._title || '',\n"
            "    scenes: remotionScenes,\n"
            "    subtitles: first._subtitles || [],\n"
            "    fps: 30, width: 1080, height: 1920\n"
            "  })\n"
            "}}];"
        }
    },
    # 10. Render Final Video (Remotion)
    {
        "id": "s10", "name": "Render Final Video", "type": "n8n-nodes-base.httpRequest", "typeVersion": 4.2,
        "position": [2400, Y + 200],
        "parameters": {
            "method": "POST",
            "url": "http://remotion-renderer:3001/render",
            "sendHeaders": True,
            "headerParameters": {"parameters": [{"name": "Content-Type", "value": "application/json"}]},
            "sendBody": True,
            "specifyBody": "json",
            "jsonBody": "={{ $json._remotionConfig }}",
            "options": {"timeout": 600000, "response": {"response": {"responseFormat": "file"}}}
        }
    },
    # 11. Upload to Drive
    {
        "id": "s11", "name": "Upload to Drive", "type": "n8n-nodes-base.googleDrive", "typeVersion": 3,
        "position": [2700, Y + 200],
        "parameters": {
            "operation": "upload",
            "name": "={{ $node['Collect Results'].json.scriptId + '.mp4' }}",
            "folderId": {"__rl": True, "value": "1nHwfrVyh4ICuPwI82XShTr5II-YdsgrI", "mode": "id"},
            "options": {}
        },
        "credentials": {"googleDriveOAuth2Api": {"id": "BWI2yq65krCDpYV6", "name": "Google Drive - Video Automation"}}
    },
    # 12. Prepare Telegram
    {
        "id": "s12", "name": "Prepare Telegram", "type": "n8n-nodes-base.code", "typeVersion": 2,
        "position": [2900, Y + 200],
        "parameters": {"jsCode":
            "const drive = $input.first().json;\n"
            "const info = $node['Collect Results'].json;\n"
            "const driveId = drive.id || '';\n"
            "const link = driveId ? 'https://drive.google.com/file/d/' + driveId + '/view' : 'No disponible';\n"
            "const lines = [\n"
            "  'VIDEO FINAL GENERADO!',\n"
            "  '',\n"
            "  'Titulo: ' + (info.title || ''),\n"
            "  'Escenas: ' + info.successCount + '/' + info.totalScenes,\n"
            "  '',\n"
            "  'Ver video: ' + link,\n"
            "  '',\n"
            "  'Aprobar: /aprobar_' + driveId,\n"
            "  'Rechazar: /rechazar_' + driveId\n"
            "];\n"
            "return [{json: {_msg: lines.join(String.fromCharCode(10))}}];"
        }
    },
    # 13. Telegram
    {
        "id": "s13", "name": "Telegram - Notify", "type": "n8n-nodes-base.telegram", "typeVersion": 1.2,
        "position": [3100, Y + 200],
        "parameters": {
            "operation": "sendMessage",
            "chatId": "5484208881",
            "text": "={{ $json._msg }}",
            "additionalFields": {}
        },
        "credentials": {"telegramApi": {"id": "eBtFrmcPo4xBiP8Y", "name": "Telegram - Video Automation"}}
    }
]

wf["nodes"].extend(new_nodes)

# ============================================================
# CONNECTIONS - including the polling loop
# ============================================================
wf["connections"]["Merge Audio and Subtitles"] = {"main": [[{"node": "Prepare Scenes", "type": "main", "index": 0}]]}
wf["connections"]["Prepare Scenes"] = {"main": [[{"node": "Process Each Scene", "type": "main", "index": 0}]]}

# SplitInBatches has 2 outputs: [0] = batch item, [1] = done (all processed)
wf["connections"]["Process Each Scene"] = {"main": [
    [{"node": "DALL-E Image", "type": "main", "index": 0}],     # [0] process this batch
    [{"node": "Collect Results", "type": "main", "index": 0}]    # [1] all done
]}

wf["connections"]["DALL-E Image"] = {"main": [[{"node": "Submit to Runway", "type": "main", "index": 0}]]}
wf["connections"]["Submit to Runway"] = {"main": [[{"node": "Wait Runway", "type": "main", "index": 0}]]}
wf["connections"]["Wait Runway"] = {"main": [[{"node": "Check Runway", "type": "main", "index": 0}]]}
wf["connections"]["Check Runway"] = {"main": [[{"node": "Runway Status", "type": "main", "index": 0}]]}

# Switch outputs - EXACTLY like Nano Banana Pro:
# [0] success → Save Result → back to SplitInBatches
# [1] generating → Wait (LOOP BACK!)
# [2] fail → (nothing for now)
wf["connections"]["Runway Status"] = {"main": [
    [{"node": "Save Scene Result", "type": "main", "index": 0}],  # [0] success
    [{"node": "Wait Runway", "type": "main", "index": 0}],        # [1] generating → LOOP BACK
    []                                                              # [2] fail
]}

# Save Result → back to SplitInBatches (next scene)
wf["connections"]["Save Scene Result"] = {"main": [[{"node": "Process Each Scene", "type": "main", "index": 0}]]}

# After all scenes: Collect → Render → Drive → Telegram
wf["connections"]["Collect Results"] = {"main": [[{"node": "Render Final Video", "type": "main", "index": 0}]]}
wf["connections"]["Render Final Video"] = {"main": [[{"node": "Upload to Drive", "type": "main", "index": 0}]]}
wf["connections"]["Upload to Drive"] = {"main": [[{"node": "Prepare Telegram", "type": "main", "index": 0}]]}
wf["connections"]["Prepare Telegram"] = {"main": [[{"node": "Telegram - Notify", "type": "main", "index": 0}]]}

# Save
clean_settings = {"executionOrder": "v1", "saveManualExecutions": True, "callerPolicy": "workflowsFromSameOwner"}
update = {"name": wf["name"], "nodes": wf["nodes"], "connections": wf["connections"], "settings": clean_settings}
r = requests.put(f"{BASE}/workflows/BtYOMZzqfp3MxSX7", json=update, headers=headers)
print(f"PUT: {r.status_code}")
if r.status_code != 200:
    print(r.text[:500])

r = requests.post(f"{BASE}/workflows/BtYOMZzqfp3MxSX7/activate", headers=headers)
print(f"Active: {r.json().get('active')}")
print(f"Nodes: {len(wf['nodes'])}")
