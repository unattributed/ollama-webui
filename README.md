# Ollama Web UI

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

MIT License



