# ~/workspace/ollama-webui/scripts/app.py
import os
import zipfile
from flask import Flask, request, jsonify
from werkzeug.utils import secure_filename
from scripts.query_handler import query_pipeline

UPLOAD_FOLDER = 'upload'
ALLOWED_EXTENSIONS = {'.txt', '.pdf', '.md', '.zip'}

app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

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

    files = request.files.getlist('files')
    saved = []

    for file in files:
        if file.filename == '':
            continue

        filename = secure_filename(file.filename)
        ext = os.path.splitext(filename)[1].lower()

        if not allowed_file(filename):
            continue

        save_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(save_path)

        if ext == '.zip':
            extract_zip(save_path, app.config['UPLOAD_FOLDER'])
            saved.append(f"Extracted: {filename}")
        else:
            saved.append(f"Saved: {filename}")

    return jsonify({"message": f"Uploaded {len(saved)} file(s)", "details": saved})


@app.route("/query", methods=["POST"])
def handle_query():
