// script.js, local Ollama chat UI
const chatContainer = document.getElementById('chat-container');
const promptForm = document.getElementById('prompt-form');
const promptInput = document.getElementById('prompt-input');
const modelTypeSelect = document.getElementById('model-type-select');
const modelSelect = document.getElementById('model-select');
const sizeSelect = document.getElementById('size-select');
const fileInput = document.getElementById('file-input');
const filePreview = document.getElementById('file-preview');
const analyzeFilesButton = document.getElementById('analyze-files-btn');
const clearFilesButton = document.getElementById('clear-files-btn');
const pullModelButton = document.getElementById('pull-model');
const modelDescription = document.getElementById('model-description');
const submitButton = document.getElementById('submit-btn');
const projectRootInput = document.getElementById('project-root-input');
const projectQueryInput = document.getElementById('project-query-input');
const projectFileInput = document.getElementById('project-file-input');
const projectCommandInput = document.getElementById('project-command-input');
const loadProjectButton = document.getElementById('load-project-btn');
const projectContextButton = document.getElementById('project-context-btn');
const projectSearchButton = document.getElementById('project-search-btn');
const projectReadButton = document.getElementById('project-read-btn');
const projectRunButton = document.getElementById('project-run-btn');
const projectClearButton = document.getElementById('project-clear-btn');
const projectAgentStatus = document.getElementById('project-agent-status');
const projectAgentPreview = document.getElementById('project-agent-preview');

const MAX_FILE_BYTES = 1024 * 1024;
const MAX_FILE_CONTEXT_CHARS = 12000;
const MAX_TOTAL_FILE_CONTEXT_CHARS = 24000;
const MAX_PROJECT_CONTEXT_CHARS = 30000;
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
const MODEL_TYPE_OPTIONS = [
  { value: 'any', label: 'Any' },
  { value: 'code-development', label: 'Code Development' },
  { value: 'tools', label: 'Tools' },
  { value: 'thinking', label: 'Thinking' },
  { value: 'vision', label: 'Vision' },
  { value: 'audio', label: 'Audio' },
  { value: 'embedding', label: 'Embedding' },
];
const CODE_DEVELOPMENT_TERMS = [
  'agentic coding',
  'code',
  'coder',
  'coding',
  'codellama',
  'codegemma',
  'devstral',
  'developer',
  'development',
  'engineering',
  'magicoder',
  'phind',
  'programming',
  'software',
  'sql',
  'starcoder',
  'swe-bench',
];

let currentModel = 'deepseek-r1';
let currentSize = '';
let currentModelType = 'any';
let catalogModels = [];
let modelsMap = {};
let installedModels = new Set();
let currentPull = null;
let selectedFileContexts = [];
let activeProjectRoot = '';
let projectContextEntries = [];

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

function normalizeCapability(value) {
  return String(value || '').trim().toLowerCase();
}

function modelCapabilities(model) {
  return Array.isArray(model.capabilities) ? model.capabilities.map(normalizeCapability).filter(Boolean) : [];
}

function updatedSortValue(model) {
  const updated = String(model.updated || '').trim().toLowerCase();
  if (!updated || updated === 'local') {
    return Number.POSITIVE_INFINITY;
  }
  if (updated === 'today' || updated === 'yesterday') {
    return updated === 'today' ? 0 : 1;
  }

  const match = updated.match(/(\d+(?:\.\d+)?)\s*(minute|hour|day|week|month|year)s?\s+ago/);
  if (!match) {
    return Number.POSITIVE_INFINITY;
  }

  const amount = Number(match[1]);
  const unitDays = {
    minute: 1 / 1440,
    hour: 1 / 24,
    day: 1,
    week: 7,
    month: 30,
    year: 365,
  };
  return amount * unitDays[match[2]];
}

function compareModelsByRecency(left, right) {
  const recencyDelta = updatedSortValue(left) - updatedSortValue(right);
  if (recencyDelta !== 0) {
    return recencyDelta;
  }

  return String(left.name || '').localeCompare(String(right.name || ''));
}

function isCodeDevelopmentModel(model) {
  const haystack = [
    model.name,
    model.description,
    ...(Array.isArray(model.capabilities) ? model.capabilities : []),
  ].join(' ').toLowerCase();

  return CODE_DEVELOPMENT_TERMS.some((term) => haystack.includes(term));
}

function modelMatchesType(model, type) {
  if (type === 'any') {
    return true;
  }
  if (type === 'code-development') {
    return isCodeDevelopmentModel(model);
  }

  return modelCapabilities(model).includes(type);
}

function populateModelTypeSelect() {
  modelTypeSelect.replaceChildren();
  MODEL_TYPE_OPTIONS.forEach((type) => {
    const option = document.createElement('option');
    option.value = type.value;
    option.textContent = type.label;
    modelTypeSelect.appendChild(option);
  });
  modelTypeSelect.value = currentModelType;
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

function updateSelectedModelControls() {
  const hasModels = modelSelect.options.length > 0;
  modelSelect.disabled = Boolean(currentPull) || !hasModels;

  if (!currentPull) {
    pullModelButton.disabled = !hasModels;
  }

  submitButton.disabled = !hasModels;
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

function boundedProjectContextText() {
  let remaining = MAX_PROJECT_CONTEXT_CHARS;
  const sections = [];

  projectContextEntries.forEach((entry) => {
    if (remaining <= 0) {
      return;
    }

    const header = `Source: ${entry.title}`;
    const content = String(entry.content || '');
    const section = `${header}\n${content}`;
    const boundedSection = section.slice(0, remaining);
    sections.push(boundedSection);
    remaining -= boundedSection.length;
  });

  return sections.join('\n\n---\n\n');
}

function buildFileContextPrompt(prompt) {
  const sections = [];

  if (projectContextEntries.length) {
    sections.push([
      'Use the local project context below as guardrails for this request.',
      'Prefer project documentation and tool output over general assumptions, and cite relevant source paths when useful.',
      '',
      boundedProjectContextText(),
    ].join('\n'));
  }

  if (selectedFileContexts.length) {
    const fileSections = selectedFileContexts.map((file) => (
      `File: ${file.name}\nSize: ${formatBytes(file.size)}\nContent:\n${file.content}`
    ));
    sections.push([
      'Use the uploaded file contents below as additional context.',
      '',
      fileSections.join('\n\n---\n\n'),
    ].join('\n'));
  }

  if (!sections.length) {
    return prompt;
  }

  return [
    ...sections,
    'Answer the user request using the provided evidence.',
    '',
    `User request: ${prompt}`,
  ].join('\n\n');
}

function setFileControls(hasFiles) {
  analyzeFilesButton.disabled = !hasFiles;
  clearFilesButton.disabled = !hasFiles;
}

function setPullControls(isPulling) {
  promptInput.placeholder = isPulling ? 'Pulling model...' : 'Send a message...';
  pullModelButton.textContent = isPulling ? 'Cancel Pull' : 'Pull Model';
  modelTypeSelect.disabled = isPulling;
  modelSelect.disabled = isPulling;
  sizeSelect.disabled = isPulling || sizeSelect.options.length <= 1;
  if (isPulling) {
    pullModelButton.disabled = false;
    pullModelButton.title = '';
  } else {
    updateSelectedModelControls();
  }
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

function setProjectStatus(text) {
  projectAgentStatus.textContent = text;
}

function setProjectBusy(isBusy) {
  [
    loadProjectButton,
    projectContextButton,
    projectSearchButton,
    projectReadButton,
    projectRunButton,
    projectClearButton,
  ].forEach((button) => {
    button.disabled = isBusy;
  });
}

function updateProjectPreview() {
  if (!projectContextEntries.length) {
    projectAgentPreview.textContent = 'No project context attached.';
    return;
  }

  projectAgentPreview.textContent = projectContextEntries
    .map((entry, index) => `${index + 1}. ${entry.title}\n${previewText(entry.content, 700)}`)
    .join('\n\n');
}

function projectQuery() {
  return projectQueryInput.value.trim() || promptInput.value.trim() || 'security architecture implementation coding guardrails';
}

async function fetchProjectJson(url, payload) {
  return fetchJson(url, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  });
}

function addProjectContextEntry(title, content) {
  projectContextEntries.push({ title, content });
  updateProjectPreview();
}

async function loadProjectDefaults() {
  try {
    const defaults = await fetchJson('/api/project/defaults');
    if (defaults.default_project && !projectRootInput.value.trim()) {
      projectRootInput.value = defaults.default_project;
    }
    activeProjectRoot = projectRootInput.value.trim();
    setProjectStatus(`Allowed roots: ${(defaults.allowed_roots || []).join(', ')}`);
  } catch (error) {
    setProjectStatus(`Project agent unavailable: ${error.message}`);
  }
  updateProjectPreview();
}

async function loadProjectSummary() {
  const projectRoot = projectRootInput.value.trim();
  if (!projectRoot) {
    setProjectStatus('Enter a project root first.');
    return;
  }

  setProjectBusy(true);
  try {
    const summary = await fetchProjectJson('/api/project/summary', { project_root: projectRoot });
    activeProjectRoot = summary.project_root;
    projectRootInput.value = activeProjectRoot;
    setProjectStatus(`Loaded ${activeProjectRoot}: ${summary.file_count} text files, ${summary.doc_count} guardrail docs.`);
    addProjectContextEntry(
      `Project summary: ${activeProjectRoot}`,
      `Text files: ${summary.file_count}\nGuardrail docs: ${summary.doc_count}\nDocs:\n${(summary.docs || []).join('\n')}`
    );
  } catch (error) {
    setProjectStatus(`Project load failed: ${error.message}`);
  } finally {
    setProjectBusy(false);
  }
}

async function addProjectGuardrails() {
  const projectRoot = projectRootInput.value.trim();
  if (!projectRoot) {
    setProjectStatus('Enter a project root first.');
    return;
  }

  setProjectBusy(true);
  try {
    const payload = await fetchProjectJson('/api/project/context', {
      project_root: projectRoot,
      query: projectQuery(),
      max_chunks: 8,
    });
    activeProjectRoot = payload.project_root;
    const content = (payload.chunks || []).map((chunk) => (
      `Path: ${chunk.path}${chunk.heading ? `\nHeading: ${chunk.heading}` : ''}\n${chunk.text}`
    )).join('\n\n---\n\n');
    addProjectContextEntry(`Guardrails for: ${payload.query || projectQuery()}`, content || 'No matching guardrails found.');
    setProjectStatus(`Added ${(payload.chunks || []).length} guardrail chunks from ${activeProjectRoot}.`);
  } catch (error) {
    setProjectStatus(`Guardrail retrieval failed: ${error.message}`);
  } finally {
    setProjectBusy(false);
  }
}

async function searchProject() {
  const query = projectQueryInput.value.trim() || promptInput.value.trim();
  if (!query) {
    setProjectStatus('Enter a search query first.');
    return;
  }

  setProjectBusy(true);
  try {
    const payload = await fetchProjectJson('/api/project/search', {
      project_root: projectRootInput.value.trim(),
      query,
      max_results: 30,
    });
    const content = (payload.results || []).map((result) => (
      `${result.path}:${result.line}: ${result.text}`
    )).join('\n');
    addProjectContextEntry(`Search: ${query}`, content || 'No matches.');
    setProjectStatus(`Added ${(payload.results || []).length} search results.`);
  } catch (error) {
    setProjectStatus(`Search failed: ${error.message}`);
  } finally {
    setProjectBusy(false);
  }
}

async function readProjectFile() {
  const path = projectFileInput.value.trim();
  if (!path) {
    setProjectStatus('Enter a project-relative file path first.');
    return;
  }

  setProjectBusy(true);
  try {
    const payload = await fetchProjectJson('/api/project/read', {
      project_root: projectRootInput.value.trim(),
      path,
    });
    addProjectContextEntry(
      `File: ${payload.path}`,
      `${payload.content}${payload.truncated ? '\n\n[truncated]' : ''}`
    );
    setProjectStatus(`Added file context: ${payload.path}`);
  } catch (error) {
    setProjectStatus(`Read failed: ${error.message}`);
  } finally {
    setProjectBusy(false);
  }
}

async function runProjectTool() {
  const command = projectCommandInput.value.trim();
  if (!command) {
    setProjectStatus('Enter an allowed tool command first.');
    return;
  }

  setProjectBusy(true);
  try {
    const payload = await fetchProjectJson('/api/project/run', {
      project_root: projectRootInput.value.trim(),
      command,
    });
    const content = [
      `Command: ${payload.command}`,
      `Exit code: ${payload.exit_code}${payload.timed_out ? ' (timed out)' : ''}`,
      `Duration: ${payload.duration_ms || 0} ms`,
      '',
      'STDOUT:',
      payload.stdout || '[empty]',
      '',
      'STDERR:',
      payload.stderr || '[empty]',
    ].join('\n');
    addProjectContextEntry(`Tool output: ${command}`, content);
    setProjectStatus(`Tool finished: ${command} (exit ${payload.exit_code})`);
  } catch (error) {
    setProjectStatus(`Tool failed: ${error.message}`);
  } finally {
    setProjectBusy(false);
  }
}

function clearProjectContext() {
  projectContextEntries = [];
  updateProjectPreview();
  setProjectStatus('Project context cleared.');
}

function addModelOption(model) {
  const option = document.createElement('option');
  option.value = model.name;
  option.textContent = model.name;
  modelSelect.appendChild(option);
}

function addInstalledModelsToCatalog() {
  installedModels.forEach((name) => {
    const { baseName, tag } = splitModelReference(name);
    const existingModel = catalogModels.find((model) => model.name === baseName);
    if (existingModel) {
      const sizes = Array.isArray(existingModel.sizes) ? existingModel.sizes : [];
      existingModel.sizes = uniqueValues([...sizes, tag]);
      return;
    }

    catalogModels.push({
      name: baseName,
      description: 'Installed local Ollama model.',
      updated: 'local',
      capabilities: [],
      sizes: tag && tag.toLowerCase() !== 'latest' ? [tag] : [],
    });
  });
}

function renderModelOptions(preferredModel = currentModel) {
  modelsMap = {};
  modelSelect.replaceChildren();

  const filteredModels = catalogModels
    .filter((model) => model && model.name && modelMatchesType(model, currentModelType))
    .sort(compareModelsByRecency);

  filteredModels.forEach((model) => {
    if (modelsMap[model.name]) {
      return;
    }

    modelsMap[model.name] = model;
    addModelOption(model);
  });

  if (modelsMap[preferredModel]) {
    currentModel = preferredModel;
    modelSelect.value = currentModel;
  } else if (modelSelect.options.length > 0) {
    currentModel = modelSelect.options[0].value;
    modelSelect.value = currentModel;
  } else {
    currentModel = '';
  }

  populateSizeSelect(currentModel);
  setModelDescription(currentModel);
  updateSelectedModelControls();
}

async function fetchModels() {
  try {
    await fetchInstalledModels();

    const models = await fetchModelCatalog();
    catalogModels = Array.isArray(models) ? models.filter((model) => model && model.name) : [];
    addInstalledModelsToCatalog();
    renderModelOptions();
  } catch (error) {
    appendStatus(`Unable to load model catalog: ${error.message}`);
    modelTypeSelect.disabled = true;
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
loadProjectButton.addEventListener('click', loadProjectSummary);
projectContextButton.addEventListener('click', addProjectGuardrails);
projectSearchButton.addEventListener('click', searchProject);
projectReadButton.addEventListener('click', readProjectFile);
projectRunButton.addEventListener('click', runProjectTool);
projectClearButton.addEventListener('click', clearProjectContext);
modelTypeSelect.addEventListener('change', () => {
  currentModelType = modelTypeSelect.value;
  currentSize = '';
  renderModelOptions(currentModel);
});
modelSelect.addEventListener('change', () => {
  currentModel = modelSelect.value;
  currentSize = '';
  populateSizeSelect(currentModel);
  setModelDescription(currentModel);
  updateSelectedModelControls();
});
sizeSelect.addEventListener('change', () => {
  currentSize = sizeSelect.value;
  setModelDescription(currentModel);
  updateSelectedModelControls();
});
window.addEventListener('DOMContentLoaded', () => {
  populateModelTypeSelect();
  loadProjectDefaults();
  fetchModels();
});
