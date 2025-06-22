# ~/workspace/ollama-webui/scripts/parser.py
import os
import PyPDF2

def read_text_file(path):
    try:
        with open(path, "r", encoding="utf-8") as f:
            return f.read()
    except Exception as e:
        return f"[ERROR] Could not read {path}: {e}"

def read_pdf_file(path):
    try:
        text = ""
        with open(path, "rb") as f:
            reader = PyPDF2.PdfReader(f)
            for page in reader.pages:
                text += page.extract_text() or ""
        return text
    except Exception as e:
        return f"[ERROR] Could not read {path}: {e}"

def extract_text_from_file(path):
    ext = os.path.splitext(path)[1].lower()
    if ext in {".txt", ".md"}:
        return read_text_file(path)
    elif ext == ".pdf":
        return read_pdf_file(path)
    else:
        return ""
