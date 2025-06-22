# ~/workspace/ollama-webui/scripts/embedder.py
import os
import json
import sys
import requests
from scripts import parser
from scripts.session_manager import session_exists

UPLOAD_DIR = "upload"
EMBEDDINGS_DIR = "embeddings"
CHUNK_SIZE = 500
OLLAMA_EMBED_URL = "http://localhost:11434/api/embeddings"

os.makedirs(EMBEDDINGS_DIR, exist_ok=True)

def chunk_text(text, chunk_size=CHUNK_SIZE):
    words = text.split()
    return [
        " ".join(words[i:i+chunk_size])
        for i in range(0, len(words), chunk_size)
    ]

def generate_embedding(text_chunk):
    payload = {
        "model": "nomic-embed-text",
        "prompt": text_chunk
    }
    try:
        response = requests.post(OLLAMA_EMBED_URL, json=payload)
        response.raise_for_status()
        return response.json().get("embedding", [])
    except requests.RequestException as e:
        print(f"[ERROR] Embedding failed: {e}")
        return []

def embed_all_files(session_id):
    if not session_exists(session_id):
        print(f"[ERROR] Session {session_id} does not exist.")
        return []

    session_dir = os.path.join(UPLOAD_DIR, session_id)
    output_file = os.path.join(EMBEDDINGS_DIR, f"{session_id}.json")
    results = []

    for filename in os.listdir(session_dir):
        filepath = os.path.join(session_dir, filename)
        if not os.path.isfile(filepath):
            continue

        text = parser.extract_text_from_file(filepath).strip()
        if not text:
            continue

        print(f"[+] Processing {filename}")
        for chunk in chunk_text(text):
            embedding = generate_embedding(chunk)
            if embedding:
                results.append({"text": chunk, "embedding": embedding})

    with open(output_file, "w") as f:
        json.dump(results, f, indent=2)

    print(f"✅ Embedded {len(results)} chunks into {output_file}")
    return results

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python scripts/embedder.py <session_id>")
        sys.exit(1)
    embed_all_files(sys.argv[1])
