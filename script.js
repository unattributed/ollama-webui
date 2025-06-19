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

// 🧹 Strip ANSI control sequences for clean display
function stripAnsiCodes(str) {
  return str.replace(
    /[\u001b\u009b][[()#;?]*(?:[0-9]{1,4}(?:;[0-9]{0,4})*)?[0-9A-ORZcf-nqry=><]/g,
    ''
  );
}

function appendMessage(role, text) {
  const div = document.createElement('div');
  div.className = 'message ' + role;
  div.textContent = text;
  chatContainer.appendChild(div);
  chatContainer.scrollTop = chatContainer.scrollHeight;
}

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

async function fetchModels() {
  const res = await fetch('models.json');
  const models = await res.json();
  modelSelect.innerHTML = '';
  models.forEach(model => {
    const opt = document.createElement('option');
    opt.value = model.name;
    opt.textContent = model.name;
    if (model.name === currentModel) opt.selected = true;
    modelSelect.appendChild(opt);
    modelsMap[model.name] = model;
  });
  updateModelDescription(modelSelect.value);
}

pullModelButton.addEventListener('click', () => {
  const model = modelSelect.value;
  promptInput.placeholder = 'Pulling and loading model...';
  const statusMsg = document.createElement('div');
  statusMsg.className = 'message status';
  statusMsg.textContent = `🔄 Starting ollama run ${model}...`;
  chatContainer.appendChild(statusMsg);
  chatContainer.scrollTop = chatContainer.scrollHeight;

  const evtSource = new EventSource(`http://localhost:11435/pull_model?model=${model}`);
  evtSource.onmessage = function (e) {
    const line = stripAnsiCodes(e.data);
    statusMsg.textContent += '\n' + line;
    chatContainer.scrollTop = chatContainer.scrollHeight;
    if (line.toLowerCase().includes('success')) {
      promptInput.placeholder = 'Ready to Use';
    }
  };
  evtSource.onerror = function () {
    statusMsg.textContent += '\n❌ Connection closed.';
    evtSource.close();
  };
});

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
        const data = JSON.parse(line);
        fullText += data.response;
      } catch {}
    }
  }
  const last = chatContainer.querySelector('.message.ai:last-child');
  if (last) last.remove();
  appendMessage('ai', fullText);
});

fileInput.addEventListener('change', () => {
  filePreview.textContent = '';
  for (const file of fileInput.files) {
    filePreview.textContent += `📄 ${file.name}\n`;
  }
});

modelSelect.addEventListener('change', () => {
  updateModelDescription(modelSelect.value);
});

window.addEventListener('DOMContentLoaded', fetchModels);
