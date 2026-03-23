"""Fix Generate All Scene Videos to use $http instead of fetch."""
import json, requests, sys
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

# New code using $http helper (available in n8n Code nodes)
generate_code = (
    "const data = $input.first().json;\n"
    "const scenes = data.scenes || [];\n"
    "const OAI = '" + OPENAI_KEY + "';\n"
    "const RW = '" + RUNWAY_KEY + "';\n"
    "const results = [];\n"
    "\n"
    "for (let i = 0; i < scenes.length; i++) {\n"
    "  const scene = scenes[i];\n"
    "  const visual = scene.visual || 'cinematic dark scene';\n"
    "  const dallePrompt = 'Vertical 9:16. ' + visual + '. Photorealistic, cinematic, no text.';\n"
    "\n"
    "  let imageUrl = '';\n"
    "  try {\n"
    "    const dalleResp = await this.helpers.httpRequest({\n"
    "      method: 'POST',\n"
    "      url: 'https://api.openai.com/v1/images/generations',\n"
    "      headers: {'Authorization': 'Bearer ' + OAI, 'Content-Type': 'application/json'},\n"
    "      body: JSON.stringify({model: 'dall-e-3', prompt: dallePrompt, size: '1024x1792', quality: 'standard', n: 1}),\n"
    "      timeout: 60000\n"
    "    });\n"
    "    imageUrl = dalleResp.data?.[0]?.url || '';\n"
    "  } catch(e) { results.push({i, error: 'DALLE:'+e.message, videoUrl:''}); continue; }\n"
    "  if (!imageUrl) { results.push({i, error:'No image', videoUrl:''}); continue; }\n"
    "\n"
    "  let taskId = '';\n"
    "  try {\n"
    "    const rwResp = await this.helpers.httpRequest({\n"
    "      method: 'POST',\n"
    "      url: 'https://api.dev.runwayml.com/v1/image_to_video',\n"
    "      headers: {'Authorization': 'Bearer ' + RW, 'X-Runway-Version': '2024-11-06', 'Content-Type': 'application/json'},\n"
    "      body: JSON.stringify({promptImage: imageUrl, promptText: visual.substring(0,200), model:'gen3a_turbo', duration:5, ratio:'768:1280'}),\n"
    "      timeout: 30000\n"
    "    });\n"
    "    taskId = rwResp.id || '';\n"
    "    if (!taskId) { results.push({i, error:'No taskId: '+JSON.stringify(rwResp).substring(0,100), videoUrl:'', imageUrl}); continue; }\n"
    "  } catch(e) { results.push({i, error:'RW:'+e.message, videoUrl:'', imageUrl}); continue; }\n"
    "\n"
    "  let videoUrl = '';\n"
    "  let status = 'PENDING';\n"
    "  for (let p = 0; p < 36; p++) {\n"
    "    await new Promise(r => setTimeout(r, 10000));\n"
    "    try {\n"
    "      const cr = await this.helpers.httpRequest({\n"
    "        method: 'GET',\n"
    "        url: 'https://api.dev.runwayml.com/v1/tasks/' + taskId,\n"
    "        headers: {'Authorization': 'Bearer ' + RW, 'X-Runway-Version': '2024-11-06'},\n"
    "        timeout: 15000\n"
    "      });\n"
    "      status = cr.status || 'UNKNOWN';\n"
    "      if (status === 'SUCCEEDED') { videoUrl = (cr.output||[])[0]||''; break; }\n"
    "      if (status === 'FAILED') break;\n"
    "    } catch(e) {}\n"
    "  }\n"
    "  results.push({i, videoUrl, imageUrl, status, taskId});\n"
    "}\n"
    "\n"
    "return [{json: {...data, sceneResults: results, successCount: results.filter(r=>r.videoUrl).length, totalScenes: scenes.length}}];"
)

for node in wf["nodes"]:
    if node["name"] == "Generate All Scene Videos":
        node["parameters"]["jsCode"] = generate_code
        print("Fixed: Generate All Scene Videos (using this.helpers.httpRequest)")

clean_settings = {"executionOrder": "v1", "saveManualExecutions": True, "callerPolicy": "workflowsFromSameOwner"}
update = {"name": wf["name"], "nodes": wf["nodes"], "connections": wf["connections"], "settings": clean_settings}
r = requests.put(f"{BASE}/workflows/BtYOMZzqfp3MxSX7", json=update, headers=headers)
print(f"PUT: {r.status_code}")
if r.status_code != 200:
    print(r.text[:300])
r = requests.post(f"{BASE}/workflows/BtYOMZzqfp3MxSX7/activate", headers=headers)
print(f"Active: {r.json().get('active')}")
