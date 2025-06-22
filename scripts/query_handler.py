# ~/workspace/ollama-webui/scripts/query_handler.py
import json
import math
import requests

EMBEDDINGS_FILE = "embeddings.json"
OLLAMA_EMBED_URL = "http://localhost:11434/api/embeddings"
OLLAMA_CHAT_URL = "http://localhost:11434/api/chat"
EMBED_MODEL = "nomic-embed-text"
LLM_MODEL = "deepseek-coder:6.7b"  # or any model installed

def load_embeddings():
    try:
        with open(EMBEDDINGS_FILE, "r") as f:
            return json.load(f)
    except Exception as e:
        print(f"[ERROR] Cannot load embeddings: {e}")
        return []

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

def ask_llm(query, context_chunks):
    context = "\n\n".join(chunk["text"] for chunk in context_chunks)
    prompt = f"""Answer the question using the context below.

Context:
{context}

Question: {query}
"""

    try:
        res = requests.post(OLLAMA_CHAT_URL, json={
            "model": LLM_MODEL,
            "messages": [{"role": "user", "content": prompt}],
            "stream": False
        })
        res.raise_for_status()
        return res.json()["message"]["content"]
    except Exception as e:
        print(f"[ERROR] Chat failed: {e}")
        return "[ERROR] Could not retrieve response."

def query_pipeline(question):
    print(f"\n[+] User query: {question}")
    data = load_embeddings()
    if not data:
        return "[ERROR] No embeddings loaded."

    q_emb = embed_query(question)
    if not q_emb:
        return "[ERROR] Failed to embed question."

    top_chunks = find_relevant_chunks(q_emb, data)
    return ask_llm(question, top_chunks)

if __name__ == "__main__":
    user_input = input("Ask a question: ")
    answer = query_pipeline(user_input)
    print("\n[💬 Answer]\n", answer)
