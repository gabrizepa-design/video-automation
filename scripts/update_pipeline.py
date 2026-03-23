"""Update the n8n video_main_pipeline for multi-scene generation."""
import json, requests, sys, time

sys.stdout.reconfigure(encoding='utf-8')

import os
N8N_KEY = os.environ["N8N_API_KEY"]
BASE = os.environ.get("N8N_API_URL", "https://noctisiops-n8n.gpsefe.easypanel.host/api/v1")
headers = {"X-N8N-API-KEY": N8N_KEY, "Content-Type": "application/json"}

OPENAI_KEY = os.environ["OPENAI_API_KEY"]
RUNWAY_KEY = os.environ["RUNWAY_API_KEY"]

# Deactivate and get workflow
requests.post(f"{BASE}/workflows/BtYOMZzqfp3MxSX7/deactivate", headers=headers)
r = requests.get(f"{BASE}/workflows/BtYOMZzqfp3MxSX7", headers=headers)
wf = r.json()

# Keep only the nodes up to Merge Audio
keep_nodes = {
    "Webhook - New Script", "Parse Script Data",
    "Prepare Refinement Body", "Claude - Refine Script", "Parse Refined Script",
    "Claude - Analyze Scenes", "Extract Claude Analysis",
    "Prepare TTS Body", "OpenAI TTS - Generate Voice",
    "Whisper - Transcribe Audio", "Merge Audio and Subtitles"
}
wf["nodes"] = [n for n in wf["nodes"] if n["name"] in keep_nodes]
valid_names = {n["name"] for n in wf["nodes"]}
wf["connections"] = {k: v for k, v in wf["connections"].items() if k in valid_names}
print(f"Kept {len(wf['nodes'])} nodes")

# --- Generate All Scene Videos (Code node) ---
generate_code = (
    "const data = $input.first().json;\n"
    "const scenes = data.scenes || [];\n"
    "const OPENAI_KEY = '" + OPENAI_KEY + "';\n"
    "const RUNWAY_KEY = '" + RUNWAY_KEY + "';\n"
    "const results = [];\n"
    "\n"
    "for (let i = 0; i < scenes.length; i++) {\n"
    "  const scene = scenes[i];\n"
    "  const visual = scene.visual || 'cinematic dark scene';\n"
    "  const dallePrompt = 'Vertical 9:16. ' + visual + '. Photorealistic, cinematic, no text.';\n"
    "\n"
    "  let imageUrl = '';\n"
    "  try {\n"
    "    const dr = await fetch('https://api.openai.com/v1/images/generations', {\n"
    "      method: 'POST',\n"
    "      headers: {'Authorization': 'Bearer ' + OPENAI_KEY, 'Content-Type': 'application/json'},\n"
    "      body: JSON.stringify({model: 'dall-e-3', prompt: dallePrompt, size: '1024x1792', quality: 'standard', n: 1})\n"
    "    });\n"
    "    const dd = await dr.json();\n"
    "    imageUrl = dd.data?.[0]?.url || '';\n"
    "  } catch(e) { results.push({i, error: 'DALLE:'+e.message, videoUrl:''}); continue; }\n"
    "  if (!imageUrl) { results.push({i, error:'No image', videoUrl:''}); continue; }\n"
    "\n"
    "  let taskId = '';\n"
    "  try {\n"
    "    const rr = await fetch('https://api.dev.runwayml.com/v1/image_to_video', {\n"
    "      method: 'POST',\n"
    "      headers: {'Authorization': 'Bearer ' + RUNWAY_KEY, 'X-Runway-Version': '2024-11-06', 'Content-Type': 'application/json'},\n"
    "      body: JSON.stringify({promptImage: imageUrl, promptText: visual.substring(0,200), model:'gen3a_turbo', duration:5, ratio:'768:1280'})\n"
    "    });\n"
    "    const rd = await rr.json();\n"
    "    taskId = rd.id || '';\n"
    "    if (!taskId) { results.push({i, error:'No taskId: '+JSON.stringify(rd).substring(0,100), videoUrl:'', imageUrl}); continue; }\n"
    "  } catch(e) { results.push({i, error:'RW:'+e.message, videoUrl:'', imageUrl}); continue; }\n"
    "\n"
    "  let videoUrl = '';\n"
    "  let status = 'PENDING';\n"
    "  for (let p = 0; p < 36; p++) {\n"
    "    await new Promise(r => setTimeout(r, 10000));\n"
    "    try {\n"
    "      const cr = await fetch('https://api.dev.runwayml.com/v1/tasks/' + taskId, {\n"
    "        headers: {'Authorization': 'Bearer ' + RUNWAY_KEY, 'X-Runway-Version': '2024-11-06'}\n"
    "      });\n"
    "      const cd = await cr.json();\n"
    "      status = cd.status || 'UNKNOWN';\n"
    "      if (status === 'SUCCEEDED') { videoUrl = (cd.output||[])[0]||''; break; }\n"
    "      if (status === 'FAILED') break;\n"
    "    } catch(e) {}\n"
    "  }\n"
    "  results.push({i, videoUrl, imageUrl, status, taskId});\n"
    "}\n"
    "\n"
    "return [{json: {...data, sceneResults: results, successCount: results.filter(r=>r.videoUrl).length, totalScenes: scenes.length}}];"
)

generate_node = {
    "id": "gen1", "name": "Generate All Scene Videos",
    "type": "n8n-nodes-base.code", "typeVersion": 2,
    "position": [1900, 304],
    "parameters": {"jsCode": generate_code}
}

# --- Prepare Telegram Message ---
telegram_msg_code = (
    "const data = $input.first().json;\n"
    "const results = data.sceneResults || [];\n"
    "const lines = ['Video generado!', '', 'Titulo: ' + (data.title||''), "
    "'Escenas: ' + data.successCount + '/' + data.totalScenes];\n"
    "results.forEach((r,i) => {\n"
    "  if (r.videoUrl) lines.push('Scene ' + (i+1) + ': ' + r.videoUrl);\n"
    "  else lines.push('Scene ' + (i+1) + ': FAILED - ' + (r.error||''));\n"
    "});\n"
    "lines.push('', 'Aprobar: /aprobar_' + (data.scriptId||''), 'Rechazar: /rechazar_' + (data.scriptId||''));\n"
    "return [{json: {...data, _telegramMsg: lines.join(String.fromCharCode(10))}}];"
)

telegram_msg_node = {
    "id": "gen3", "name": "Prepare Telegram Message",
    "type": "n8n-nodes-base.code", "typeVersion": 2,
    "position": [2200, 304],
    "parameters": {"jsCode": telegram_msg_code}
}

# --- Telegram Node ---
telegram_node = {
    "id": "gen4", "name": "Telegram - Notify Gabriel",
    "type": "n8n-nodes-base.telegram", "typeVersion": 1.2,
    "position": [2400, 304],
    "parameters": {
        "operation": "sendMessage",
        "chatId": "5484208881",
        "text": "={{ $json._telegramMsg }}",
        "additionalFields": {}
    },
    "credentials": {"telegramApi": {"id": "eBtFrmcPo4xBiP8Y", "name": "Telegram - Video Automation"}}
}

wf["nodes"].extend([generate_node, telegram_msg_node, telegram_node])

# Connections
wf["connections"]["Merge Audio and Subtitles"] = {
    "main": [[{"node": "Generate All Scene Videos", "type": "main", "index": 0}]]
}
wf["connections"]["Generate All Scene Videos"] = {
    "main": [[{"node": "Prepare Telegram Message", "type": "main", "index": 0}]]
}
wf["connections"]["Prepare Telegram Message"] = {
    "main": [[{"node": "Telegram - Notify Gabriel", "type": "main", "index": 0}]]
}

clean_settings = {"executionOrder": "v1", "saveManualExecutions": True, "callerPolicy": "workflowsFromSameOwner"}
update = {"name": wf["name"], "nodes": wf["nodes"], "connections": wf["connections"], "settings": clean_settings}
r = requests.put(f"{BASE}/workflows/BtYOMZzqfp3MxSX7", json=update, headers=headers)
print(f"PUT: {r.status_code}")
if r.status_code != 200:
    print(r.text[:500])
r = requests.post(f"{BASE}/workflows/BtYOMZzqfp3MxSX7/activate", headers=headers)
print(f"Active: {r.json().get('active')}")
print(f"Nodes: {len(wf['nodes'])}")

# Show flow
r = requests.get(f"{BASE}/workflows/BtYOMZzqfp3MxSX7", headers=headers)
wf2 = r.json()
print("\nPipeline:")
flow = "Webhook - New Script"
visited = set()
for _ in range(20):
    conns = wf2["connections"].get(flow, {}).get("main", [[]])
    if conns and conns[0]:
        nxt = conns[0][0]["node"]
        if nxt in visited: break
        visited.add(nxt)
        print(f"  -> {nxt}")
        flow = nxt
    else:
        break
