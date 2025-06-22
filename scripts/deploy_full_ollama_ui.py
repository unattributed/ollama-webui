#!/usr/bin/env python3
# /opt/ollama-webui/scripts/deploy_full_ollama_ui.py

import os
import sys
import base64
import shutil
import subprocess
from pathlib import Path

INSTALL_DIR = Path("/opt/ollama-webui")
FAVICON_B64 = """AAABAAMAEBAAAAAAIAADAQAANgAAABgYAAAAACAAkgEAADkBAAAgIAAAAAAgAOwBAADLAgAAiVBORw0KGgoAAAANSUhEUgAAABAAAAAQCAYAAAAf8/9hAAAAyklEQVR4nNWQXUoDQRCEv+75iUaD2WMEDyQ58Z7DvMVnZzew09M+rEoQDayC6Af90nRVNSW7+52fTk6dKiLQcMRBYmKVE94Md2eaKtvujvJcGIYBVSWlRNw/7Lm6XmF1PgQBAHcch/eVEIJiZqgGbtZrDodH5Ol49G3XkVJiKX3fE283G8yMWuvrBzNvL35Gaw1VpZRCTDkTQ1iULCKo6jycpX4H/ZH6/xj4hZ5+x0D167M/UKKILBada+I4jsQYLxb1kdYaOWfMjBfFTFTc9vdKiAAAAABJRU5ErkJggolQTkcNChoKAAAADUlIRFIAAAAYAAAAGAgGAAAA4Hc9+AAAAVlJREFUeJztlc9q3EAMhz9p5PEueHNIj/sQzTWn0Aduzi19kOYVSi91wrqsbUk9NNkugZBNcKHQ/C4zII2+0R9m5OrDZf7oQUVIgAQ1JSPxTEwgtbBadxSceZ4xK3gkd7c95+fvUBX2+z3D8JNxGiFBBDwC+/7tlsxAFXa7AfekmJIeBEJR8EgoDQ3B7DPNPWAaJ5gHRIVxPzIMO8wqbdviObFed8j19cdsmkqtLRFOZpKZiAjAn33m7wyPJCK4+72PoirU2qIiNG3Dl0+fsYv3F1jTsN1uUVWW1M3XG2xzdkatlb7vD4bMJCJQ1cO62WxOvkBEUEphmias6zpqrYeSPKXn7I99VRURwVR18dIcSzMft25hwF+N/gZ4Azypl4z2qwDujruf5GuvAZidfuzf7MH/BbCHkVvyVT2OaaUU4GUfynN6+F9UFev7nrZtF80gIlitVrg7vwC0Ip+w9DBXIQAAAABJRU5ErkJggolQTkcNChoKAAAADUlIRFIAAAAgAAAAIAgGAAAAc3p69AAAAbNJREFUeJztl8Fu2kAQhr9Zz9oYCFRtlCpXXqNSc63UR2uVN+MlKvVEURtANYbdnR6wU0I4VCQiauQ57Wp25v/2X0vWyKfPH2z2w6jXkGVCMsPMcCIgAJDsfglAf3ixy1vCmvOZKjEElssFRVHgfU5KETMjhEgIgcdh6PdvS8DhxMgkgxjY1ImsUMTt1DfbSO4VJxDDlrtVpJcZnki9DTgSvV5JXW/4vfjF+Pqay3dvWK/XVFVFFSpWq5+IOEAQsd3FcMjNzUdLKZGS4ZxjsbgjhIgI2O4cIoI1G2kStneP/bxzrnElNWKNdwJvx5f4XDEiJonC9ZDpdGpl2cc5wXt/xKbj0TZ+AHawb9fHakSE269fUO89db3mYjRiMpn8M8BzxHA0Rt9fXeHzHBFhPp8jIjjniDE+oBURUkq7wuGQPM9PFm57brdbVL0nz/P7tzu0KaX0yF5VxTn3ZAARQQeDAUVRnNzsqeFaW18M4EXVO4AOoAPoAF4VwOG//+wAVVWdBKHPBdDv90+qez3fQAfQAfy3ANoOl+eMVs/MUFX9O7+dKVo9VUVnsxllWZ4VYH/o+QPq/dGqR/v8+AAAAABJRU5ErkJggg=="""

def write_file(path: Path, content: str, binary=False):
    path.parent.mkdir(parents=True, exist_ok=True)
    mode = "wb" if binary else "w"
    with open(path, mode) as f:
        if binary:
            f.write(base64.b64decode(content))
        else:
            f.write(content)

def uninstall():
    print("🔧 Uninstalling Ollama Web UI...")
    if INSTALL_DIR.exists():
        shutil.rmtree(INSTALL_DIR)
        print(f"✅ Removed {INSTALL_DIR}")
    bin_link = Path("/usr/local/bin/ollama-webui")
    if bin_link.exists():
        bin_link.unlink()
        print(f"✅ Removed symlink {bin_link}")
    sys.exit(0)

def update_shell_path():
    bin_link = Path("/usr/local/bin/ollama-webui")
    target_script = INSTALL_DIR / "scripts" / "pull_model.py"
    if not bin_link.exists():
        bin_link.symlink_to(target_script)
        print(f"🔗 Symlink created: {bin_link} → {target_script}")

def pip_install():
    print("📦 Installing Python dependencies...")
    subprocess.run([sys.executable, "-m", "pip", "install", "-r", str(INSTALL_DIR / "requirements.txt")], check=True)

def main():
    if "--uninstall" in sys.argv:
        uninstall()

    print("🚀 Deploying Ollama Web UI to /opt/ollama-webui ...")

    files = {
        ".gitignore": """# Editor & OS temp files
*.swp
*.swo
*.bak
*.tmp
.DS_Store
Thumbs.db

# Scripts, backups, and uploads
*.zip
*.tar
*.sh
*.log
*~
_tmpbkup/

# files for testing, and development
scripts/__pycache__
tests/__pycache__

# VS Code workspace files (optional)
.vscode/

# Python VENV
.venv/""",
        "index.html": """<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <title>Ollama Web UI</title>
  <link rel="icon" type="image/x-icon" href="favicon.ico" />
  <link rel="stylesheet" href="style.css" />
</head>
<body>
  <div id="app">
    <header>
      <div class="title">🧠 Ollama Web UI</div>
      <div class="model-controls">
        <label for="model-select">Choose Model:</label>
        <select id="model-select"></select>
        <button id="pull-model">Pull Model</button>
      </div>
      <div id="model-description" class="model-description"></div>
    </header>

    <main id="chat-container"></main>

    <div id="upload-area">
      <input type="file" id="file-input" multiple />
      <label for="file-input">📎 Upload File(s)</label>
      <div id="file-preview"></div>
    </div>

    <footer>
      <form id="prompt-form">
        <input
          type="text"
          id="prompt-input"
          placeholder="Send a message..."
          autocomplete="off"
          required
        />
        <button type="submit" id="submit-btn">Send</button>
      </form>
    </footer>
  </div>

  <script src="script.js"></script>
</body>
</html>""",
        "models.json": """[
  {
    "name": "deepseek-r1",
    "description": "DeepSeek-R1 is a family of open reasoning models with performance approaching that of leading models, such as O3 and Gemini 2.5 Pro.",
    "updated": "2 days ago"
  },
  {
    "name": "llama4",
    "description": "Meta's latest collection of multimodal models.",
    "updated": "2 days ago"
  },
  {
    "name": "qwen3",
    "description": "Qwen3 is the latest generation of large language models in Qwen series, offering a comprehensive suite of dense and mixture-of-experts (MoE) models.",
    "updated": "3 weeks ago"
  },
  {
    "name": "qwen2.5vl",
    "description": "Flagship vision-language model of Qwen and also a significant leap from the previous Qwen2-VL.",
    "updated": "3 weeks ago"
  },
  {
    "name": "devstral",
    "description": "Devstral: the best open source model for coding agents",
    "updated": "4 weeks ago"
  },
  {
    "name": "gemma3",
    "description": "The current, most capable model that runs on a single GPU.",
    "updated": "2 months ago"
  },
  {
    "name": "phi4",
    "description": "Phi-4 is a 14B parameter, state-of-the-art open model from Microsoft.",
    "updated": "5 months ago"
  },
  {
    "name": "llama3.1",
    "description": "Llama 3.1 is a new state-of-the-art model from Meta available in 8B, 70B and 405B parameter sizes.",
    "updated": "6 months ago"
  },
  {
    "name": "llama3.3",
    "description": "New state of the art 70B model. Llama 3.3 70B offers similar performance compared to the Llama 3.1 405B model.",
    "updated": "6 months ago"
  },
  {
    "name": "llama3.2",
    "description": "Meta's Llama 3.2 goes small with 1B and 3B models.",
    "updated": "8 months ago"
  }
]""",
        "README.md": """# Ollama Web UI

![Verified Commits](https://img.shields.io/badge/commits-signed-blue?logo=gnupg&label=GPG%20Signed)

A lightweight, client-side JavaScript interface for interacting with Ollama's local model server via `localhost:11434`. Includes a model pull server powered by Flask to install and manage multiple models.

## Features

- Model selector with `:latest` tag support
- ChatGPT-style streaming responses
- Prompt history
- File upload and zip preview
- Model pull interface (`pull_model.py`)
- Automatically detects and downloads models

---

## 🚀 Getting Started

### 1. Clone the Repository

```bash
git clone https://github.com/yourusername/ollama-webui.git
cd ollama-webui
````

### 2. Set Up a Virtual Environment (Recommended)

We strongly recommend using a virtual environment to isolate dependencies.

```bash
python3 -m venv .venv
source .venv/bin/activate
```

### 3. Install Python Dependencies

Make sure you're inside the virtual environment before running:

```bash
pip install -r requirements.txt
```

> If you encounter any missing modules, ensure you're using the correct Python version and have activated the virtual environment.

---

## 🧠 Pulling a Model

Use the Flask-based helper script to pull a model via HTTP.

```bash
python scripts/pull_model.py
```

By default, this will start a local server on [http://127.0.0.1:11435](http://127.0.0.1:11435) and expose `/pull_model?model=MODEL_NAME`.

Example:

```bash
curl http://127.0.0.1:11435/pull_model?model=deepseek-coder:latest
```

---

## 🌐 Using the Web UI

1. Start your Ollama server (if not already running):

```bash
ollama run deepseek-coder:latest
```

2. Open `index.html` in your browser.

> The UI connects to `localhost:11434` to send/receive prompt data.

---

## 📦 Project Structure

```
ollama-webui/
├── index.html           # Web UI (static)
├── style.css            # UI styling
├── script.js            # JS logic for streaming/chat
├── models.json          # Predefined model list
├── pull_model.py        # Flask server to trigger model pulls
└── requirements.txt     # Python dependencies
```

---

## 🔧 Development Tips

* Use `source .venv/bin/activate` each time you start work
* Run `deactivate` to leave the virtual environment
* Update dependencies with `pip freeze > requirements.txt`

---

## 📁 Git Ignore Recommendations

To keep your repository clean and avoid committing CI/CD secrets or workflows unintentionally, make sure the following are in your `.gitignore`:

```
# Editor & OS temp files
*.swp
*.swo
*.bak
*.tmp
.DS_Store
Thumbs.db

# Scripts, backups, and uploads
*.zip
*.tar
*.sh
*.log
*~
_tmpbkup/

# files for testing, and development
scripts/__pycache__
tests/__pycache__

# VS Code workspace files (optional)
.vscode/ #vscode is wonderful
.github/

# Python VENV
.venv/
```

> `.github/` is ignored intentionally if you're managing CI/CD workflows locally or externally.

---

## 🛠️ Requirements

* Python 3.9+
* pip
* Ollama installed and accessible via terminal
* Modern browser (for full Web UI support)

---

## 📜 License

MIT License""",
        "requirements.txt": """Flask==3.1.1
flask-cors==6.0.1""",
        "script.js": """// script.js (Streaming pull logs + chat UI)
const chatContainer = document.getElementById('chat-container');
const promptForm = document.getElementById('prompt-form');
const promptInput = document.getElementById('prompt-input');
const modelSelect = document.getElementById('model-select');
const fileInput = document.getElementById('file-input');
const filePreview = document.getElementById('file-preview');
const pullModelButton = document.getElementById('pull-model');
const modelDescription = document.getElementById('model-description');

let currentModel = 'deepseek-r1';
let modelsMap = {};

// 🧹 Strip ANSI control sequences for clean display
function stripAnsiCodes(str) {
  return str.replace(
    /[\u001b\u009b][[()#;?]*(?:[0-9]{1,4}(?:;[0-9]{0,4})*)?[0-9A-ORZcf-nqry=><]/g,
    ''
  );
}

function appendMessage(role, text) {
  const div = document.createElement('div');
  div.className = 'message ' + role;
  div.textContent = text;
  chatContainer.appendChild(div);
  chatContainer.scrollTop = chatContainer.scrollHeight;
}

function updateModelDescription(modelName) {
  const model = modelsMap[modelName];
  if (model) {
    modelDescription.innerHTML = `
      <strong>Description:</strong> ${model.description}<br>
      <strong>Updated:</strong> ${model.updated}
    `;
  } else {
    modelDescription.innerHTML = '';
  }
}

async function fetchModels() {
  const res = await fetch('models.json');
  const models = await res.json();
  modelSelect.innerHTML = '';
  models.forEach(model => {
    const opt = document.createElement('option');
    opt.value = model.name;
    opt.textContent = model.name;
    if (model.name === currentModel) opt.selected = true;
    modelSelect.appendChild(opt);
    modelsMap[model.name] = model;
  });
  updateModelDescription(modelSelect.value);
}

pullModelButton.addEventListener('click', () => {
  const model = modelSelect.value;
  promptInput.placeholder = 'Pulling and loading model...';
  const statusMsg = document.createElement('div');
  statusMsg.className = 'message status';
  statusMsg.textContent = `🔄 Starting ollama run ${model}...`;
  chatContainer.appendChild(statusMsg);
  chatContainer.scrollTop = chatContainer.scrollHeight;

  const evtSource = new EventSource(`http://localhost:11435/pull_model?model=${model}`);
  evtSource.onmessage = function (e) {
    const line = stripAnsiCodes(e.data);
    statusMsg.textContent += '\n' + line;
    chatContainer.scrollTop = chatContainer.scrollHeight;
    if (line.toLowerCase().includes('success')) {
      promptInput.placeholder = 'Ready to Use';
    }
  };
  evtSource.onerror = function () {
    statusMsg.textContent += '\n❌ Connection closed.';
    evtSource.close();
  };
});

promptForm.addEventListener('submit', async (e) => {
  e.preventDefault();
  const prompt = promptInput.value.trim();
  if (!prompt) return;
  appendMessage('user', prompt);
  promptInput.value = '';
  appendMessage('ai', '...thinking...');

  const res = await fetch('http://localhost:11434/api/generate', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ model: modelSelect.value, prompt, stream: true })
  });

  const reader = res.body.getReader();
  let buffer = '', fullText = '';

  while (true) {
    const { done, value } = await reader.read();
    if (done) break;
    buffer += new TextDecoder().decode(value);
    const lines = buffer.split('\n');
    buffer = lines.pop();
    for (const line of lines) {
      if (!line.trim()) continue;
      try {
        const data = JSON.parse(line);
        fullText += data.response;
      } catch {}
    }
  }
  const last = chatContainer.querySelector('.message.ai:last-child');
  if (last) last.remove();
  appendMessage('ai', fullText);
});

fileInput.addEventListener('change', () => {
  filePreview.textContent = '';
  for (const file of fileInput.files) {
    filePreview.textContent += `📄 ${file.name}\n`;
  }
});

modelSelect.addEventListener('change', () => {
  updateModelDescription(modelSelect.value);
});

window.addEventListener('DOMContentLoaded', fetchModels);""",
        "style.css": """body {
  margin: 0;
  background-color: #1e1e1e;
  font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
  color: #f5f5f5;
  display: flex;
  flex-direction: column;
  height: 100vh;
}

#app {
  display: flex;
  flex-direction: column;
  height: 100%;
}

header {
  background: #2a2a2a;
  padding: 0.5rem 1rem;
  display: flex;
  justify-content: space-between;
  align-items: center;
  border-bottom: 1px solid #444;
}

.title {
  font-size: 1.2rem;
  font-weight: bold;
  color: #ffff66;
}

.model-controls {
  display: flex;
  align-items: center;
  gap: 0.5rem;
}

main#chat-container {
  flex: 1;
  padding: 1rem;
  overflow-y: auto;
  display: flex;
  flex-direction: column;
  gap: 1rem;
}

.message {
  max-width: 80%;
  padding: 0.75rem;
  border-radius: 10px;
  white-space: pre-wrap;
}

.message.user {
  align-self: flex-end;
  background-color: #333;
  color: #fff;
}

.message.ai {
  align-self: flex-start;
  background-color: #444;
  color: #fff;
}

#upload-area {
  padding: 0.5rem 1rem;
  background: #2a2a2a;
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
  border-top: 1px solid #444;
}

#file-input {
  display: none;
}

#upload-area label {
  background-color: #444;
  color: #ffff66;
  padding: 0.5rem 1rem;
  border-radius: 5px;
  cursor: pointer;
  text-align: center;
}

#file-preview {
  font-size: 0.85rem;
  color: #ccc;
  white-space: pre-wrap;
  max-height: 100px;
  overflow-y: auto;
}

footer {
  background: #2a2a2a;
  padding: 0.75rem 1rem;
  display: flex;
  justify-content: center;
  border-top: 1px solid #444;
}

#prompt-form {
  display: flex;
  width: 100%;
  max-width: 800px;
  gap: 0.5rem;
}

#prompt-input {
  flex: 1;
  padding: 0.5rem;
  border: none;
  border-radius: 5px;
  background-color: #1e1e1e;
  color: #fff;
  border: 1px solid #444;
}

#submit-btn {
  background-color: #ffff66;
  color: #000;
  border: none;
  padding: 0.5rem 1rem;
  border-radius: 5px;
  cursor: pointer;
  font-weight: bold;
}""",
        ".github/SECURITY.md": """# trigger
# trigger
# re-trigger
# re-trigger
# verify protection rules""",
        ".github/workflows/security.yml": """name: Security CI

on: [push, pull_request]

jobs:
  audit:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.10'
      - run: pip install pip-audit
      - run: pip-audit -r requirements.txt""",
        "scripts/pull_model.py": """#!/usr/bin/env python3
# scripts/pull_model.py

import subprocess
import sys
from flask import Flask, request, Response, send_from_directory
from flask_cors import CORS
import os

app = Flask(__name__, static_folder='../', static_url_path='')
CORS(app)

@app.route('/')
def serve_index():
    return send_from_directory(app.static_folder, 'index.html')

@app.route('/<path:path>')
def serve_static(path):
    return send_from_directory(app.static_folder, path)

@app.route('/pull_model', methods=['GET'])
def pull_model():
    model = request.args.get('model')
    if not model:
        return 'Missing model parameter', 400

    def stream_output():
        try:
            process = subprocess.Popen(
                ['ollama', 'run', model],
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                universal_newlines=True,
                bufsize=1
            )
            for line in iter(process.stdout.readline, ''):
                yield f'data: {line.strip()}\n\n'
            process.stdout.close()
            process.wait()
        except Exception as e:
            yield f'data: Error: {str(e)}\n\n'

    return Response(stream_output(), mimetype='text/event-stream')

if __name__ == '__main__':
    print('Starting Ollama pull model server on http://127.0.0.1:11435 ...')
    app.run(host='127.0.0.1', port=11435, threaded=True)""",
    }

    for relpath, content in files.items():
        binary = relpath.endswith(".ico")
        write_file(INSTALL_DIR / relpath, content, binary=binary)

    write_file(INSTALL_DIR / "favicon.ico", FAVICON_B64, binary=True)

    for folder in ["scripts", ".github/workflows", "tests", "tmpbkup"]:
        (INSTALL_DIR / folder).mkdir(parents=True, exist_ok=True)

    update_shell_path()
    pip_install()

    print("✅ Deployment complete.")
    print("📁 Installed at: /opt/ollama-webui")
    print("▶️ To start: python3 /opt/ollama-webui/scripts/pull_model.py")

if __name__ == "__main__":
    main()
