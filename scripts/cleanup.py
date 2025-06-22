# ~/workspace/ollama-webui/scripts/cleanup.py
import os
import time
import shutil
import json

UPLOAD_DIR = "upload"
EMBEDDINGS_DIR = "embeddings"
SESSIONS_FILE = "sessions/session_list.json"
DEFAULT_EXPIRY_SECONDS = 86400  # 24 hours

def load_sessions():
    if not os.path.exists(SESSIONS_FILE):
        return []
    with open(SESSIONS_FILE, "r") as f:
        return json.load(f)

def save_sessions(data):
    with open(SESSIONS_FILE, "w") as f:
        json.dump(data, f, indent=2)

def delete_path(path):
    if os.path.isdir(path):
        shutil.rmtree(path)
    elif os.path.exists(path):
        os.remove(path)

def clean_expired_sessions(expiry_seconds=DEFAULT_EXPIRY_SECONDS):
    now = int(time.time())
    sessions = load_sessions()
    kept = []

    for s in sessions:
        age = now - s["timestamp"]
        if age > expiry_seconds:
            sid = s["id"]
            print(f"[🧹] Removing session: {sid} (age {age}s)")
            delete_path(os.path.join(UPLOAD_DIR, sid))
            delete_path(os.path.join(EMBEDDINGS_DIR, f"{sid}.json"))
        else:
            kept.append(s)

    save_sessions(kept)
    print(f"✅ Cleanup complete. Active sessions: {len(kept)}")

if __name__ == "__main__":
    clean_expired_sessions()
