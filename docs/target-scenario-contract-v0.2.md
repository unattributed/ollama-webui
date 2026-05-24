# Browser-Safe AI Target Scenario Contract v0.2

This document defines the controlled local lab surfaces that the Browser-Safe AI Systems toolkit is allowed to test in this repository.

The machine-readable contract is:

```text
docs/target-scenario-contract-v0.2.json
```

The Flask helper also exposes the same contract at:

```text
/api/browser-safe/target-contract
```

## Purpose

The contract keeps the vulnerable app, toolkit, and article series aligned. A toolkit test should not claim coverage against `ollama-webui` unless it maps to a scenario in the contract or is clearly marked as planned.

## Scope

This repository is an intentionally vulnerable local browser-based AI lab target. It is not a secure product and must not be used with production secrets or exposed to public interfaces.

Allowed scope:

- local loopback browser testing
- local repositories and files owned by the operator
- safe synthetic fixtures
- controlled Project Agent guardrail, search, read, and allowlisted tool-output workflows
- deterministic evidence capture by the toolkit

Out of scope:

- third-party systems
- credential theft
- persistence
- evasion
- destructive commands
- public internet exposure
- production secrets

## Active scenario ids

| Scenario id | Surface | Endpoint or path | Evidence class |
| --- | --- | --- | --- |
| `chat.basic_prompt` | Chat form | `/api/generate` | `browser_chat_generation` |
| `browser.redirect_chain` | Browser-Safe redirect-chain lab pages | `/browser-safe/redirect/start` | `redirect_chain_context` |
| `browser.dom_render_mismatch` | Browser-Safe DOM/render mismatch lab page | `/browser-safe/dom-render-mismatch` | `dom_render_mismatch_context` |
| `browser.iframe_frame_tree` | Browser-Safe iframe/frame-tree lab pages | `/browser-safe/iframe-frame-tree` | `iframe_frame_tree_context` |
| `file_upload.text_context` | Uploaded file analysis | Browser local file reader | `uploaded_text_context` |
| `project_agent.guardrail_context` | Project Agent guardrails | `/api/project/context` | `project_document_context` |
| `project_agent.search` | Project Agent search | `/api/project/search` | `project_search_context` |
| `project_agent.read_file` | Project Agent file read | `/api/project/read` | `project_file_context` |
| `project_agent.run_tool` | Project Agent tool runner | `/api/project/run` | `local_tool_output_context` |
| `model.catalog_filter` | Model selectors | `/api/models` | `model_selection_context` |

## Redirect-chain local lab surface

The redirect-chain lab surface is intentionally local and deterministic. It is used to teach and validate how staged browser navigation can change what a browser-based AI system observes.

Entry point:

```text
/browser-safe/redirect/start
```

Supported safe variants:

```text
baseline
encoded
slow
```

Example local checks with free and open-source tooling:

```bash
curl -i -L http://127.0.0.1:11435/browser-safe/redirect/start?variant=baseline
python -m urllib.request http://127.0.0.1:11435/browser-safe/redirect/start?variant=encoded
```

The surface never redirects to third-party systems. Each hop remains under the local Flask helper and ends at a synthetic browser-safe evidence page.

Toolkit mapping:

```text
guided_lab_id: guided.redirect_chain_evidence
implementation_status: target-ready
```

The `target-ready` status means the vulnerable app exposes the local target behavior and the toolkit may implement evidence capture in a separate branch. It does not mean the toolkit lab is already implemented.


## DOM/render mismatch local lab surface

The DOM/render mismatch lab surface is intentionally local and deterministic. It is used to teach and validate how raw DOM extraction, browser-rendered visible text, CSS-hidden text, offscreen content, ARIA-hidden content, and metadata can diverge.

Entry point:

```text
/browser-safe/dom-render-mismatch
```

Metadata endpoint:

```text
/api/browser-safe/dom-render-mismatch/scenarios
```

Supported safe variants:

```text
baseline
hidden_instruction
rendered_contradiction
```

Example local checks with free and open-source tooling:

```bash
curl -s http://127.0.0.1:11435/api/browser-safe/dom-render-mismatch/scenarios | python -m json.tool
curl -s http://127.0.0.1:11435/browser-safe/dom-render-mismatch?variant=hidden_instruction
```

The surface does not load external scripts, images, fonts, or trackers. It is designed for Playwright-based or purpose-built Python browser evidence capture in the toolkit. Static HTML parsing alone is not sufficient for senior-quality DOM/render mismatch testing because the lab is about the difference between raw DOM state and browser-rendered state.

Toolkit mapping:

```text
guided_lab_id: guided.dom_render_mismatch
implementation_status: target-ready
```

The `target-ready` status means the vulnerable app exposes the local target behavior and the toolkit may implement browser-rendering evidence capture in a separate branch. It does not mean the toolkit lab is already implemented.

## Iframe/frame-tree local lab surface

The iframe/frame-tree lab surface is intentionally local and deterministic. It is used to teach and validate how browser-based AI systems observe same-origin frames, sandboxed frames, srcdoc frames, and nested browsing contexts.

Entry point:

```text
/browser-safe/iframe-frame-tree
```

Metadata endpoint:

```text
/api/browser-safe/iframe-frame-tree/scenarios
```

Supported safe variants:

```text
baseline
sandboxed_frame
srcdoc_hidden_context
nested_frame_chain
```

Example local checks with free and open-source tooling:

```bash
curl -s http://127.0.0.1:11435/api/browser-safe/iframe-frame-tree/scenarios | python -m json.tool
curl -s http://127.0.0.1:11435/browser-safe/iframe-frame-tree?variant=nested_frame_chain
```

The surface does not load external scripts, images, fonts, frames, or trackers. It is designed for Playwright-based or purpose-built Python browser evidence capture in the toolkit. Static HTML parsing alone is not sufficient for senior-quality iframe/frame-tree testing because the lab is about the browser-created frame tree, srcdoc handling, sandbox attributes, frame URLs, nested browsing contexts, and cross-frame rendered text.

Toolkit mapping:

```text
guided_lab_id: guided.iframe_frame_tree_evidence
implementation_status: target-ready
```

The `target-ready` status means the vulnerable app exposes the local target behavior and the toolkit may implement browser-rendering frame-tree evidence capture in a separate branch. It does not mean the toolkit lab is already implemented.

## Traceability rules

1. Every toolkit test that targets `ollama-webui` should reference one scenario id from the JSON contract.
2. Every evidence record should name the scenario id in the target or metadata when that field exists.
3. Documentation must mark unimplemented mappings as planned.
4. New vulnerable app features should not be treated as toolkit coverage until this contract is updated.

## Validation

Run:

```bash
cd /home/foo/Workspace/ollama-webui
python scripts/validate_target_contract.py
```

The validator confirms that the contract has required top-level fields, active scenarios, scenario ids, safety boundaries, expected artifacts, article mappings, and no duplicate scenario ids.

The DOM/render mismatch target explicitly requires browser rendering evidence capture. A valid toolkit implementation must compare raw DOM state, browser-rendered visible text, computed style findings, and screenshot evidence. Static HTML parsing alone is not sufficient for this scenario.
The iframe/frame-tree target explicitly requires browser rendering and frame-tree observation. A valid toolkit implementation must capture the frame tree, frame URLs, top-page DOM snapshot, frame DOM snapshots, sandbox findings, srcdoc findings, cross-frame rendered text, model-bound context, model response, artifact manifest, evidence records, and analyst-readable report. Static HTML parsing alone is not sufficient for this scenario.
