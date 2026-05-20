// script.js, local Ollama chat UI
const chatContainer = document.getElementById('chat-container');
const promptForm = document.getElementById('prompt-form');
const promptInput = document.getElementById('prompt-input');
const modelSelect = document.getElementById('model-select');
const sizeSelect = document.getElementById('size-select');
const fileInput = document.getElementById('file-input');
const filePreview = document.getElementById('file-preview');
const analyzeFilesButton = document.getElementById('analyze-files-btn');
const clearFilesButton = document.getElementById('clear-files-btn');
const pullModelButton = document.getElementById('pull-model');
const modelDescription = document.getElementById('model-description');
const submitButton = document.getElementById('submit-btn');

const MAX_FILE_BYTES = 1024 * 1024;
const MAX_FILE_CONTEXT_CHARS = 12000;
const MAX_TOTAL_FILE_CONTEXT_CHARS = 24000;
const TEXT_FILE_EXTENSIONS = new Set([
  'c',
  'conf',
  'cpp',
  'cs',
  'css',
  'csv',
  'go',
  'h',
  'html',
  'ini',
  'java',
  'js',
  'json',
  'jsx',
  'log',
  'md',
  'php',
  'py',
  'rb',
  'rs',
  'sh',
  'sql',
  'svg',
  'toml',
  'ts',
  'tsx',
  'txt',
  'xml',
  'yaml',
  'yml',
]);

let currentModel = 'deepseek-r1';
let currentSize = '';
let modelsMap = {};
let installedModels = new Set();
let currentPull = null;
let selectedFileContexts = [];

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

function splitModelReference(value) {
  const name = String(value || '').trim();
  const lastColon = name.lastIndexOf(':');
  const lastSlash = name.lastIndexOf('/');

  if (lastColon > lastSlash) {
    return {
      baseName: name.slice(0, lastColon),
      tag: name.slice(lastColon + 1),
    };
  }

  return { baseName: name, tag: '' };
}

function uniqueValues(values) {
  const seen = new Set();
  return values.filter((value) => {
    const normalized = String(value || '').trim();
    const key = normalized.toLowerCase();
    if (!normalized || seen.has(key)) {
      return false;
    }

    seen.add(key);
    return true;
  });
}

function addSizeToModel(modelName, size) {
  const normalized = String(size || '').trim();
  if (!modelName || !normalized || normalized.toLowerCase() === 'latest' || !modelsMap[modelName]) {
    return;
  }

  const sizes = Array.isArray(modelsMap[modelName].sizes) ? modelsMap[modelName].sizes : [];
  modelsMap[modelName].sizes = uniqueValues([...sizes, normalized]);
}

function installedSizesForModel(modelName) {
  const sizes = [];
  installedModels.forEach((installedName) => {
    const { baseName, tag } = splitModelReference(installedName);
    if (baseName === modelName && tag && tag.toLowerCase() !== 'latest') {
      sizes.push(tag);
    }
  });

  return uniqueValues(sizes);
}

function getModelSizes(modelName) {
  const model = modelsMap[modelName];
  const catalogSizes = model && Array.isArray(model.sizes) ? model.sizes : [];
  return uniqueValues([...catalogSizes, ...installedSizesForModel(modelName)]);
}

function selectedModelReference() {
  const modelName = modelSelect.value;
  const size = sizeSelect.value;
  return modelName && size ? `${modelName}:${size}` : modelName;
}

function isModelInstalled(modelName, size = '') {
  if (!modelName) {
    return false;
  }

  const modelReference = size ? `${modelName}:${size}` : modelName;
  return installedModels.has(modelReference) || (!size && installedModels.has(`${modelName}:latest`));
}

function fileExtension(fileName) {
  const dotIndex = String(fileName || '').lastIndexOf('.');
  return dotIndex >= 0 ? fileName.slice(dotIndex + 1).toLowerCase() : '';
}

function isTextLikeFile(file) {
  if (file.type.startsWith('text/')) {
    return true;
  }

  const extension = fileExtension(file.name);
  if (!extension && (!file.type || file.type === 'application/octet-stream')) {
    return true;
  }

  return TEXT_FILE_EXTENSIONS.has(extension);
}

function formatBytes(value) {
  if (value < 1024) {
    return `${value} B`;
  }
  if (value < 1024 * 1024) {
    return `${(value / 1024).toFixed(1)} KB`;
  }
  return `${(value / 1024 / 1024).toFixed(1)} MB`;
}

function readFileAsText(file) {
  return new Promise((resolve, reject) => {
    const reader = new FileReader();
    reader.addEventListener('load', () => resolve(String(reader.result || '')));
    reader.addEventListener('error', () => reject(reader.error || new Error(`Unable to read ${file.name}`)));
    reader.readAsText(file);
  });
}

function buildFileContextPrompt(prompt) {
  if (!selectedFileContexts.length) {
    return prompt;
  }

  const fileSections = selectedFileContexts.map((file) => (
    `File: ${file.name}\nSize: ${formatBytes(file.size)}\nContent:\n${file.content}`
  ));

  return [
    'Use the uploaded file contents below as context for the user request.',
    'If the request asks for analysis, summarize the important points, call out notable issues, and answer using evidence from the files.',
    '',
    fileSections.join('\n\n---\n\n'),
    '',
    `User request: ${prompt}`,
  ].join('\n');
}

function setFileControls(hasFiles) {
  analyzeFilesButton.disabled = !hasFiles;
  clearFilesButton.disabled = !hasFiles;
}

function setPullControls(isPulling) {
  promptInput.placeholder = isPulling ? 'Pulling model...' : 'Send a message...';
  pullModelButton.textContent = isPulling ? 'Cancel Pull' : 'Pull Model';
  pullModelButton.disabled = false;
  modelSelect.disabled = isPulling;
  sizeSelect.disabled = isPulling || sizeSelect.options.length <= 1;
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

function populateSizeSelect(modelName) {
  const sizes = getModelSizes(modelName);
  const preferredSize = sizes.includes(currentSize) ? currentSize : sizes[0] || '';

  sizeSelect.replaceChildren();
  if (sizes.length) {
    sizes.forEach((size) => {
      const option = document.createElement('option');
      option.value = size;
      option.textContent = size;
      sizeSelect.appendChild(option);
    });
  } else {
    const option = document.createElement('option');
    option.value = '';
    option.textContent = 'default';
    sizeSelect.appendChild(option);
  }

  sizeSelect.value = preferredSize;
  currentSize = sizeSelect.value;
  sizeSelect.disabled = Boolean(currentPull) || sizes.length <= 1;
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
  const selectedSize = sizeSelect.value;
  const modelReference = selectedModelReference();
  installed.textContent = isModelInstalled(modelName, selectedSize)
    ? 'Local status: installed'
    : `Local status: ${modelReference} not detected locally`;

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
    const { baseName, tag } = splitModelReference(name);
    if (modelsMap[baseName]) {
      addSizeToModel(baseName, tag);
      return;
    }
    if (modelsMap[name]) {
      return;
    }

    addModelOption({
      name: baseName,
      description: 'Installed local Ollama model.',
      updated: 'local',
      sizes: tag && tag.toLowerCase() !== 'latest' ? [tag] : [],
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

    populateSizeSelect(modelSelect.value);
    setModelDescription(modelSelect.value);
  } catch (error) {
    appendStatus(`Unable to load model catalog: ${error.message}`);
    modelSelect.disabled = true;
    sizeSelect.disabled = true;
    pullModelButton.disabled = true;
    submitButton.disabled = true;
  }
}

function pullSelectedModel() {
  if (currentPull) {
    cancelCurrentPull();
    return;
  }

  const modelName = modelSelect.value;
  const model = selectedModelReference();
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
      if (!sizeSelect.value) {
        installedModels.add(`${model}:latest`);
      }
      addSizeToModel(modelName, sizeSelect.value);
      setModelDescription(modelName);
      finishPull();
    } else if (line.toLowerCase().startsWith('error:')) {
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
  const model = selectedModelReference();
  if (!prompt || !model) {
    return;
  }

  appendMessage('user', prompt);
  promptInput.value = '';
  promptInput.disabled = true;
  submitButton.disabled = true;
  analyzeFilesButton.disabled = true;

  const aiMessage = appendMessage('ai', '');
  const decoder = new TextDecoder();
  let buffer = '';
  let fullText = '';
  const promptWithFiles = buildFileContextPrompt(prompt);

  try {
    const response = await fetch('/api/generate', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ model, prompt: promptWithFiles, stream: true }),
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
    setFileControls(selectedFileContexts.length > 0);
    promptInput.focus();
  }
}

async function previewSelectedFiles() {
  const files = Array.from(fileInput.files || []);
  selectedFileContexts = [];
  filePreview.textContent = '';
  setFileControls(false);

  if (!files.length) {
    return;
  }

  const previewLines = [];
  let remainingChars = MAX_TOTAL_FILE_CONTEXT_CHARS;

  for (const file of files) {
    if (!isTextLikeFile(file)) {
      previewLines.push(`${file.name} (${formatBytes(file.size)}) skipped: not a text-like file.`);
      continue;
    }

    if (file.size > MAX_FILE_BYTES) {
      previewLines.push(`${file.name} (${formatBytes(file.size)}) skipped: larger than ${formatBytes(MAX_FILE_BYTES)}.`);
      continue;
    }

    if (remainingChars <= 0) {
      previewLines.push(`${file.name} skipped: total file context limit reached.`);
      continue;
    }

    try {
      const rawContent = await readFileAsText(file);
      const contentLimit = Math.min(MAX_FILE_CONTEXT_CHARS, remainingChars);
      const content = rawContent.slice(0, contentLimit);
      const truncated = rawContent.length > content.length;

      selectedFileContexts.push({
        name: file.name,
        size: file.size,
        content,
      });
      remainingChars -= content.length;
      previewLines.push(`${file.name} (${formatBytes(file.size)}) ready${truncated ? ', truncated' : ''}.`);
    } catch (error) {
      previewLines.push(`${file.name} (${formatBytes(file.size)}) skipped: ${error.message}`);
    }
  }

  filePreview.textContent = previewLines.join('\n');
  setFileControls(selectedFileContexts.length > 0);
}

function clearSelectedFiles() {
  fileInput.value = '';
  selectedFileContexts = [];
  filePreview.textContent = '';
  setFileControls(false);
}

function analyzeSelectedFiles() {
  if (!selectedFileContexts.length || submitButton.disabled) {
    return;
  }

  promptInput.value = 'Analyze the uploaded file contents.';
  promptForm.requestSubmit();
}

pullModelButton.addEventListener('click', pullSelectedModel);
promptForm.addEventListener('submit', submitPrompt);
fileInput.addEventListener('change', previewSelectedFiles);
analyzeFilesButton.addEventListener('click', analyzeSelectedFiles);
clearFilesButton.addEventListener('click', clearSelectedFiles);
modelSelect.addEventListener('change', () => {
  currentModel = modelSelect.value;
  currentSize = '';
  populateSizeSelect(currentModel);
  setModelDescription(currentModel);
});
sizeSelect.addEventListener('change', () => {
  currentSize = sizeSelect.value;
  setModelDescription(currentModel);
});
window.addEventListener('DOMContentLoaded', fetchModels);
