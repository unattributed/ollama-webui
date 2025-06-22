99489ad 2025-06-22 add dev_server.py to automate session creation, embedding, and flask startup
001948d 2025-06-22 add streamed llm response support using ollama api with stream:true
e993536 2025-06-22 replace script.js to support streamed llm response rendering in chat
e9a28e1 2025-06-22 migrate query_handler.py to retrieve session embeddings from sqlite
3ac8f92 2025-06-22 migrate embedder.py to store embeddings in sqlite using db.py
cf4dc06 2025-06-22 add db.py for sqlite-based embedding persistence and retrieval
f5fee8a 2025-06-22 add cleanup.py to remove expired sessions and related files
331688b 2025-06-22 enable session-aware uploads, queries, and sidebar listing in script.js
1af73d0 2025-06-22 add session sidebar and client-side tracking to index.html
964efc4 2025-06-22 update query_handler.py to load session-based embeddings for answering queries
e4e8eab 2025-06-22 update embedder.py to isolate file processing and embeddings by session id
345fd5b 2025-06-22 update app.py to support session-aware upload, query, and session listing api
bd8a13f 2025-06-22 add session_manager.py to handle session creation and metadata tracking
2c4f31f 2025-06-22 connect chat input to /query endpoint and display llm response in ui
74b4cce 2025-06-22 add /query endpoint to app.py for llm-based question answering
6e128a4 2025-06-22 add query_handler.py to embed user prompt and retrieve context-aware llm response
546794d 2025-06-22 add embedder.py to chunk and embed uploaded text using ollama api
3c97c04 2025-06-22 add parser.py for extracting text from txt, md, and pdf files
f9080a1 2025-06-22 move flask upload server to scripts/app.py
0e66745 2025-06-22 implement file validation, upload logic, and progress feedback in script.js
a89a074 2025-06-22 add drag-and-drop and multi-file upload support to index.html
2582d1b 2025-06-22 refactor: simplify script structure and prepare for upload integration
f3beab8 2025-06-22 docs: update readme to reflect current deployment and structure
276c113 2025-06-22 feat: add updated favicon.ico image with finalized GIMP design
ad26b46 2025-06-22 chore: add base64-encoded favicon for deployment embedding
28e7c3a 2025-06-22 fix: reduce unnecessary output and clean up deployment logic
573aac3 2025-06-21 test: verify protection rules on branch push
6d01883 2025-06-21 test: expose CI jobs for branch rules
6885c48 2025-06-21 test: expose CI jobs for branch rules
5092095 2025-06-21 test: trigger CI status check for protection rules
cd28c1d 2025-06-20 chore: simplify requirements.txt to minimal safe set for audit compliance
4ebb4bb 2025-06-20 test: trivial newline to trigger ci
e0b9a0e 2025-06-20 fix: remove .github from .gitignore to enable GitHub Actions workflow
06e63a6 2025-06-20 add gpg signed commits badge to readme and include .gitignore recommendations section
6134297 2025-06-20 add .github directory to .gitignore to exclude ci/cd config from version control
9039017 2025-06-20 updated README.md to include virtual environment and pip usage instructions
8183d3b 2025-06-20 updated README.md to include pip usage
67cecd8 2025-06-20 updated requirements.txt to include missing flask-cors dependency
b71480f 2025-06-20 add .gitignore to exclude unnecessary files from version control
a68128f 2025-06-20 Initial commit of Ollama WebUI