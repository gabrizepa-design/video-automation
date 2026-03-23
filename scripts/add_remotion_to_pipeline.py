"""Add Remotion render step to the n8n pipeline."""
import json, requests, sys, os
sys.stdout.reconfigure(encoding='utf-8')

N8N_KEY = os.environ["N8N_API_KEY"]
BASE = os.environ.get("N8N_API_URL", "https://noctisiops-n8n.gpsefe.easypanel.host/api/v1")
headers = {"X-N8N-API-KEY": N8N_KEY, "Content-Type": "application/json"}

requests.post(f"{BASE}/workflows/BtYOMZzqfp3MxSX7/deactivate", headers=headers)
r = requests.get(f"{BASE}/workflows/BtYOMZzqfp3MxSX7", headers=headers)
wf = r.json()

# --- Node: Build Remotion Config ---
build_config_code = (
    "const data = $input.first().json;\n"
    "const scenes = data.scenes || [];\n"
    "const results = data.sceneResults || [];\n"
    "const subtitles = data.subtitles || [];\n"
    "\n"
    "const remotionScenes = [];\n"
    "for (let i = 0; i < scenes.length; i++) {\n"
    "  const scene = scenes[i];\n"
    "  const result = results.find(r => r.i === i) || {};\n"
    "  if (!result.videoUrl) continue;\n"
    "  remotionScenes.push({\n"
    "    id: i + 1,\n"
    "    videoPath: result.videoUrl,\n"
    "    start: scene.start,\n"
    "    end: scene.end,\n"
    "    duration: scene.duration || (scene.end - scene.start),\n"
    "    narration: scene.narration || '',\n"
    "    visual: scene.visual || '',\n"
    "    transition: i < scenes.length - 1 ? 'fade' : 'cut'\n"
    "  });\n"
    "}\n"
    "\n"
    "const config = {\n"
    "  title: data.title || 'Video',\n"
    "  scenes: remotionScenes,\n"
    "  subtitles: subtitles,\n"
    "  outputPath: '/tmp/videos/final/video_' + Date.now() + '.mp4',\n"
    "  fps: 30,\n"
    "  width: 1080,\n"
    "  height: 1920\n"
    "};\n"
    "\n"
    "return [{json: {\n"
    "  _remotionConfig: JSON.stringify(config),\n"
    "  _successCount: data.successCount,\n"
    "  _totalScenes: data.totalScenes,\n"
    "  scriptId: data.scriptId || 'script_' + Date.now(),\n"
    "  title: data.title || '',\n"
    "  filename: data.filename || ''\n"
    "}}];"
)

build_config_node = {
    "id": "rem1",
    "name": "Build Remotion Config",
    "type": "n8n-nodes-base.code",
    "typeVersion": 2,
    "position": [2200, 304],
    "parameters": {"jsCode": build_config_code}
}

# --- Node: Render Video (HTTP Request to Remotion) ---
render_node = {
    "id": "rem2",
    "name": "Render Final Video",
    "type": "n8n-nodes-base.httpRequest",
    "typeVersion": 4.2,
    "position": [2400, 304],
    "parameters": {
        "method": "POST",
        "url": "http://remotion-renderer:3001/render",
        "sendHeaders": True,
        "headerParameters": {
            "parameters": [
                {"name": "Content-Type", "value": "application/json"}
            ]
        },
        "sendBody": True,
        "specifyBody": "json",
        "jsonBody": "={{ $json._remotionConfig }}",
        "options": {
            "timeout": 600000,
            "response": {"response": {"responseFormat": "file"}}
        }
    }
}

# --- Node: Upload to Drive ---
upload_drive_code = (
    "// Pass the rendered video binary + metadata to next node\n"
    "const prev = $node['Build Remotion Config'].json;\n"
    "return [{json: {\n"
    "  scriptId: prev.scriptId,\n"
    "  title: prev.title,\n"
    "  filename: prev.filename,\n"
    "  _successCount: prev._successCount,\n"
    "  _totalScenes: prev._totalScenes,\n"
    "  hasVideo: !!$binary?.data\n"
    "}, binary: $binary}];"
)

pass_binary_node = {
    "id": "rem3",
    "name": "Prepare Upload",
    "type": "n8n-nodes-base.code",
    "typeVersion": 2,
    "position": [2600, 304],
    "parameters": {"jsCode": upload_drive_code}
}

# --- Node: Upload to Google Drive ---
drive_upload_node = {
    "id": "rem4",
    "name": "Upload to Google Drive",
    "type": "n8n-nodes-base.googleDrive",
    "typeVersion": 3,
    "position": [2800, 304],
    "parameters": {
        "operation": "upload",
        "name": "={{ $json.scriptId + '.mp4' }}",
        "folderId": {"__rl": True, "value": "1nHwfrVyh4ICuPwI82XShTr5II-YdsgrI", "mode": "id"},
        "options": {}
    },
    "credentials": {"googleDriveOAuth2Api": {"id": "BWI2yq65krCDpYV6", "name": "Google Drive - Video Automation"}}
}

# Add new nodes
wf["nodes"].extend([build_config_node, render_node, pass_binary_node, drive_upload_node])

# Update Prepare Telegram Message to include Drive link
for node in wf["nodes"]:
    if node["name"] == "Prepare Telegram Message":
        node["parameters"]["jsCode"] = (
            "const data = $input.first().json;\n"
            "const driveId = data.id || '';\n"
            "const driveLink = driveId ? 'https://drive.google.com/file/d/' + driveId + '/view' : 'No disponible';\n"
            "const prev = $node['Build Remotion Config'].json;\n"
            "const lines = [\n"
            "  'Video FINAL generado!',\n"
            "  '',\n"
            "  'Titulo: ' + (prev.title || ''),\n"
            "  'Escenas: ' + (prev._successCount || '?') + '/' + (prev._totalScenes || '?'),\n"
            "  '',\n"
            "  'Ver video: ' + driveLink,\n"
            "  '',\n"
            "  'Aprobar: /aprobar_' + driveId,\n"
            "  'Rechazar: /rechazar_' + driveId\n"
            "];\n"
            "return [{json: {_telegramMsg: lines.join(String.fromCharCode(10))}}];"
        )
        node["position"] = [3000, 304]
        print("Updated: Prepare Telegram Message with Drive link")

# Update Telegram position
for node in wf["nodes"]:
    if node["name"] == "Telegram - Notify Gabriel":
        node["position"] = [3200, 304]

# Update connections:
# Generate All Scene Videos → Build Remotion Config → Render → Prepare Upload → Drive Upload → Telegram Msg → Telegram
wf["connections"]["Generate All Scene Videos"] = {
    "main": [[{"node": "Build Remotion Config", "type": "main", "index": 0}]]
}
wf["connections"]["Build Remotion Config"] = {
    "main": [[{"node": "Render Final Video", "type": "main", "index": 0}]]
}
wf["connections"]["Render Final Video"] = {
    "main": [[{"node": "Prepare Upload", "type": "main", "index": 0}]]
}
wf["connections"]["Prepare Upload"] = {
    "main": [[{"node": "Upload to Google Drive", "type": "main", "index": 0}]]
}
wf["connections"]["Upload to Google Drive"] = {
    "main": [[{"node": "Prepare Telegram Message", "type": "main", "index": 0}]]
}

clean_settings = {"executionOrder": "v1", "saveManualExecutions": True, "callerPolicy": "workflowsFromSameOwner"}
update = {"name": wf["name"], "nodes": wf["nodes"], "connections": wf["connections"], "settings": clean_settings}
r = requests.put(f"{BASE}/workflows/BtYOMZzqfp3MxSX7", json=update, headers=headers)
print(f"PUT: {r.status_code}")
if r.status_code != 200:
    print(r.text[:300])

r = requests.post(f"{BASE}/workflows/BtYOMZzqfp3MxSX7/activate", headers=headers)
print(f"Active: {r.json().get('active')}")
print(f"Nodes: {len(wf['nodes'])}")

# Verify flow
r = requests.get(f"{BASE}/workflows/BtYOMZzqfp3MxSX7", headers=headers)
wf2 = r.json()
print("\nFull pipeline:")
flow = "Webhook - New Script"
visited = set()
for _ in range(25):
    conns = wf2["connections"].get(flow, {}).get("main", [[]])
    if conns and conns[0]:
        nxt = conns[0][0]["node"]
        if nxt in visited: break
        visited.add(nxt)
        print(f"  -> {nxt}")
        flow = nxt
    else:
        break
