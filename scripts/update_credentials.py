import json
import urllib.request
import urllib.error
import os

API_KEY = os.environ["N8N_API_KEY"]
BASE_URL = os.environ.get("N8N_API_URL", "https://noctisiops-n8n.gpsefe.easypanel.host/api/v1")

# ✅ IDs reales encontrados en n8n
TELEGRAM_CRED = {"id": "3uQQYkFBx9E4ykyT", "name": "Telegram account"}

# ⚠️ Reemplaza estos con los IDs reales de tu n8n UI
# Settings → Credentials → busca Google Drive y YouTube
GOOGLE_DRIVE_CRED = {"id": "REPLACE_WITH_GDRIVE_ID", "name": "Google Drive"}
YOUTUBE_CRED = {"id": "REPLACE_WITH_YOUTUBE_ID", "name": "YouTube"}

WORKFLOWS = {
    "video_main_pipeline":        "BtYOMZzqfp3MxSX7",
    "telegram_approval_handler":  "KnKfqHCDDBovKtkJ",
    "youtube_auto_upload":        "C5Ekv0LPSBbyJ1Wd",
}

def api_call(method, path, data=None):
    url = BASE_URL + path
    payload = json.dumps(data).encode("utf-8") if data else None
    req = urllib.request.Request(
        url, data=payload, method=method,
        headers={"X-N8N-API-KEY": API_KEY, "Content-Type": "application/json"}
    )
    try:
        with urllib.request.urlopen(req) as r:
            return json.loads(r.read())
    except urllib.error.HTTPError as e:
        print(f"  HTTP {e.code}: {e.read().decode()[:300]}")
        return None

def fix_credentials(nodes):
    """Reemplaza los IDs placeholder por los reales"""
    for node in nodes:
        creds = node.get("credentials", {})
        if "telegramApi" in creds:
            creds["telegramApi"] = TELEGRAM_CRED
        if "telegramTrigger" in creds:
            creds["telegramTrigger"] = TELEGRAM_CRED
        if "googleDriveOAuth2Api" in creds:
            creds["googleDriveOAuth2Api"] = GOOGLE_DRIVE_CRED
        if "youTubeOAuth2Api" in creds:
            creds["youTubeOAuth2Api"] = YOUTUBE_CRED
    return nodes

print("Fetching and updating workflows...")

for name, wf_id in WORKFLOWS.items():
    print(f"\n[{name}]")
    wf = api_call("GET", f"/workflows/{wf_id}")
    if not wf:
        print("  Could not fetch workflow")
        continue

    original_nodes = len(wf.get("nodes", []))
    wf["nodes"] = fix_credentials(wf.get("nodes", []))

    # PUT to update
    result = api_call("PUT", f"/workflows/{wf_id}", {
        "name": wf["name"],
        "nodes": wf["nodes"],
        "connections": wf["connections"],
        "settings": wf.get("settings", {}),
        "staticData": wf.get("staticData")
    })

    if result:
        print(f"  OK Updated - {original_nodes} nodes fixed")
        for node in result.get("nodes", []):
            for ctype, cval in node.get("credentials", {}).items():
                if "REPLACE" in str(cval.get("id", "")):
                    print(f"  PENDING: {node['name']} -> {ctype} needs real ID")
    else:
        print("  FAILED")

print("\nDone!")
