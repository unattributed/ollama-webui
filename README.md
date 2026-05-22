# Ollama Web UI

A lightweight local Web UI for chatting with models served by Ollama. The Python helper serves the static frontend, proxies browser requests to the local Ollama API, streams model pull progress, and streams generation responses back to the browser.

## Features

- Local browser UI for Ollama models
- Newest-first model selector from Ollama's public model library, with `models.json` as a fallback
- Model type filter with `Any`, `Code Development`, and Ollama capability types such as `Tools`, `Thinking`, `Vision`, `Audio`, and `Embedding`
- Contextual size selector so pulls and chats use a specific available model tag
- Local installed model detection through Ollama `/api/tags`
- Streaming prompt responses through Ollama `/api/generate`
- Streaming model downloads through Ollama `/api/pull`
- Cancel button for an active model pull
- Text-like file analysis through prompt context
- Project Agent panel for scoped local project guardrails, file search/read, and allowlisted development tool execution
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

The model selector defaults to `Any`, which shows locally pullable catalog models the helper can read from Ollama, sorted by the newest `Updated` timestamp exposed by the site. `Code Development` is a local convenience filter, not an official Ollama category; it matches coding-oriented model names and descriptions while the other type filters map directly to Ollama capability tags where available. Cloud-only catalog entries are excluded because this Web UI is built around local Ollama pull and chat workflows.

## Pull a Model

Use the Web UI model and size selectors, or test the pull endpoint directly with a full model tag:

```bash
curl -N 'http://127.0.0.1:11435/pull_model?model=deepseek-r1:7b&pull_id=manual-test'
```

While a pull is active, the Web UI changes the pull button to `Cancel Pull`. Cancelling closes the active upstream Ollama pull stream for that request.

## Analyze Files

Use `Upload File(s)` to select text-like files such as Markdown, plain text, code, CSV, JSON, XML, YAML, or logs. The browser reads supported files locally and adds their contents to the next prompt sent to Ollama.

Click `Analyze Files` to send a default analysis request, or type your own question and press `Send`. Large files are skipped or truncated before being added to the prompt so local models are not overloaded.

## Project Agent

Use the Project Agent panel to give Ollama bounded local project context before asking for coding help. The default project is `/home/foo/Workspace/OSMAP` when it exists.

- `Load Project` validates the project root and summarizes available text files and docs.
- `Add Guardrails` retrieves relevant chunks from `docs/**/*.md` plus root project docs such as `README.md` and `SECURITY.md`.
- `Search` finds matching lines in text-like project files.
- `Read File` attaches one project-relative text file to the next prompt.
- `Run Tool` executes an allowlisted local development command under the project root and attaches stdout/stderr to the next prompt.
- `Clear Context` removes accumulated project context from future prompts.

Project access is restricted to directories under `OLLAMA_WEBUI_PROJECT_ROOTS`, which defaults to `~/Workspace`. The helper skips large files and directories such as `.git`, `.venv`, `target`, `node_modules`, and caches. Tool execution does not use a shell. The current allowlist covers read-only Git commands, common Cargo subcommands, `rustc`, `pytest`, `ruff`, `mypy`, and `python -m` modules such as `pytest`, `py_compile`, `compileall`, `ruff`, `mypy`, and `unittest`.

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
