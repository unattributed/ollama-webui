# ~/workspace/ollama-webui/scripts/db.py
import sqlite3
import os
import json
import time

DB_PATH = "embeddings.db"

def init_db():
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS embeddings (
                session_id TEXT,
                chunk TEXT,
                embedding TEXT,
                timestamp INTEGER
            )
        """)
        conn.commit()

def insert_embedding(session_id, chunk, embedding):
    ts = int(time.time())
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute("""
            INSERT INTO embeddings (session_id, chunk, embedding, timestamp)
            VALUES (?, ?, ?, ?)
        """, (session_id, chunk, json.dumps(embedding), ts))
        conn.commit()

def load_embeddings(session_id):
    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.execute("""
            SELECT chunk, embedding FROM embeddings
            WHERE session_id = ?
        """, (session_id,))
        return [{"text": row[0], "embedding": json.loads(row[1])} for row in cursor.fetchall()]

def delete_session_embeddings(session_id):
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute("DELETE FROM embeddings WHERE session_id = ?", (session_id,))
        conn.commit()

if __name__ == "__main__":
    init_db()
    print("✅ SQLite database initialized.")
