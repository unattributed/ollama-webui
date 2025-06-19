#!/usr/bin/env python3
# scripts/pull_model.py

import subprocess
import sys
from flask import Flask, request, Response, send_from_directory
from flask_cors import CORS
import os

app = Flask(__name__, static_folder='../', static_url_path='')
CORS(app)

@app.route('/')
def serve_index():
    return send_from_directory(app.static_folder, 'index.html')

@app.route('/<path:path>')
def serve_static(path):
    return send_from_directory(app.static_folder, path)

@app.route('/pull_model', methods=['GET'])
def pull_model():
    model = request.args.get('model')
    if not model:
        return 'Missing model parameter', 400

    def stream_output():
        try:
            process = subprocess.Popen(
                ['ollama', 'run', model],
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                universal_newlines=True,
                bufsize=1
            )
            for line in iter(process.stdout.readline, ''):
                yield f'data: {line.strip()}\n\n'
            process.stdout.close()
            process.wait()
        except Exception as e:
            yield f'data: Error: {str(e)}\n\n'

    return Response(stream_output(), mimetype='text/event-stream')

if __name__ == '__main__':
    print('Starting Ollama pull model server on http://127.0.0.1:11435 ...')
    app.run(host='127.0.0.1', port=11435, threaded=True)
