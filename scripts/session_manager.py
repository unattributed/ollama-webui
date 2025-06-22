# ~/workspace/ollama-webui/scripts/session_manager.py
import os
import json
import uuid
import time

SESSIONS_DIR = "sessions"
SESSION_LIST_FILE = os.path.join(SESSIONS_DIR, "session_list.json")
os.makedirs(SESSIONS_DIR, exist_ok=True)

def load_sessions():
    if not os.path.exists(SESSION_LIST_FILE):
        return []

    try:
        with open(SESSION_LIST_FILE, "r") as f:
            return json.load(f)
    except Exception:
        return []

def save_sessions(sessions):
    with open(SESSION_LIST_FILE, "w") as f:
        json.dump(sessions, f, indent=2)

def create_session(title=None):
    sid = str(uuid.uuid4())
    timestamp = int(time.time())
    title = title or f"Session {timestamp}"

    sessions = load_sessions()
    sessions.append({
        "id": sid,
        "title": title,
        "timestamp": timestamp
    })
    save_sessions(sessions)

    return sid

def session_exists(session_id):
    return any(s["id"] == session_id for s in load_sessions())

def delete_session(session_id):
    sessions = [s for s in load_sessions() if s["id"] != session_id]
    save_sessions(sessions)
    return len(sessions)

if __name__ == "__main__":
    # Test run
    sid = create_session("test run")
    print("Created session:", sid)
    print("Sessions:", load_sessions())
