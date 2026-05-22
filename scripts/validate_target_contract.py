#!/usr/bin/env python3
"""Validate the Browser-Safe AI target scenario contract."""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parent.parent
CONTRACT_PATH = REPO_ROOT / "docs" / "target-scenario-contract-v0.2.json"
SCHEMA_VERSION = "browser-safe-ai-target-contract/v0.2"
SCENARIO_ID_RE = re.compile(r"^[a-z][a-z0-9_]*(?:\.[a-z][a-z0-9_]*)+$")
SHA_SAFE_STATUSES = {"active", "planned", "deprecated"}
REQUIRED_SCENARIO_FIELDS = {
    "id",
    "status",
    "ui_surface",
    "endpoint",
    "evidence_class",
    "allowed_tests",
    "disallowed_tests",
    "expected_artifacts",
    "article_parts",
    "toolkit_mapping",
}
REQUIRED_SCENARIOS = {
    "chat.basic_prompt",
    "file_upload.text_context",
    "project_agent.guardrail_context",
    "project_agent.search",
    "project_agent.read_file",
    "project_agent.run_tool",
    "model.catalog_filter",
}


def fail(message: str) -> None:
    """Print a validation error and exit."""
    print(f"target contract validation failed: {message}", file=sys.stderr)
    raise SystemExit(1)


def require_mapping(value: Any, name: str) -> dict[str, Any]:
    """Return a dictionary value or fail."""
    if not isinstance(value, dict):
        fail(f"{name} must be an object")
    return value


def require_non_empty_list(value: Any, name: str) -> list[Any]:
    """Return a non-empty list value or fail."""
    if not isinstance(value, list) or not value:
        fail(f"{name} must be a non-empty list")
    return value


def require_non_empty_string(value: Any, name: str) -> str:
    """Return a non-empty string value or fail."""
    if not isinstance(value, str) or not value.strip():
        fail(f"{name} must be a non-empty string")
    return value


def validate_safety_boundaries(payload: dict[str, Any]) -> None:
    """Validate the safety boundary section."""
    boundaries = require_mapping(payload.get("safety_boundaries"), "safety_boundaries")
    for field in ("authorized_scope", "out_of_scope", "operator_requirements"):
        entries = require_non_empty_list(boundaries.get(field), f"safety_boundaries.{field}")
        for index, entry in enumerate(entries):
            require_non_empty_string(entry, f"safety_boundaries.{field}[{index}]")


def validate_global_limits(payload: dict[str, Any]) -> None:
    """Validate global size and timeout limits."""
    limits = require_mapping(payload.get("global_limits"), "global_limits")
    required_limits = {
        "max_file_bytes",
        "max_file_context_chars",
        "max_total_file_context_chars",
        "max_project_context_chars",
        "project_helper_max_file_bytes",
        "project_helper_max_search_file_bytes",
        "project_helper_max_command_output_chars",
        "project_helper_command_timeout_seconds",
    }
    missing = required_limits - set(limits)
    if missing:
        fail(f"global_limits missing required fields: {', '.join(sorted(missing))}")

    for field in sorted(required_limits):
        value = limits[field]
        if not isinstance(value, int) or value <= 0:
            fail(f"global_limits.{field} must be a positive integer")


def validate_scenario(scenario: Any, index: int) -> str:
    """Validate one scenario and return its id."""
    item = require_mapping(scenario, f"scenarios[{index}]")
    missing = REQUIRED_SCENARIO_FIELDS - set(item)
    if missing:
        fail(f"scenarios[{index}] missing required fields: {', '.join(sorted(missing))}")

    scenario_id = require_non_empty_string(item.get("id"), f"scenarios[{index}].id")
    if not SCENARIO_ID_RE.fullmatch(scenario_id):
        fail(f"invalid scenario id: {scenario_id}")

    status = require_non_empty_string(item.get("status"), f"{scenario_id}.status")
    if status not in SHA_SAFE_STATUSES:
        fail(f"{scenario_id}.status must be one of: {', '.join(sorted(SHA_SAFE_STATUSES))}")

    for field in ("ui_surface", "endpoint", "evidence_class"):
        require_non_empty_string(item.get(field), f"{scenario_id}.{field}")

    for field in ("allowed_tests", "disallowed_tests", "expected_artifacts", "article_parts"):
        values = require_non_empty_list(item.get(field), f"{scenario_id}.{field}")
        for value_index, value in enumerate(values):
            require_non_empty_string(value, f"{scenario_id}.{field}[{value_index}]")

    mapping = require_mapping(item.get("toolkit_mapping"), f"{scenario_id}.toolkit_mapping")
    for field in ("current", "planned"):
        values = require_non_empty_list(mapping.get(field), f"{scenario_id}.toolkit_mapping.{field}")
        for value_index, value in enumerate(values):
            require_non_empty_string(value, f"{scenario_id}.toolkit_mapping.{field}[{value_index}]")

    return scenario_id


def validate_contract(payload: dict[str, Any]) -> None:
    """Validate the complete target contract."""
    if payload.get("schema_version") != SCHEMA_VERSION:
        fail(f"schema_version must be {SCHEMA_VERSION}")

    target = require_mapping(payload.get("target"), "target")
    if target.get("name") != "ollama-webui":
        fail("target.name must be ollama-webui")
    if target.get("production_safe") is not False:
        fail("target.production_safe must be false")
    for field in ("role", "repository", "local_base_url", "allowed_environment"):
        require_non_empty_string(target.get(field), f"target.{field}")

    validate_safety_boundaries(payload)
    validate_global_limits(payload)

    scenarios = require_non_empty_list(payload.get("scenarios"), "scenarios")
    seen: set[str] = set()
    for index, scenario in enumerate(scenarios):
        scenario_id = validate_scenario(scenario, index)
        if scenario_id in seen:
            fail(f"duplicate scenario id: {scenario_id}")
        seen.add(scenario_id)

    missing_required = REQUIRED_SCENARIOS - seen
    if missing_required:
        fail(f"missing required scenarios: {', '.join(sorted(missing_required))}")

    traceability_rules = require_non_empty_list(payload.get("traceability_rules"), "traceability_rules")
    for index, rule in enumerate(traceability_rules):
        require_non_empty_string(rule, f"traceability_rules[{index}]")


def main() -> None:
    """Load and validate the contract file."""
    try:
        payload = json.loads(CONTRACT_PATH.read_text(encoding="utf-8"))
    except FileNotFoundError:
        fail(f"missing contract file: {CONTRACT_PATH}")
    except json.JSONDecodeError as exc:
        fail(f"invalid JSON: {exc}")

    validate_contract(require_mapping(payload, "contract"))
    print(f"validated target contract: {CONTRACT_PATH}")
    print(f"scenario count: {len(payload['scenarios'])}")


if __name__ == "__main__":
    main()
