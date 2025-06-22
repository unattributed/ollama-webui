# ~/workspace/ollama-webui/scripts/embedder.py
import os
import json
import requests
from scripts import parser

UPLOAD_DIR = "upload"
CHUNK_SIZE = 500  # words
OLLAMA_EMBED_URL = "http://localhost:11434/api/embeddings"

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

def embed_all_files():
    results = []
    for filename in os.listdir(UPLOAD_DIR):
        filepath = os.path.join(UPLOAD_DIR, filename)
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

    return results

if __name__ == "__main__":
    embedded_chunks = embed_all_files()
    print(f"\n✅ Embedded {len(embedded_chunks)} chunks.")
    with open("embeddings.json", "w") as f:
        json.dump(embedded_chunks, f, indent=2)
