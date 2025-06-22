# ~/workspace/ollama-webui/scripts/query_handler.py
import math
import requests
from scripts import db

OLLAMA_EMBED_URL = "http://localhost:11434/api/embeddings"
OLLAMA_CHAT_URL = "http://localhost:11434/api/chat"
EMBED_MODEL = "nomic-embed-text"
LLM_MODEL = "deepseek-coder:6.7b"

def embed_query(text):
    try:
        res = requests.post(OLLAMA_EMBED_URL, json={
            "model": EMBED_MODEL,
            "prompt": text
        })
        res.raise_for_status()
        return res.json().get("embedding", [])
    except Exception as e:
        print(f"[ERROR] Failed to embed query: {e}")
        return []

def cosine_similarity(vec1, vec2):
    dot = sum(a*b for a, b in zip(vec1, vec2))
    norm1 = math.sqrt(sum(a*a for a in vec1))
    norm2 = math.sqrt(sum(b*b for b in vec2))
    return dot / (norm1 * norm2 + 1e-8)

def find_relevant_chunks(query_embedding, embedded_chunks, top_k=5):
    ranked = sorted(
        embedded_chunks,
        key=lambda x: cosine_similarity(query_embedding, x["embedding"]),
        reverse=True
    )
    return ranked[:top_k]

def stream_llm(query, context_chunks):
    context = "\n\n".join(chunk["text"] for chunk in context_chunks)
    prompt = f"""Answer the question using the context below.

Context:
{context}

Question: {query}
"""

    try:
        with requests.post(OLLAMA_CHAT_URL, json={
            "model": LLM_MODEL,
            "messages": [{"role": "user", "content": prompt}],
            "stream": True
        }, stream=True) as res:
            res.raise_for_status()
            for line in res.iter_lines():
                if line:
                    yield line.decode("utf-8")
    except Exception as e:
        yield "[ERROR] Streaming failed: " + str(e)

def query_pipeline(question, session_id, stream=False):
    print(f"\n[+] User query: {question}")
    data = db.load_embeddings(session_id)
    if not data:
        return ["[ERROR] No embeddings loaded for this session."]

    q_emb = embed_query(question)
    if not q_emb:
        return ["[ERROR] Failed to embed question."]

    top_chunks = find_relevant_chunks(q_emb, data)
    return stream_llm(question, top_chunks) if stream else ["".join(stream_llm(question, top_chunks))]

if __name__ == "__main__":
    import sys
    if len(sys.argv) < 3:
        print("Usage: python scripts/query_handler.py '<question>' <session_id>")
        sys.exit(1)

    for chunk in query_pipeline(sys.argv[1], sys.argv[2], stream=True):
        print(chunk, end="", flush=True)
