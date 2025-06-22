# ~/workspace/ollama-webui/scripts/dev_server.py

import os
import subprocess
import uuid
from scripts.session_manager import create_session

def main():
    # Create a new session
    session_id = str(uuid.uuid4())
    create_session(f"Dev Session {session_id}")
    print(f"\n[🔧] Created session: {session_id}")

    # Run embedder
    print(f"[📦] Embedding files from upload/{session_id}/ ...")
    subprocess.run(["python3", "scripts/embedder.py", session_id])

    # Start Flask server
    print(f"\n[🚀] Starting Flask server at http://localhost:11435 ...")
    os.environ["FLASK_APP"] = "scripts/app.py"
    os.environ["FLASK_RUN_PORT"] = "11435"
    subprocess.run(["flask", "run"])

if __name__ == "__main__":
    main()
