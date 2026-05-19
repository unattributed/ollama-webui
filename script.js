// script.js, local Ollama chat UI
const chatContainer = document.getElementById('chat-container');
const promptForm = document.getElementById('prompt-form');
const promptInput = document.getElementById('prompt-input');
const modelSelect = document.getElementById('model-select');
const fileInput = document.getElementById('file-input');
const filePreview = document.getElementById('file-preview');
const pullModelButton = document.getElementById('pull-model');
const modelDescription = document.getElementById('model-description');
const submitButton = document.getElementById('submit-btn');

let currentModel = 'deepseek-r1';
let modelsMap = {};
let installedModels = new Set();

function stripAnsiCodes(value) {
  return String(value).replace(
    /[\u001b\u009b][[()#;?]*(?:[0-9]{1,4}(?:;[0-9]{0,4})*)?[0-9A-ORZcf-nqry=><]/g,
    ''
  );
}

function appendMessage(role, text) {
  const div = document.createElement('div');
  div.className = `message ${role}`;
  div.textContent = text;
  chatContainer.appendChild(div);
  chatContainer.scrollTop = chatContainer.scrollHeight;
  return div;
}

function appendStatus(text) {
  return appendMessage('status', text);
}

function setModelDescription(modelName) {
  const model = modelsMap[modelName];
  modelDescription.replaceChildren();

  if (!model) {
    return;
  }

  const description = document.createElement('div');
  description.textContent = `Description: ${model.description}`;

  const updated = document.createElement('div');
  updated.textContent = `Catalog updated: ${model.updated}`;

  const installed = document.createElement('div');
  installed.textContent = installedModels.has(modelName) || installedModels.has(`${modelName}:latest`)
    ? 'Local status: installed'
    : 'Local status: not detected locally';

  modelDescription.append(description, updated, installed);
}

async function fetchJson(url, options = {}) {
  const response = await fetch(url, options);
  if (!response.ok) {
    const text = await response.text();
    throw new Error(text || `request failed with HTTP ${response.status}`);
  }
  return response.json();
}

async function fetchInstalledModels() {
  try {
    const payload = await fetchJson('/api/tags');
    installedModels = new Set((payload.models || []).flatMap((model) => [model.name, model.model].filter(Boolean)));
  } catch (error) {
    installedModels = new Set();
    appendStatus(`Ollama model list unavailable: ${error.message}`);
  }
}

async function fetchModels() {
  try {
    await fetchInstalledModels();

    const models = await fetchJson('models.json');
    modelsMap = {};
    modelSelect.replaceChildren();

    models.forEach((model) => {
      modelsMap[model.name] = model;
      const option = document.createElement('option');
      option.value = model.name;
      option.textContent = model.name;
      modelSelect.appendChild(option);
    });

    if (modelsMap[currentModel]) {
      modelSelect.value = currentModel;
    } else if (models.length > 0) {
      currentModel = models[0].name;
      modelSelect.value = currentModel;
    }

    setModelDescription(modelSelect.value);
  } catch (error) {
    appendStatus(`Unable to load model catalog: ${error.message}`);
    modelSelect.disabled = true;
    pullModelButton.disabled = true;
    submitButton.disabled = true;
  }
}

function pullSelectedModel() {
  const model = modelSelect.value;
  if (!model) {
    appendStatus('No model selected.');
    return;
  }

  promptInput.placeholder = 'Pulling model...';
  pullModelButton.disabled = true;
  const statusMessage = appendStatus(`Starting model pull: ${model}`);
  const eventSource = new EventSource(`/pull_model?model=${encodeURIComponent(model)}`);

  eventSource.onmessage = (event) => {
    const line = stripAnsiCodes(event.data);
    statusMessage.textContent += `\n${line}`;
    chatContainer.scrollTop = chatContainer.scrollHeight;

    if (line.toLowerCase().startsWith('success:')) {
      promptInput.placeholder = 'Ready to use';
      pullModelButton.disabled = false;
      installedModels.add(model);
      installedModels.add(`${model}:latest`);
      setModelDescription(model);
      eventSource.close();
    }
  };

  eventSource.onerror = () => {
    statusMessage.textContent += '\nConnection closed.';
    promptInput.placeholder = 'Send a message...';
    pullModelButton.disabled = false;
    eventSource.close();
  };
}

async function submitPrompt(event) {
  event.preventDefault();

  const prompt = promptInput.value.trim();
  const model = modelSelect.value;
  if (!prompt || !model) {
    return;
  }

  appendMessage('user', prompt);
  promptInput.value = '';
  promptInput.disabled = true;
  submitButton.disabled = true;

  const aiMessage = appendMessage('ai', '');
  const decoder = new TextDecoder();
  let buffer = '';
  let fullText = '';

  try {
    const response = await fetch('/api/generate', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ model, prompt, stream: true }),
    });

    if (!response.ok || !response.body) {
      const text = await response.text();
      throw new Error(text || `request failed with HTTP ${response.status}`);
    }

    const reader = response.body.getReader();

    while (true) {
      const { done, value } = await reader.read();
      if (done) {
        break;
      }

      buffer += decoder.decode(value, { stream: true });
      const lines = buffer.split('\n');
      buffer = lines.pop() || '';

      for (const line of lines) {
        if (!line.trim()) {
          continue;
        }

        const data = JSON.parse(line);
        if (data.error) {
          throw new Error(data.error);
        }
        if (data.response) {
          fullText += data.response;
          aiMessage.textContent = fullText;
          chatContainer.scrollTop = chatContainer.scrollHeight;
        }
      }
    }

    if (!fullText) {
      aiMessage.textContent = '[no response returned]';
    }
  } catch (error) {
    aiMessage.textContent = `Error: ${error.message}`;
  } finally {
    promptInput.disabled = false;
    submitButton.disabled = false;
    promptInput.focus();
  }
}

function previewSelectedFiles() {
  filePreview.textContent = '';
  for (const file of fileInput.files) {
    filePreview.textContent += `📄 ${file.name} (${file.size} bytes)\n`;
  }
}

pullModelButton.addEventListener('click', pullSelectedModel);
promptForm.addEventListener('submit', submitPrompt);
fileInput.addEventListener('change', previewSelectedFiles);
modelSelect.addEventListener('change', () => {
  currentModel = modelSelect.value;
  setModelDescription(currentModel);
});
window.addEventListener('DOMContentLoaded', fetchModels);
