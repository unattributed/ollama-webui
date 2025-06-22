// ~/workspace/ollama-webui/script.js

document.addEventListener("DOMContentLoaded", () => {
  const dropZone = document.getElementById("drop-zone");
  const fileInput = document.getElementById("file-input");
  const fileList = document.getElementById("file-list");
  const statusBox = document.getElementById("upload-status");
  const chatOutput = document.getElementById("chat-output");
  const sendBtn = document.getElementById("send-btn");
  const promptBox = document.getElementById("user-prompt");
  const sessionList = document.getElementById("session-list");
  const newSessionBtn = document.getElementById("new-session");

  let sessionId = localStorage.getItem("session_id") || null;

  function updateSession(id) {
    sessionId = id;
    localStorage.setItem("session_id", id);
    loadSessions(); // refresh sidebar
    chatOutput.innerHTML = `<div class="llm-msg">🧾 New session started: ${id}</div>`;
  }

  function loadSessions() {
    fetch("/sessions")
      .then((res) => res.json())
      .then((sessions) => {
        sessionList.innerHTML = "";
        sessions
          .sort((a, b) => b.timestamp - a.timestamp)
          .forEach((s) => {
            const li = document.createElement("li");
            li.textContent = s.title;
            li.className = s.id === sessionId ? "active" : "";
            li.addEventListener("click", () => {
              updateSession(s.id);
            });
            sessionList.appendChild(li);
          });
      });
  }

  newSessionBtn.addEventListener("click", () => {
    sessionId = null;
    localStorage.removeItem("session_id");
    chatOutput.innerHTML = "";
  });

  // File drag/drop logic
  dropZone.addEventListener("dragover", (e) => {
    e.preventDefault();
    dropZone.classList.add("dragover");
  });

  dropZone.addEventListener("dragleave", () => {
    dropZone.classList.remove("dragover");
  });

  dropZone.addEventListener("drop", (e) => {
    e.preventDefault();
    dropZone.classList.remove("dragover");
    handleFiles(e.dataTransfer.files);
  });

  dropZone.addEventListener("click", () => {
    fileInput.click();
  });

  fileInput.addEventListener("change", () => {
    handleFiles(fileInput.files);
  });

  function handleFiles(files) {
    fileList.innerHTML = "";
    const formData = new FormData();
    let valid = false;

    Array.from(files).forEach((file) => {
      if (!/\.(txt|pdf|zip|md)$/i.test(file.name)) {
        const li = document.createElement("li");
        li.textContent = `❌ Skipped: ${file.name}`;
        li.style.color = "red";
        fileList.appendChild(li);
        return;
      }

      formData.append("files", file);
      const li = document.createElement("li");
      li.textContent = `✅ Queued: ${file.name}`;
      fileList.appendChild(li);
      valid = true;
    });

    if (sessionId) {
      formData.append("session_id", sessionId);
    }

    if (valid) uploadFiles(formData);
  }

  async function uploadFiles(formData) {
    statusBox.classList.remove("hidden");
    statusBox.textContent = "Uploading...";

    try {
      const res = await fetch("/upload", {
        method: "POST",
        body: formData,
      });

      const result = await res.json();
      statusBox.textContent = result.message || "Upload complete";
      if (result.session_id) updateSession(result.session_id);
    } catch (err) {
      statusBox.textContent = "Upload failed. Check server logs.";
      console.error(err);
    }

    setTimeout(() => {
      statusBox.classList.add("hidden");
    }, 3000);
  }

  sendBtn.addEventListener("click", async () => {
    const prompt = promptBox.value.trim();
    if (!prompt) return;

    chatOutput.innerHTML += `<div class="user-msg">🧠 You: ${prompt}</div>`;
    promptBox.value = "";

    const body = {
      question: prompt,
    };
    if (sessionId) body.session_id = sessionId;

    try {
      const res = await fetch("/query", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(body),
      });

      const data = await res.json();
      if (data.session_id) updateSession(data.session_id);
      chatOutput.innerHTML += `<div class="llm-msg">🤖 Ollama: ${data.answer}</div>`;
    } catch (e) {
      chatOutput.innerHTML += `<div class="llm-msg">❌ Error contacting LLM.</div>`;
    }

    chatOutput.scrollTop = chatOutput.scrollHeight;
  });

  // Initial load
  loadSessions();
});
