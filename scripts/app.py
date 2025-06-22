# ~/workspace/ollama-webui/scripts/app.py
import os
import zipfile
from flask import Flask, request, jsonify
from werkzeug.utils import secure_filename
from scripts.query_handler import query_pipeline
from scripts.session_manager import create_session, load_sessions, session_exists

UPLOAD_BASE = 'upload'
ALLOWED_EXTENSIONS = {'.txt', '.pdf', '.md', '.zip'}

app = Flask(__name__)
os.makedirs(UPLOAD_BASE, exist_ok=True)

def allowed_file(filename):
    return '.' in filename and os.path.splitext(filename)[1].lower() in ALLOWED_EXTENSIONS

def extract_zip(path, extract_to):
    try:
        with zipfile.ZipFile(path, 'r') as zip_ref:
            zip_ref.extractall(extract_to)
        os.remove(path)  # Remove zip after extraction
    except zipfile.BadZipFile:
        print(f"[!] Bad zip file: {path}")

@app.route('/upload', methods=['POST'])
def upload():
    if 'files' not in request.files:
        return jsonify({"error": "No files part in request"}), 400

    session_id = request.form.get("session_id")
    if not session_id or not session_exists(session_id):
        session_id = create_session("Uploaded files")

    upload_dir = os.path.join(UPLOAD_BASE, session_id)
    os.makedirs(upload_dir, exist_ok=True)

    files = request.files.getlist('files')
    saved = []

    for file in files:
        if file.filename == '':
            continue

        filename = secure_filename(file.filename)
        ext = os.path.splitext(filename)[1].lower()

        if not allowed_file(filename):
            continue

        save_path = os.path.join(upload_dir, filename)
        file.save(save_path)

        if ext == '.zip':
            extract_zip(save_path, upload_dir)
            saved.append(f"Extracted: {filename}")
        else:
            saved.append(f"Saved: {filename}")

    return jsonify({
        "message": f"Uploaded {len(saved)} file(s)",
        "details": saved,
        "session_id": session_id
    })

@app.route("/query", methods=["POST"])
def handle_query():
    data = request.get_json()
    question = data.get("question", "").strip()
    session_id = data.get("session_id")

    if not question:
        return jsonify({"error": "Empty question"}), 400
    if not session_id or not session_exists(session_id):
        session_id = create_session("Chat session")

    answer = query_pipeline(question, session_id)
    return jsonify({"answer": answer, "session_id": session_id})

@app.route("/sessions", methods=["GET"])
def list_sessions():
    return jsonify(load_sessions())

if __name__ == '__main__':
    app.run(debug=True, port=11435)
