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
let currentPull = null;

function stripAnsiCodes(value) {
  return String(value).replace(
    /[\u001b\u009b][[()#;?]*(?:[0-9]{1,4}(?:;[0-9]{0,4})*)?[0-9A-ORZcf-nqry=><]/g,
    ''
  );
}

function previewText(value, maxLength = 180) {
  const text = stripAnsiCodes(value).replace(/\s+/g, ' ').trim();
  if (!text) {
    return '[empty response]';
  }
  return text.length > maxLength ? `${text.slice(0, maxLength)}...` : text;
}

function responseErrorMessage(response, text) {
  try {
    const payload = JSON.parse(text);
    if (payload && typeof payload.error === 'string' && payload.error.trim()) {
      return payload.error;
    }
  } catch {
    // Fall through to a sanitized raw-body preview.
  }

  return `request failed with HTTP ${response.status}: ${previewText(text)}`;
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

function createPullId() {
  if (globalThis.crypto && typeof globalThis.crypto.randomUUID === 'function') {
    return globalThis.crypto.randomUUID();
  }

  return `${Date.now()}-${Math.random().toString(16).slice(2)}`;
}

function setPullControls(isPulling) {
  promptInput.placeholder = isPulling ? 'Pulling model...' : 'Send a message...';
  pullModelButton.textContent = isPulling ? 'Cancel Pull' : 'Pull Model';
  pullModelButton.disabled = false;
  modelSelect.disabled = isPulling;
}

function finishPull(statusText = null) {
  if (currentPull) {
    currentPull.eventSource.close();
    if (statusText) {
      currentPull.statusMessage.textContent += `\n${statusText}`;
      chatContainer.scrollTop = chatContainer.scrollHeight;
    }
  }

  currentPull = null;
  setPullControls(false);
}

function parseGenerateLine(line) {
  try {
    return JSON.parse(line);
  } catch {
    throw new Error(`invalid stream response from /api/generate: ${previewText(line)}`);
  }
}

function setModelDescription(modelName) {
  const model = modelsMap[modelName];
  modelDescription.replaceChildren();

  if (!model) {
    return;
  }

  const description = document.createElement('div');
  description.textContent = `Description: ${model.description || 'No description available.'}`;

  const updated = document.createElement('div');
  updated.textContent = `Catalog updated: ${model.updated || 'unknown'}`;

  const details = [];
  if (Array.isArray(model.capabilities) && model.capabilities.length) {
    details.push(`Capabilities: ${model.capabilities.join(', ')}`);
  }
  if (Array.isArray(model.sizes) && model.sizes.length) {
    details.push(`Sizes: ${model.sizes.join(', ')}`);
  }

  const installed = document.createElement('div');
  installed.textContent = installedModels.has(modelName) || installedModels.has(`${modelName}:latest`)
    ? 'Local status: installed'
    : 'Local status: not detected locally';

  const detailNodes = details.map((detail) => {
    const node = document.createElement('div');
    node.textContent = detail;
    return node;
  });

  modelDescription.append(description, updated, ...detailNodes, installed);
}

async function fetchJson(url, options = {}) {
  const response = await fetch(url, options);
  if (!response.ok) {
    const text = await response.text();
    throw new Error(responseErrorMessage(response, text));
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

async function fetchModelCatalog() {
  try {
    return await fetchJson('/api/models');
  } catch (error) {
    appendStatus(`Ollama model catalog unavailable, using bundled list: ${error.message}`);
    return fetchJson('models.json');
  }
}

function addModelOption(model) {
  if (!model || !model.name || modelsMap[model.name]) {
    return;
  }

  modelsMap[model.name] = model;
  const option = document.createElement('option');
  option.value = model.name;
  option.textContent = model.name;
  modelSelect.appendChild(option);
}

function addInstalledModelsToCatalog() {
  installedModels.forEach((name) => {
    const baseName = name.endsWith(':latest') ? name.slice(0, -7) : name;
    if (modelsMap[baseName] || modelsMap[name]) {
      return;
    }

    addModelOption({
      name,
      description: 'Installed local Ollama model.',
      updated: 'local',
    });
  });
}

async function fetchModels() {
  try {
    await fetchInstalledModels();

    const models = await fetchModelCatalog();
    modelsMap = {};
    modelSelect.replaceChildren();

    models.forEach(addModelOption);
    addInstalledModelsToCatalog();

    if (modelsMap[currentModel]) {
      modelSelect.value = currentModel;
    } else if (modelSelect.options.length > 0) {
      currentModel = modelSelect.options[0].value;
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
  if (currentPull) {
    cancelCurrentPull();
    return;
  }

  const model = modelSelect.value;
  if (!model) {
    appendStatus('No model selected.');
    return;
  }

  const pullId = createPullId();
  const statusMessage = appendStatus(`Starting model pull: ${model}`);
  const eventSource = new EventSource(
    `/pull_model?model=${encodeURIComponent(model)}&pull_id=${encodeURIComponent(pullId)}`
  );

  currentPull = {
    id: pullId,
    model,
    eventSource,
    statusMessage,
    lastLine: '',
    cancelling: false,
  };
  setPullControls(true);

  eventSource.onmessage = (event) => {
    if (!currentPull || currentPull.eventSource !== eventSource) {
      return;
    }

    const line = stripAnsiCodes(event.data);
    if (line === currentPull.lastLine) {
      return;
    }
    currentPull.lastLine = line;
    statusMessage.textContent += `\n${line}`;
    chatContainer.scrollTop = chatContainer.scrollHeight;

    if (line.toLowerCase().startsWith('success:')) {
      installedModels.add(model);
      installedModels.add(`${model}:latest`);
      setModelDescription(model);
      finishPull();
    }
  };

  eventSource.onerror = () => {
    if (!currentPull || currentPull.eventSource !== eventSource) {
      return;
    }

    finishPull(currentPull.cancelling ? 'Pull cancelled.' : 'Connection closed.');
  };
}

async function cancelCurrentPull() {
  if (!currentPull || currentPull.cancelling) {
    return;
  }

  const pull = currentPull;
  pull.cancelling = true;
  pullModelButton.disabled = true;
  pull.statusMessage.textContent += '\nCancel requested.';
  chatContainer.scrollTop = chatContainer.scrollHeight;

  try {
    const response = await fetch('/api/pull_model/cancel', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ pull_id: pull.id }),
    });
    if (!response.ok) {
      const text = await response.text();
      throw new Error(responseErrorMessage(response, text));
    }
  } catch (error) {
    if (currentPull === pull) {
      pull.statusMessage.textContent += `\nCancel request failed: ${error.message}`;
      chatContainer.scrollTop = chatContainer.scrollHeight;
      pullModelButton.disabled = false;
    }
    return;
  }

  if (currentPull === pull) {
    finishPull('Pull cancelled.');
  }
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

    if (!response.ok) {
      const text = await response.text();
      throw new Error(responseErrorMessage(response, text));
    }

    if (!response.body) {
      throw new Error('streaming response body is unavailable');
    }

    const reader = response.body.getReader();
    const handleLine = (line) => {
      if (!line.trim()) {
        return;
      }

      const data = parseGenerateLine(line);
      if (data.error) {
        throw new Error(String(data.error));
      }
      if (data.response) {
        fullText += data.response;
        aiMessage.textContent = fullText;
        chatContainer.scrollTop = chatContainer.scrollHeight;
      }
    };

    while (true) {
      const { done, value } = await reader.read();
      if (done) {
        break;
      }

      buffer += decoder.decode(value, { stream: true });
      const lines = buffer.split('\n');
      buffer = lines.pop() || '';

      for (const line of lines) {
        handleLine(line);
      }
    }

    buffer += decoder.decode();
    handleLine(buffer);

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
