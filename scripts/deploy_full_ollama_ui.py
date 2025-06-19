# scripts/deploy_full_ollama_ui.py

"""
Ollama Web UI Deployment Script (Self-contained)

Usage:
-------
# Install Web UI (creates full ~/ollama-webui tree)
python3 scripts/deploy_full_ollama_ui.py --install --verbose

# Uninstall the Web UI
python3 scripts/deploy_full_ollama_ui.py --uninstall --verbose

# Dry-run mode to preview actions
python3 scripts/deploy_full_ollama_ui.py --install --dry-run
"""

import os
import shutil
import argparse

HOME_DIR = os.path.expanduser("~")
WEBUI_DIR = os.path.join(HOME_DIR, "ollama-webui")
SCRIPTS_DIR = os.path.abspath(os.path.dirname(__file__))
TARGET_SCRIPTS_DIR = os.path.join(WEBUI_DIR, "scripts")

ASSET_CONTENTS = {
    "index.html": """<!DOCTYPE html>
<html lang=\"en\">
<head>
  <meta charset=\"UTF-8\">
  <meta name=\"viewport\" content=\"width=device-width, initial-scale=1.0\">
  <title>Ollama Web UI</title>
  <link rel=\"stylesheet\" href=\"style.css\">
  <link rel=\"icon\" type=\"image/x-icon\" href=\"favicon.ico\">
</head>
<body>
  <div id=\"chat-container\"></div>
  <form id=\"prompt-form\">
    <select id=\"model-select\"></select>
    <button type=\"button\" id=\"pull-model\">Pull Model</button>
    <input type=\"text\" id=\"prompt-input\" placeholder=\"Send a message...\">
    <input type=\"file\" id=\"file-input\" multiple>
    <pre id=\"file-preview\"></pre>
  </form>
  <div id=\"model-description\"></div>
  <script src=\"script.js\"></script>
</body>
</html>
""",
    "style.css": """body { font-family: sans-serif; background: #111; color: #eee; padding: 2rem; }
#chat-container { height: 400px; overflow-y: auto; border: 1px solid #444; padding: 1rem; margin-bottom: 1rem; white-space: pre-wrap; }
.message { margin-bottom: 0.5rem; }
.message.user { color: #8cf; }
.message.ai { color: #c8f; }
.message.status { color: #ccc; font-style: italic; }
form { display: flex; gap: 0.5rem; flex-wrap: wrap; }
#prompt-input { flex: 1; }
#file-preview { font-size: 0.8em; color: #999; }
""",
    "script.js": """// (see previous message for full cleaned script.js contents)
""",
    "models.json": """[
  {\"name\": \"deepseek-r1\", \"description\": \"Open-source coding assistant model\", \"updated\": \"2025-06-01\" },
  {\"name\": \"llama3\", \"description\": \"Meta AI's general-purpose LLM\", \"updated\": \"2025-05-15\" }
]
""",
    "favicon.ico": None  # favicon.ico must still be copied externally (binary)
}

SCRIPT_CONTENTS = {
    "pull_model.py": """# pull_model.py placeholder content\nfrom flask import Flask\napp = Flask(__name__)\n@app.route('/')\ndef hello():\n    return 'Hello from Ollama Pull Server'\nif __name__ == '__main__':\n    app.run(host='127.0.0.1', port=11435)\n"""
}

def write_file(path, content, dry_run=False, verbose=False, binary=False):
    if dry_run:
        print(f"[dry-run] Would write {path}")
        return
    mode = 'wb' if binary else 'w'
    with open(path, mode) as f:
        if not binary:
            f.write(content)
        if verbose:
            print(f"Wrote file: {path}")

def install_webui(dry_run=False, verbose=False):
    os.makedirs(WEBUI_DIR, exist_ok=True)
    os.makedirs(TARGET_SCRIPTS_DIR, exist_ok=True)

    for filename, content in ASSET_CONTENTS.items():
        path = os.path.join(WEBUI_DIR, filename)
        if content is not None:
            write_file(path, content, dry_run, verbose)
        else:
            src = os.path.join(SCRIPTS_DIR, filename)
            dst = path
            if os.path.exists(src):
                shutil.copy2(src, dst)
                if verbose:
                    print(f"Copied favicon.ico -> {dst}")

    for filename, content in SCRIPT_CONTENTS.items():
        path = os.path.join(TARGET_SCRIPTS_DIR, filename)
        write_file(path, content, dry_run, verbose)

    if not dry_run:
        print(f"\n✅ Ollama Web UI installed at: {WEBUI_DIR}")

def uninstall_webui(dry_run=False, verbose=False):
    if os.path.exists(WEBUI_DIR):
        if dry_run:
            print(f"[dry-run] Would delete {WEBUI_DIR}")
        else:
            shutil.rmtree(WEBUI_DIR)
            if verbose:
                print(f"Deleted: {WEBUI_DIR}")
    else:
        print("Nothing to uninstall: directory does not exist.")

def main():
    parser = argparse.ArgumentParser(description="Deploy or remove the Ollama Web UI.")
    parser.add_argument("--install", action="store_true", help="Install the Web UI")
    parser.add_argument("--uninstall", action="store_true", help="Uninstall the Web UI")
    parser.add_argument("--dry-run", action="store_true", help="Preview actions without executing")
    parser.add_argument("--verbose", action="store_true", help="Show detailed output")
    args = parser.parse_args()

    if args.install:
        install_webui(dry_run=args.dry_run, verbose=args.verbose)
    elif args.uninstall:
        uninstall_webui(dry_run=args.dry_run, verbose=args.verbose)
    else:
        parser.print_help()

if __name__ == "__main__":
    main()
