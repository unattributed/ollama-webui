// script.js (Streaming pull logs + chat UI)
const chatContainer = document.getElementById('chat-container');
const promptForm = document.getElementById('prompt-form');
const promptInput = document.getElementById('prompt-input');
const modelSelect = document.getElementById('model-select');
const fileInput = document.getElementById('file-input');
const filePreview = document.getElementById('file-preview');
const pullModelButton = document.getElementById('pull-model');
const modelDescription = document.getElementById('model-description');

let currentModel = 'deepseek-r1';
let modelsMap = {};

// Normalize terminal-like output from the pull endpoint before showing it in the UI.
// This keeps log rendering readable when Ollama emits ANSI color/control sequences.
function stripAnsiCodes(str) {
  return str.replace(
    /[\u001b\u009b][[()#;?]*(?:[0-9]{1,4}(?:;[0-9]{0,4})*)?[0-9A-ORZcf-nqry=><]/g,
    ''
  );
}

// Append one message block to the chat stream and keep the newest line in view.
// Role controls CSS styling so operators can distinguish user, model, and status output.
function appendMessage(role, text) {
  const div = document.createElement('div');
  div.className = 'message ' + role;
  div.textContent = text;
  chatContainer.appendChild(div);
  chatContainer.scrollTop = chatContainer.scrollHeight;
}

// Show metadata from models.json for the currently selected model.
// This helps teammates verify they are targeting the expected model/version.
function updateModelDescription(modelName) {
  const model = modelsMap[modelName];
  if (model) {
    modelDescription.innerHTML = `
      <strong>Description:</strong> ${model.description}<br>
      <strong>Updated:</strong> ${model.updated}
    `;
  } else {
    modelDescription.innerHTML = '';
  }
}

// Load the model catalog from local static JSON and populate the selector at page boot.
// Keeping this client-side avoids an extra backend dependency for simple model metadata.
async function fetchModels() {
  const res = await fetch('models.json');
  const models = await res.json();
  modelSelect.innerHTML = '';
  models.forEach(model => {
    // Cache full model objects for quick description updates on selection changes.
    const opt = document.createElement('option');
    opt.value = model.name;
    opt.textContent = model.name;
    if (model.name === currentModel) opt.selected = true;
    modelSelect.appendChild(opt);
    modelsMap[model.name] = model;
  });
  updateModelDescription(modelSelect.value);
}

// Trigger a model pull/run via the Flask helper on localhost:11435 and stream logs via SSE.
// This is intentionally separate from port 11434 so chat traffic and admin pull operations
// stay isolated for debugging and process supervision.
pullModelButton.addEventListener('click', () => {
  const model = modelSelect.value;
  promptInput.placeholder = 'Pulling and loading model...';
  const statusMsg = document.createElement('div');
  statusMsg.className = 'message status';
  statusMsg.textContent = `🔄 Starting ollama run ${model}...`;
  chatContainer.appendChild(statusMsg);
  chatContainer.scrollTop = chatContainer.scrollHeight;

  const evtSource = new EventSource(`http://localhost:11435/pull_model?model=${model}`);
  // Stream server-sent lines from the backend subprocess into one status message block.
  evtSource.onmessage = function (e) {
    const line = stripAnsiCodes(e.data);
    statusMsg.textContent += '\n' + line;
    chatContainer.scrollTop = chatContainer.scrollHeight;
    if (line.toLowerCase().includes('success')) {
      promptInput.placeholder = 'Ready to Use';
    }
  };
  // On connection failure, close the SSE stream to avoid client-side orphan connections.
  evtSource.onerror = function () {
    statusMsg.textContent += '\n❌ Connection closed.';
    evtSource.close();
  };
});

// Send prompt requests directly to Ollama's streaming generate API on localhost:11434.
// The response is NDJSON; this parser accumulates partial chunks into a final message.
promptForm.addEventListener('submit', async (e) => {
  e.preventDefault();
  const prompt = promptInput.value.trim();
  if (!prompt) return;
  appendMessage('user', prompt);
  promptInput.value = '';
  appendMessage('ai', '...thinking...');

  const res = await fetch('http://localhost:11434/api/generate', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ model: modelSelect.value, prompt, stream: true })
  });

  const reader = res.body.getReader();
  let buffer = '', fullText = '';

  while (true) {
    const { done, value } = await reader.read();
    if (done) break;
    buffer += new TextDecoder().decode(value);
    const lines = buffer.split('\n');
    buffer = lines.pop();
    for (const line of lines) {
      if (!line.trim()) continue;
      try {
        // Each JSON line contains an incremental token slice in data.response.
        const data = JSON.parse(line);
        fullText += data.response;
      } catch {}
    }
  }
  const last = chatContainer.querySelector('.message.ai:last-child');
  if (last) last.remove();
  appendMessage('ai', fullText);
});

// Preview selected files locally so operators can confirm upload selection before prompting.
fileInput.addEventListener('change', () => {
  filePreview.textContent = '';
  for (const file of fileInput.files) {
    filePreview.textContent += `📄 ${file.name}\n`;
  }
});

// Refresh the human-readable model metadata whenever selection changes.
modelSelect.addEventListener('change', () => {
  updateModelDescription(modelSelect.value);
});

// Initialize model list once DOM nodes are available.
window.addEventListener('DOMContentLoaded', fetchModels);
