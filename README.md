# Ollama Web UI

A lightweight local Web UI for chatting with models served by Ollama. The Python helper serves the static frontend, proxies browser requests to the local Ollama API, streams model pull progress, and streams generation responses back to the browser.

## Features

- Local browser UI for Ollama models
- Model selector from Ollama's public model library, with `models.json` as a fallback
- Local installed model detection through Ollama `/api/tags`
- Streaming prompt responses through Ollama `/api/generate`
- Streaming model downloads through Ollama `/api/pull`
- File name preview for selected uploads
- Same-origin Flask proxy to avoid direct browser CORS issues

## Requirements

- Parrot OS or another Debian-family Linux system
- Python 3.9 or newer
- Existing project virtual environment at `.venv`, or a new one if this is a fresh checkout
- Ollama installed and listening on `127.0.0.1:11434`

## Setup

From the project directory:

```bash
cd /home/foo/Workspace/ollama-webui
```

Use the existing virtual environment when it already exists:

```bash
source .venv/bin/activate
```

Only create the virtual environment if `.venv` does not already exist:

```bash
test -d .venv || python3 -m venv .venv
source .venv/bin/activate
```

Install the direct runtime dependencies:

```bash
python -m pip install --upgrade pip setuptools wheel
python -m pip install -r requirements.txt
python -m pip check
```

Do not use `pip freeze > requirements.txt` for normal maintenance. This project only needs direct runtime dependencies in `requirements.txt`; freezing every transitive package can reintroduce resolver conflicts.

## Verify Ollama

Confirm Ollama is reachable before starting the Web UI helper:

```bash
curl -sS http://127.0.0.1:11434/api/version
curl -sS http://127.0.0.1:11434/api/tags
```

If Ollama is not running, start it using your local Ollama installation method, for example:

```bash
ollama serve
```

## Start the Web UI

Run the Flask helper from the project root:

```bash
cd /home/foo/Workspace/ollama-webui
source .venv/bin/activate
python scripts/pull_model.py
```

Open the Web UI in your browser:

```text
http://127.0.0.1:11435/
```

Do not open `index.html` directly with a `file://` URL. Use the Flask helper URL so the UI, pull endpoint, and Ollama generation proxy all share the same local origin.

The model selector is scoped to Ollama models that are suitable for this chat UI's `/api/generate` workflow. Embedding-only models, such as text embedding models, are intentionally excluded from the remote catalog because they are not applicable for conversational prompt/response generation in this application.

## Pull a Model

Use the Web UI button, or test the pull endpoint directly:

```bash
curl -N 'http://127.0.0.1:11435/pull_model?model=deepseek-r1'
```

## Smoke Test

Run this from the project root with the virtual environment active:

```bash
python -m pip check
python -m py_compile scripts/pull_model.py scripts/deploy_full_ollama_ui.py
curl -sS http://127.0.0.1:11434/api/version
```

In a second terminal, start the helper:

```bash
source .venv/bin/activate
python scripts/pull_model.py
```

Then test the helper health endpoint:

```bash
curl -sS http://127.0.0.1:11435/health
```

## Install or Remove a Local Copy

Preview installation:

```bash
python scripts/deploy_full_ollama_ui.py --install --dry-run --verbose
```

Install to the default target, `~/ollama-webui`:

```bash
python scripts/deploy_full_ollama_ui.py --install --verbose
```

Remove the installed copy:

```bash
python scripts/deploy_full_ollama_ui.py --uninstall
```

## Project Structure

```text
ollama-webui/
├── index.html
├── style.css
├── script.js
├── models.json
├── requirements.txt
└── scripts/
    ├── deploy_full_ollama_ui.py
    └── pull_model.py
```

## Notes

- The helper defaults to `http://127.0.0.1:11434` for Ollama.
- Override the Ollama API location with `OLLAMA_HOST` when needed:

```bash
OLLAMA_HOST='http://127.0.0.1:11434' python scripts/pull_model.py
```

## License

MIT License
