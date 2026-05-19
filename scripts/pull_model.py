#!/usr/bin/env python3
"""
Local Flask helper for Ollama Web UI.

This process serves the static Web UI and proxies browser requests to the local
Ollama daemon. Keeping browser traffic on the same origin avoids direct CORS
issues between the UI and Ollama's default API listener.
"""

from __future__ import annotations

import json
import os
import re
import time
from html.parser import HTMLParser
from pathlib import Path
from threading import Lock
from typing import Any, Iterator

import requests
from flask import Flask, Response, jsonify, request, send_from_directory, stream_with_context
from flask_cors import CORS
from werkzeug.exceptions import HTTPException

BASE_DIR = Path(__file__).resolve().parent.parent
OLLAMA_HOST = os.environ.get("OLLAMA_HOST", "http://127.0.0.1:11434").rstrip("/")
REQUEST_CONNECT_TIMEOUT_SECONDS = 5
REQUEST_READ_TIMEOUT_SECONDS = 600
CATALOG_CACHE_SECONDS = 3600
CATALOG_REQUEST_TIMEOUT_SECONDS = 10
OLLAMA_LIBRARY_URL = os.environ.get("OLLAMA_LIBRARY_URL", "https://ollama.com/library")
MODEL_NAME_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.:/-]{0,127}$")
PULL_ID_RE = re.compile(r"^[A-Za-z0-9_.:-]{1,80}$")
catalog_cache: dict[str, Any] = {"expires_at": 0.0, "models": []}
active_pulls: dict[str, requests.Response] = {}
active_pulls_lock = Lock()

app = Flask(__name__, static_folder=str(BASE_DIR), static_url_path="")
CORS(app, resources={r"/*": {"origins": ["http://127.0.0.1:11435", "http://localhost:11435"]}})


class OllamaLibraryParser(HTMLParser):
    """Extract model catalog entries from Ollama's library page."""

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.models: list[dict[str, Any]] = []
        self._seen_names: set[str] = set()
        self._current: dict[str, Any] | None = None
        self._depth = 0
        self._capture: str | None = None
        self._capture_parts: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        attrs_map = dict(attrs)

        if tag == "li" and "x-test-model" in attrs_map and self._current is None:
            self._current = {
                "name": "",
                "description": "",
                "updated": "",
                "capabilities": [],
                "sizes": [],
            }
            self._depth = 1
            return

        if self._current is None:
            return

        self._depth += 1
        if tag == "div" and "x-test-model-title" in attrs_map:
            self._current["name"] = attrs_map.get("title", "").strip()
        elif tag == "p" and not self._current["description"]:
            self._start_capture("description")
        elif tag == "span" and "x-test-capability" in attrs_map:
            self._start_capture("capabilities")
        elif tag == "span" and "x-test-size" in attrs_map:
            self._start_capture("sizes")
        elif tag == "span" and "x-test-updated" in attrs_map:
            self._start_capture("updated")

    def handle_data(self, data: str) -> None:
        if self._capture:
            self._capture_parts.append(data)

    def handle_endtag(self, tag: str) -> None:
        if self._current is None:
            return

        if self._capture:
            value = " ".join("".join(self._capture_parts).split())
            if value:
                if self._capture in {"capabilities", "sizes"}:
                    self._current[self._capture].append(value)
                else:
                    self._current[self._capture] = value
            self._capture = None
            self._capture_parts = []

        self._depth -= 1
        if self._depth == 0:
            self._finish_current_model()

    def _start_capture(self, field: str) -> None:
        self._capture = field
        self._capture_parts = []

    def _finish_current_model(self) -> None:
        if self._current is None:
            return

        name = str(self._current.get("name", "")).strip()
        capabilities = self._current.get("capabilities", [])
        is_embedding_only = capabilities == ["embedding"]
        if name and name not in self._seen_names and not is_embedding_only:
            self._seen_names.add(name)
            self.models.append(self._current)

        self._current = None


def validate_model_name(model: str | None) -> str | None:
    """Return a stripped model name if it is safe enough to pass to Ollama."""
    if model is None:
        return None

    model = model.strip()
    if not model or not MODEL_NAME_RE.fullmatch(model):
        return None

    return model


def validate_pull_id(pull_id: str | None) -> str | None:
    """Return a client-generated pull id if it is safe to use as a lookup key."""
    if pull_id is None:
        return None

    pull_id = pull_id.strip()
    if not pull_id or not PULL_ID_RE.fullmatch(pull_id):
        return None

    return pull_id


def request_timeout() -> tuple[int, int]:
    """Return the connect and read timeout tuple used for Ollama requests."""
    return (REQUEST_CONNECT_TIMEOUT_SECONDS, REQUEST_READ_TIMEOUT_SECONDS)


def sse_line(message: str) -> str:
    """Format a single Server-Sent Events data message."""
    safe_message = message.replace("\r", " ").replace("\n", " ")
    return f"data: {safe_message}\n\n"


def decode_stream_line(line: str | bytes, encoding: str | None = None) -> str:
    """Return a text line from requests.iter_lines output."""
    if isinstance(line, bytes):
        return line.decode(encoding or "utf-8", errors="replace")

    return line


def load_bundled_model_catalog() -> list[dict[str, Any]]:
    """Load the checked-in fallback model catalog."""
    catalog_path = BASE_DIR / "models.json"
    try:
        payload = json.loads(catalog_path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return []

    if not isinstance(payload, list):
        return []

    return [model for model in payload if isinstance(model, dict) and model.get("name")]


def fetch_ollama_library_catalog() -> list[dict[str, Any]]:
    """Fetch and parse the current public Ollama model library."""
    response = requests.get(
        OLLAMA_LIBRARY_URL,
        params={"sort": "newest"},
        timeout=CATALOG_REQUEST_TIMEOUT_SECONDS,
    )
    response.raise_for_status()

    parser = OllamaLibraryParser()
    parser.feed(response.text)
    return parser.models


def model_catalog() -> list[dict[str, Any]]:
    """Return a cached Ollama library catalog with a bundled fallback."""
    now = time.monotonic()
    cached_models = catalog_cache.get("models")
    if cached_models and now < float(catalog_cache.get("expires_at", 0)):
        return cached_models

    try:
        models = fetch_ollama_library_catalog()
    except requests.RequestException:
        models = load_bundled_model_catalog()

    if not models:
        models = load_bundled_model_catalog()

    catalog_cache["models"] = models
    catalog_cache["expires_at"] = now + CATALOG_CACHE_SECONDS
    return models


def register_active_pull(pull_id: str, upstream: requests.Response) -> None:
    """Track an active Ollama pull stream so it can be cancelled."""
    with active_pulls_lock:
        active_pulls[pull_id] = upstream


def unregister_active_pull(pull_id: str) -> None:
    """Stop tracking an Ollama pull stream."""
    with active_pulls_lock:
        active_pulls.pop(pull_id, None)


def close_active_pull(pull_id: str) -> bool:
    """Close an active Ollama pull stream if one exists."""
    with active_pulls_lock:
        upstream = active_pulls.pop(pull_id, None)

    if upstream is None:
        return False

    upstream.close()
    return True


def proxy_ollama_json(path: str) -> tuple[dict[str, Any], int]:
    """Fetch a non-streaming JSON response from Ollama."""
    try:
        response = requests.get(f"{OLLAMA_HOST}{path}", timeout=request_timeout())
    except requests.RequestException as exc:
        return {"error": f"unable to reach Ollama at {OLLAMA_HOST}: {exc}"}, 502

    try:
        payload = response.json()
    except ValueError:
        payload = {"error": response.text.strip() or "Ollama returned a non-JSON response"}

    return payload, response.status_code


@app.get("/")
def serve_index() -> Response:
    """Serve the main Web UI."""
    return send_from_directory(app.static_folder, "index.html")


@app.get("/health")
def health() -> tuple[Response, int]:
    """Return local helper health and Ollama connectivity status."""
    payload, status = proxy_ollama_json("/api/version")
    helper_status = {
        "status": "ok",
        "ollama_host": OLLAMA_HOST,
        "ollama_connected": 200 <= status < 300,
        "ollama": payload,
    }
    return jsonify(helper_status), 200 if helper_status["ollama_connected"] else 502


@app.get("/api/tags")
def api_tags() -> tuple[Response, int]:
    """Proxy Ollama's local model list."""
    payload, status = proxy_ollama_json("/api/tags")
    return jsonify(payload), status


@app.get("/api/models")
def api_models() -> Response:
    """Return the pullable Ollama model catalog."""
    return jsonify(model_catalog())


@app.post("/api/generate")
def api_generate() -> Response | tuple[Response, int]:
    """Proxy streaming prompt generation to Ollama."""
    body = request.get_json(silent=True) or {}
    model = validate_model_name(body.get("model"))
    prompt = str(body.get("prompt", "")).strip()

    if model is None:
        return jsonify({"error": "invalid or missing model name"}), 400
    if not prompt:
        return jsonify({"error": "missing prompt"}), 400

    upstream_payload = {
        "model": model,
        "prompt": prompt,
        "stream": True,
    }

    try:
        upstream = requests.post(
            f"{OLLAMA_HOST}/api/generate",
            json=upstream_payload,
            stream=True,
            timeout=request_timeout(),
        )
    except requests.RequestException as exc:
        return jsonify({"error": f"unable to reach Ollama at {OLLAMA_HOST}: {exc}"}), 502

    if upstream.status_code >= 400:
        error_text = upstream.text.strip() or "Ollama returned an error"
        upstream.close()
        return jsonify({"error": error_text}), upstream.status_code

    @stream_with_context
    def generate() -> Iterator[str]:
        with upstream:
            for line in upstream.iter_lines(decode_unicode=True):
                if line:
                    line = decode_stream_line(line, upstream.encoding)
                    yield f"{line}\n"

    headers = {
        "Cache-Control": "no-cache",
        "X-Accel-Buffering": "no",
    }
    return Response(generate(), mimetype="application/x-ndjson", headers=headers)


@app.get("/pull_model")
def pull_model() -> Response | tuple[Response, int]:
    """Pull a model through Ollama's API and stream progress to the browser."""
    model = validate_model_name(request.args.get("model"))
    pull_id = validate_pull_id(request.args.get("pull_id"))
    if model is None:
        return jsonify({"error": "invalid or missing model parameter"}), 400
    if pull_id is None:
        return jsonify({"error": "invalid or missing pull_id parameter"}), 400

    try:
        upstream = requests.post(
            f"{OLLAMA_HOST}/api/pull",
            json={"model": model, "stream": True},
            stream=True,
            timeout=request_timeout(),
        )
    except requests.RequestException as exc:
        return jsonify({"error": f"unable to reach Ollama at {OLLAMA_HOST}: {exc}"}), 502

    if upstream.status_code >= 400:
        error_text = upstream.text.strip() or "Ollama returned an error"
        upstream.close()
        return jsonify({"error": error_text}), upstream.status_code

    register_active_pull(pull_id, upstream)

    @stream_with_context
    def stream_pull() -> Iterator[str]:
        try:
            yield sse_line(f"pulling {model}")
            with upstream:
                for line in upstream.iter_lines(decode_unicode=True):
                    if not line:
                        continue

                    line = decode_stream_line(line, upstream.encoding)
                    try:
                        event = json.loads(line)
                    except ValueError:
                        yield sse_line(line)
                        continue

                    status = str(event.get("status", "progress"))
                    completed = event.get("completed")
                    total = event.get("total")

                    if isinstance(completed, int) and isinstance(total, int) and total > 0:
                        percent = completed * 100 / total
                        yield sse_line(f"{status}: {percent:.1f}%")
                    else:
                        yield sse_line(status)

            yield sse_line("success: model pull completed")
        except requests.RequestException as exc:
            yield sse_line(f"pull interrupted: {exc}")
        finally:
            unregister_active_pull(pull_id)
            upstream.close()

    headers = {
        "Cache-Control": "no-cache",
        "X-Accel-Buffering": "no",
    }
    return Response(stream_pull(), mimetype="text/event-stream", headers=headers)


@app.post("/api/pull_model/cancel")
def cancel_pull_model() -> tuple[Response, int]:
    """Cancel an active model pull by closing its upstream Ollama stream."""
    body = request.get_json(silent=True) or {}
    pull_id = validate_pull_id(body.get("pull_id") or request.args.get("pull_id"))
    if pull_id is None:
        return jsonify({"error": "invalid or missing pull_id parameter"}), 400

    return jsonify({"cancelled": close_active_pull(pull_id)}), 200


@app.get("/<path:path>")
def serve_static(path: str) -> Response:
    """Serve static Web UI assets from the project root."""
    return send_from_directory(app.static_folder, path)


@app.errorhandler(HTTPException)
def api_http_error(error: HTTPException) -> Response | tuple[Response, int]:
    """Return JSON errors for API-style routes instead of Flask HTML pages."""
    if request.path.startswith(("/api/", "/pull_model")):
        return jsonify({"error": error.description or error.name}), error.code or 500

    return error


def main() -> None:
    """Run the local Web UI helper."""
    print(f"Starting Ollama Web UI helper on http://127.0.0.1:11435")
    print(f"Proxying Ollama API requests to {OLLAMA_HOST}")
    app.run(host="127.0.0.1", port=11435, threaded=True)


if __name__ == "__main__":
    main()
