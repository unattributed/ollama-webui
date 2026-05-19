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
from pathlib import Path
from typing import Any, Iterator

import requests
from flask import Flask, Response, jsonify, request, send_from_directory, stream_with_context
from flask_cors import CORS
from werkzeug.exceptions import HTTPException

BASE_DIR = Path(__file__).resolve().parent.parent
OLLAMA_HOST = os.environ.get("OLLAMA_HOST", "http://127.0.0.1:11434").rstrip("/")
REQUEST_CONNECT_TIMEOUT_SECONDS = 5
REQUEST_READ_TIMEOUT_SECONDS = 600
MODEL_NAME_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.:/-]{0,127}$")

app = Flask(__name__, static_folder=str(BASE_DIR), static_url_path="")
CORS(app, resources={r"/*": {"origins": ["http://127.0.0.1:11435", "http://localhost:11435"]}})


def validate_model_name(model: str | None) -> str | None:
    """Return a stripped model name if it is safe enough to pass to Ollama."""
    if model is None:
        return None

    model = model.strip()
    if not model or not MODEL_NAME_RE.fullmatch(model):
        return None

    return model


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
    if model is None:
        return jsonify({"error": "invalid or missing model parameter"}), 400

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

    @stream_with_context
    def stream_pull() -> Iterator[str]:
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

    headers = {
        "Cache-Control": "no-cache",
        "X-Accel-Buffering": "no",
    }
    return Response(stream_pull(), mimetype="text/event-stream", headers=headers)


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
