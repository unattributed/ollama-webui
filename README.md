# Ollama Web UI

Ollama Web UI is an intentionally insecure local lab application for chatting with models served by Ollama.

This project is not a secure product, not a hardened assistant, and not a production-ready AI coding environment. It has no intentional focus on security. It is deliberately useful as a weak, inspectable browser-based LLM target for the AI Browser Security Test Suite in the same spirit that OWASP Juice Shop is useful as an intentionally vulnerable web application.

Use it only on a machine and projects you control. The Project Agent feature can read local files under configured workspace roots and run allowlisted local development tools. That behavior is dangerous by design if pointed at real sensitive repositories or if exposed beyond localhost.

The Python helper serves the static frontend, proxies browser requests to the local Ollama API, streams model pull progress, streams generation responses back to the browser, and exposes intentionally simple local project helper endpoints for testing.

## Insecure Lab Warning

This application deliberately does not provide production security controls:

- no authentication or multi-user isolation
- no hardened browser sandbox
- no protection against prompt injection or model manipulation
- no guarantee that uploaded files, local project files, or tool output are handled safely
- no robust secret detection, redaction, policy engine, or audit boundary
- no safe-by-default authorization model for local file and tool access beyond simple local path and command allowlists

The expected use case is local defensive research, browser-AI testing, and controlled demonstrations by the AI Browser Security Test Suite. Do not bind it to public interfaces, do not use it with production secrets, and do not treat model responses as security decisions.

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
- Browser-Safe AI target scenario contract for toolkit traceability
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


## Browser-Safe AI Target Scenario Contract

This intentionally vulnerable app now publishes a controlled target scenario contract for the Browser-Safe AI Systems toolkit.

Machine-readable contract:

```text
docs/target-scenario-contract-v0.2.json
```

Human-readable contract:

```text
docs/target-scenario-contract-v0.2.md
```

Local helper endpoint:

```text
http://127.0.0.1:11435/api/browser-safe/target-contract
```

The contract defines which local lab surfaces are active, which tests are allowed, which tests are out of scope, which evidence artifacts are expected, and which article-series parts the scenario supports.

Current scenario ids:

```text
chat.basic_prompt
browser.redirect_chain
browser.dom_render_mismatch
browser.iframe_frame_tree
file_upload.text_context
project_agent.guardrail_context
project_agent.search
project_agent.read_file
project_agent.run_tool
model.catalog_filter
```

Validate the contract before treating it as a toolkit target source:

```bash
cd /home/foo/Workspace/ollama-webui
python scripts/validate_target_contract.py
```

The contract does not make this application safer. It makes the deliberately weak lab target more explicit and prevents the toolkit from claiming coverage that the target has not declared.

## Project Agent

Use the Project Agent panel to give Ollama bounded local project context before asking for coding help. The default project is `/home/foo/Workspace/OSMAP` when it exists.

This is a lab feature, not a secure coding agent. Treat every project file,
tool result, and generated answer as untrusted. The feature exists so the test
suite can demonstrate how local project evidence enters an LLM context and why
real systems need stronger isolation, policy controls, redaction, approvals,
and auditing.

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

### Browser-Safe redirect-chain lab target

The local helper includes a deterministic redirect-chain lab surface for Browser-Safe AI Systems guided labs:

```text
/browser-safe/redirect/start?variant=baseline
/api/browser-safe/redirect-chain/scenarios
```

The redirect-chain target remains local-only and uses safe synthetic content. It is intended for free and open-source tooling such as `curl`, browser developer tools, and purpose-built Python helpers supplied by the project.


### Browser-Safe DOM/render mismatch lab target

The local helper includes a deterministic DOM/render mismatch lab surface for Browser-Safe AI Systems guided labs:

```text
/browser-safe/dom-render-mismatch?variant=hidden_instruction
/api/browser-safe/dom-render-mismatch/scenarios
```

The DOM/render mismatch target remains local-only and uses safe synthetic content. It is intended for free and open-source tooling, especially browser automation with Playwright or purpose-built Python helpers supplied by the project. Static HTML parsing alone is not sufficient for this lab because the security question is the difference between raw DOM state and browser-rendered state.

The DOM/render mismatch target explicitly requires browser rendering evidence capture. A valid toolkit implementation must compare raw DOM state, browser-rendered visible text, computed style findings, and screenshot evidence. Static HTML parsing alone is not sufficient.

### Browser-Safe iframe/frame-tree lab target

The local helper includes a deterministic iframe/frame-tree lab surface for Browser-Safe AI Systems guided labs:

```text
/browser-safe/iframe-frame-tree?variant=baseline
/api/browser-safe/iframe-frame-tree/scenarios
```

Supported safe variants:

```text
baseline
sandboxed_frame
srcdoc_hidden_context
nested_frame_chain
```

The iframe/frame-tree target remains local-only and uses safe synthetic content. It is intended for free and open-source tooling, especially browser automation with Playwright or purpose-built Python helpers supplied by the project. Static HTML parsing alone is not sufficient for this lab because the security question requires browser-rendered frame-tree observation, frame URL capture, sandbox attribute review, srcdoc detection, nested browsing context mapping, and cross-frame rendered text collection.

The target deliberately does not load external URLs, collect credentials, use no third-party tracking, and does not support production-target testing. A valid toolkit implementation must fail closed on external URLs, wrong or missing scenario headers, and incomplete frame-tree evidence.
