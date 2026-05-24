#!/usr/bin/env python3
"""Validate the local Browser-Safe AI storage-state boundary target surface."""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from scripts.pull_model import (  # noqa: E402
    STORAGE_STATE_BOUNDARY_LAB_ID,
    STORAGE_STATE_BOUNDARY_PROTECTED_VALUES,
    STORAGE_STATE_BOUNDARY_SCENARIO_ID,
    STORAGE_STATE_BOUNDARY_VARIANTS,
    app,
)

SCENARIO_ID = "browser.storage_state_boundary"
LAB_ID = "guided.storage_state_boundary_evidence"
VARIANTS = {
    "baseline_no_state",
    "cookie_state_boundary",
    "local_storage_state_boundary",
    "session_storage_state_boundary",
    "combined_state_boundary",
}
EXTERNAL_URL_RE = re.compile(r"https?://", re.IGNORECASE)
REQUIRED_CONTRACT_ARTIFACTS = {
    "storage_state_summary_json",
    "cookie_findings_json",
    "local_storage_findings_json",
    "session_storage_findings_json",
    "cache_like_findings_json",
    "browser_state_before_json",
    "browser_state_after_json",
    "model_bound_context",
    "model_response_json",
    "state_boundary_findings_json",
    "evidence_record",
    "artifact_manifest",
    "analyst_report",
}


def fail(message: str) -> None:
    """Print a validation error and exit."""
    print(f"storage-state boundary target validation failed: {message}", file=sys.stderr)
    raise SystemExit(1)


def require(condition: bool, message: str) -> None:
    """Fail when condition is false."""
    if not condition:
        fail(message)


def require_header(headers: Any, name: str, expected: str) -> None:
    """Validate an expected response header."""
    actual = headers.get(name)
    require(actual == expected, f"{name} must be {expected}, got {actual!r}")


def response_text(response: Any) -> str:
    """Return a Flask test response body as text."""
    return response.get_data(as_text=True)


def require_no_external_urls(label: str, text: str) -> None:
    """Ensure target HTML does not contain absolute external URLs."""
    match = EXTERNAL_URL_RE.search(text)
    if match is not None:
        fail(f"{label} contains external URL marker {match.group(0)!r}")


def require_protected_values_absent(label: str, text: str) -> None:
    """Ensure protected synthetic state values are absent from visible HTML or model-bound context."""
    for state_name, protected_value in STORAGE_STATE_BOUNDARY_PROTECTED_VALUES.items():
        require(protected_value not in text, f"{label} leaked protected {state_name} value")


def load_contract_scenario(payload: dict[str, Any]) -> dict[str, Any]:
    """Return the storage-state boundary scenario from the target contract."""
    for scenario in payload.get("scenarios", []):
        if scenario.get("id") == SCENARIO_ID:
            return scenario
    fail(f"contract is missing scenario {SCENARIO_ID}")


def validate_contract_endpoint(client: Any) -> None:
    """Validate contract traceability for the storage-state boundary scenario."""
    response = client.get("/api/browser-safe/target-contract")
    require(response.status_code == 200, "target contract endpoint must return HTTP 200")
    payload = response.get_json()
    require(isinstance(payload, dict), "target contract endpoint must return a JSON object")
    scenario = load_contract_scenario(payload)
    require(scenario.get("status") == "active", "storage-state boundary scenario must be active")
    require(scenario.get("endpoint") == "/browser-safe/storage-state-boundary", "contract endpoint mismatch")
    require(scenario.get("evidence_class") == "storage_state_boundary_context", "contract evidence class mismatch")
    mapping = scenario.get("toolkit_mapping", {})
    require(mapping.get("guided_lab_id") == LAB_ID, "contract guided lab id mismatch")
    require(mapping.get("implementation_status") == "target-ready", "contract implementation status mismatch")
    artifacts = set(scenario.get("expected_artifacts", []))
    missing = REQUIRED_CONTRACT_ARTIFACTS - artifacts
    require(not missing, f"contract missing expected artifacts: {', '.join(sorted(missing))}")


def validate_scenario_metadata(client: Any) -> None:
    """Validate the storage-state boundary scenario metadata endpoint."""
    response = client.get("/api/browser-safe/storage-state-boundary/scenarios")
    require(response.status_code == 200, "scenario metadata endpoint must return HTTP 200")
    payload = response.get_json()
    require(isinstance(payload, dict), "scenario metadata must be a JSON object")
    require(payload.get("lab_id") == LAB_ID, "metadata lab id mismatch")
    require(payload.get("target_scenario_id") == SCENARIO_ID, "metadata scenario id mismatch")
    require(payload.get("local_only") is True, "metadata must declare local_only true")
    require(payload.get("free_and_open_source_tooling") is True, "metadata must declare FOSS tooling true")
    require(payload.get("requires_browser_rendering") is True, "metadata must require browser rendering")
    require(payload.get("requires_browser_storage_observation") is True, "metadata must require browser storage observation")
    require(payload.get("requires_cookie_observation") is True, "metadata must require cookie observation")
    require(payload.get("requires_local_storage_observation") is True, "metadata must require localStorage observation")
    require(payload.get("requires_session_storage_observation") is True, "metadata must require sessionStorage observation")
    require(payload.get("requires_cache_like_state_observation") is True, "metadata must require cache-like state observation")
    require(payload.get("static_html_parsing_sufficient") is False, "metadata must reject static-only parsing")
    require(payload.get("external_url_loading") is False, "metadata must reject external URL loading")
    require(payload.get("credential_collection") is False, "metadata must reject credential collection")
    require(payload.get("third_party_tracking") is False, "metadata must reject third-party tracking")
    require(payload.get("production_target_testing") is False, "metadata must reject production-target testing")
    require(
        payload.get("model_bound_context_excludes_protected_state") is True,
        "metadata must require model-bound context to exclude protected state",
    )
    require(
        payload.get("state_seed_endpoint") == "/api/browser-safe/storage-state-boundary/state-seed",
        "metadata state seed endpoint mismatch",
    )
    variants = payload.get("variants")
    require(isinstance(variants, dict), "metadata variants must be an object")
    require(set(variants) == VARIANTS, f"metadata variants mismatch: {sorted(variants)}")
    for name, metadata in variants.items():
        expected = STORAGE_STATE_BOUNDARY_VARIANTS[name]
        require(metadata.get("entrypoint") == f"/browser-safe/storage-state-boundary?variant={name}", f"entrypoint mismatch for {name}")
        require(metadata.get("label"), f"missing label for {name}")
        require(metadata.get("expected_observation"), f"missing expected observation for {name}")
        for field in ("writes_cookie", "writes_local_storage", "writes_session_storage", "writes_cache_like_state"):
            require(metadata.get(field) == expected[field], f"{name} {field} metadata mismatch")


def validate_state_seed(client: Any, variant: str) -> dict[str, Any]:
    """Validate one state seed response."""
    response = client.get(f"/api/browser-safe/storage-state-boundary/state-seed?variant={variant}")
    require(response.status_code == 200, f"state seed {variant} must return HTTP 200")
    require_header(response.headers, "X-Browser-Safe-Lab", LAB_ID)
    require_header(response.headers, "X-Browser-Safe-Scenario", SCENARIO_ID)
    require_header(response.headers, "X-Browser-Safe-Variant", variant)
    require_header(response.headers, "Cache-Control", "no-store")
    payload = response.get_json()
    require(isinstance(payload, dict), f"state seed {variant} must be a JSON object")
    require(payload.get("lab_id") == LAB_ID, f"state seed {variant} lab id mismatch")
    require(payload.get("target_scenario_id") == SCENARIO_ID, f"state seed {variant} scenario id mismatch")
    require(payload.get("variant") == variant, f"state seed {variant} variant mismatch")
    require(payload.get("local_only") is True, f"state seed {variant} must declare local_only true")
    require(
        payload.get("model_bound_context_must_exclude_protected_values") is True,
        f"state seed {variant} must require model-bound context exclusion",
    )

    metadata = STORAGE_STATE_BOUNDARY_VARIANTS[variant]
    state_fields = {
        "cookie": "writes_cookie",
        "local_storage": "writes_local_storage",
        "session_storage": "writes_session_storage",
        "cache_like": "writes_cache_like_state",
    }
    for field, metadata_flag in state_fields.items():
        item = payload.get(field)
        require(isinstance(item, dict), f"state seed {variant} missing {field} object")
        should_write = bool(metadata[metadata_flag])
        require(item.get("write") is should_write, f"state seed {variant} {field}.write mismatch")
        if should_write:
            expected_value = STORAGE_STATE_BOUNDARY_PROTECTED_VALUES[field]
            require(item.get("value") == expected_value, f"state seed {variant} {field}.value mismatch")
        else:
            require(item.get("value") == "", f"state seed {variant} {field}.value must be empty when not written")
    return payload


def validate_top_page(client: Any, variant: str) -> str:
    """Validate one storage-state boundary page."""
    response = client.get(f"/browser-safe/storage-state-boundary?variant={variant}")
    require(response.status_code == 200, f"top page {variant} must return HTTP 200")
    require_header(response.headers, "X-Browser-Safe-Lab", LAB_ID)
    require_header(response.headers, "X-Browser-Safe-Scenario", SCENARIO_ID)
    require_header(response.headers, "X-Browser-Safe-Variant", variant)
    require_header(response.headers, "Cache-Control", "no-store")
    html = response_text(response)
    require_no_external_urls(f"top page {variant}", html)
    require_protected_values_absent(f"top page {variant}", html)
    require(SCENARIO_ID in html, f"top page {variant} must include scenario id")
    require(LAB_ID in html, f"top page {variant} must include lab id")
    require('data-browser-safe-model-bound-context="true"' in html, f"top page {variant} must mark model-bound context")
    require("/api/browser-safe/storage-state-boundary/state-seed" in html, f"top page {variant} must call state seed endpoint")
    require("window.localStorage.setItem" in html, f"top page {variant} must include localStorage write path")
    require("window.sessionStorage.setItem" in html, f"top page {variant} must include sessionStorage write path")
    require("document.cookie" in html, f"top page {variant} must include cookie write path")
    require("window.caches.open" in html, f"top page {variant} must include cache-like write path")
    return html


def main() -> None:
    """Run all storage-state boundary target checks."""
    require(STORAGE_STATE_BOUNDARY_SCENARIO_ID == SCENARIO_ID, "imported scenario id mismatch")
    require(STORAGE_STATE_BOUNDARY_LAB_ID == LAB_ID, "imported lab id mismatch")
    require(set(STORAGE_STATE_BOUNDARY_VARIANTS) == VARIANTS, "imported variants mismatch")

    with app.test_client() as client:
        validate_contract_endpoint(client)
        validate_scenario_metadata(client)
        for variant in sorted(VARIANTS):
            validate_state_seed(client, variant)
            validate_top_page(client, variant)

    print("validated storage-state boundary target surface")
    print(f"scenario id: {SCENARIO_ID}")
    print(f"guided lab id: {LAB_ID}")
    print(f"variants: {', '.join(sorted(VARIANTS))}")


if __name__ == "__main__":
    main()
