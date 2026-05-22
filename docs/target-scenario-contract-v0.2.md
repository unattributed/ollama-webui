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
| `file_upload.text_context` | Uploaded file analysis | Browser local file reader | `uploaded_text_context` |
| `project_agent.guardrail_context` | Project Agent guardrails | `/api/project/context` | `project_document_context` |
| `project_agent.search` | Project Agent search | `/api/project/search` | `project_search_context` |
| `project_agent.read_file` | Project Agent file read | `/api/project/read` | `project_file_context` |
| `project_agent.run_tool` | Project Agent tool runner | `/api/project/run` | `local_tool_output_context` |
| `model.catalog_filter` | Model selectors | `/api/models` | `model_selection_context` |

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
