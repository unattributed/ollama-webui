#!/usr/bin/env python3
"""Validate the local Browser-Safe AI iframe/frame-tree target surface."""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from scripts.pull_model import app  # noqa: E402

SCENARIO_ID = "browser.iframe_frame_tree"
LAB_ID = "guided.iframe_frame_tree_evidence"
VARIANTS = {
    "baseline",
    "sandboxed_frame",
    "srcdoc_hidden_context",
    "nested_frame_chain",
}
EXTERNAL_URL_RE = re.compile(r"https?://", re.IGNORECASE)
REQUIRED_CONTRACT_ARTIFACTS = {
    "frame_tree_json",
    "frame_url_list",
    "top_page_dom_snapshot_html",
    "frame_dom_snapshots",
    "sandbox_findings_json",
    "srcdoc_findings_json",
    "cross_frame_rendered_text",
    "model_bound_context",
    "model_response_json",
    "artifact_manifest",
}


def fail(message: str) -> None:
    """Print a validation error and exit."""
    print(f"iframe/frame-tree target validation failed: {message}", file=sys.stderr)
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


def load_contract_scenario(payload: dict[str, Any]) -> dict[str, Any]:
    """Return the iframe/frame-tree scenario from the target contract."""
    for scenario in payload.get("scenarios", []):
        if scenario.get("id") == SCENARIO_ID:
            return scenario
    fail(f"contract is missing scenario {SCENARIO_ID}")


def validate_contract_endpoint(client: Any) -> None:
    """Validate contract traceability for the iframe/frame-tree scenario."""
    response = client.get("/api/browser-safe/target-contract")
    require(response.status_code == 200, "target contract endpoint must return HTTP 200")
    payload = response.get_json()
    require(isinstance(payload, dict), "target contract endpoint must return a JSON object")
    scenario = load_contract_scenario(payload)
    require(scenario.get("status") == "active", "iframe/frame-tree scenario must be active")
    require(scenario.get("endpoint") == "/browser-safe/iframe-frame-tree", "contract endpoint mismatch")
    require(scenario.get("evidence_class") == "iframe_frame_tree_context", "contract evidence class mismatch")
    mapping = scenario.get("toolkit_mapping", {})
    require(mapping.get("guided_lab_id") == LAB_ID, "contract guided lab id mismatch")
    require(mapping.get("implementation_status") == "target-ready", "contract implementation status mismatch")
    artifacts = set(scenario.get("expected_artifacts", []))
    missing = REQUIRED_CONTRACT_ARTIFACTS - artifacts
    require(not missing, f"contract missing expected artifacts: {', '.join(sorted(missing))}")


def validate_scenario_metadata(client: Any) -> None:
    """Validate the iframe/frame-tree scenario metadata endpoint."""
    response = client.get("/api/browser-safe/iframe-frame-tree/scenarios")
    require(response.status_code == 200, "scenario metadata endpoint must return HTTP 200")
    payload = response.get_json()
    require(isinstance(payload, dict), "scenario metadata must be a JSON object")
    require(payload.get("lab_id") == LAB_ID, "metadata lab id mismatch")
    require(payload.get("target_scenario_id") == SCENARIO_ID, "metadata scenario id mismatch")
    require(payload.get("local_only") is True, "metadata must declare local_only true")
    require(payload.get("free_and_open_source_tooling") is True, "metadata must declare FOSS tooling true")
    require(payload.get("requires_browser_rendering") is True, "metadata must require browser rendering")
    require(payload.get("requires_frame_tree_observation") is True, "metadata must require frame-tree observation")
    require(payload.get("static_html_parsing_sufficient") is False, "metadata must reject static-only parsing")
    require(payload.get("external_url_loading") is False, "metadata must reject external URL loading")
    require(payload.get("credential_collection") is False, "metadata must reject credential collection")
    require(payload.get("third_party_tracking") is False, "metadata must reject third-party tracking")
    variants = payload.get("variants")
    require(isinstance(variants, dict), "metadata variants must be an object")
    require(set(variants) == VARIANTS, f"metadata variants mismatch: {sorted(variants)}")
    for name, metadata in variants.items():
        require(metadata.get("entrypoint") == f"/browser-safe/iframe-frame-tree?variant={name}", f"entrypoint mismatch for {name}")
        require(metadata.get("label"), f"missing label for {name}")
        require(metadata.get("expected_observation"), f"missing expected observation for {name}")


def validate_top_page(client: Any, variant: str) -> str:
    """Validate one iframe/frame-tree top-level page."""
    response = client.get(f"/browser-safe/iframe-frame-tree?variant={variant}")
    require(response.status_code == 200, f"top page {variant} must return HTTP 200")
    require_header(response.headers, "X-Browser-Safe-Lab", LAB_ID)
    require_header(response.headers, "X-Browser-Safe-Scenario", SCENARIO_ID)
    require_header(response.headers, "X-Browser-Safe-Variant", variant)
    html = response_text(response)
    require_no_external_urls(f"top page {variant}", html)
    require("<iframe" in html, f"top page {variant} must include an iframe")
    require(SCENARIO_ID in html, f"top page {variant} must include scenario id")
    if variant == "sandboxed_frame":
        require("sandbox=\"\"" in html, "sandboxed_frame must include an empty sandbox attribute")
    if variant == "srcdoc_hidden_context":
        require("srcdoc=" in html, "srcdoc_hidden_context must include a srcdoc iframe")
        require("data-browser-safe-srcdoc=\"true\"" in html, "srcdoc iframe marker is missing")
    if variant == "nested_frame_chain":
        require("frame-nested-1" in html, "nested_frame_chain must include first nested frame")
    return html


def validate_child_frame(client: Any, variant: str, frame_id: str, depth: int) -> str:
    """Validate one iframe/frame-tree child frame endpoint."""
    response = client.get(
        "/browser-safe/iframe-frame-tree/frame"
        f"?variant={variant}&frame_id={frame_id}&depth={depth}"
    )
    require(response.status_code == 200, f"child frame {variant}/{frame_id} must return HTTP 200")
    require_header(response.headers, "X-Browser-Safe-Lab", LAB_ID)
    require_header(response.headers, "X-Browser-Safe-Scenario", SCENARIO_ID)
    require_header(response.headers, "X-Browser-Safe-Variant", variant)
    require_header(response.headers, "X-Browser-Safe-Frame-Id", frame_id)
    html = response_text(response)
    require_no_external_urls(f"child frame {variant}/{frame_id}", html)
    require(SCENARIO_ID in html, f"child frame {variant}/{frame_id} must include scenario id")
    require(f"data-browser-safe-frame-depth=\"{depth}\"" in html, "child frame depth marker mismatch")
    return html


def main() -> None:
    """Run all iframe/frame-tree target checks."""
    with app.test_client() as client:
        validate_contract_endpoint(client)
        validate_scenario_metadata(client)
        for variant in sorted(VARIANTS):
            validate_top_page(client, variant)
        for variant in ("baseline", "sandboxed_frame"):
            validate_child_frame(client, variant, variant, 1)
        nested_one = validate_child_frame(client, "nested_frame_chain", "nested-1", 1)
        require("frame-nested-2" in nested_one, "nested frame depth 1 must include nested depth 2")
        nested_two = validate_child_frame(client, "nested_frame_chain", "nested-2", 2)
        require("frame-nested-3" in nested_two, "nested frame depth 2 must include nested depth 3")
        nested_three = validate_child_frame(client, "nested_frame_chain", "nested-3", 3)
        require("frame-nested-4" not in nested_three, "nested frame depth must stop at 3")

    print("validated iframe/frame-tree target surface")
    print(f"scenario id: {SCENARIO_ID}")
    print(f"guided lab id: {LAB_ID}")
    print(f"variants: {', '.join(sorted(VARIANTS))}")


if __name__ == "__main__":
    main()
