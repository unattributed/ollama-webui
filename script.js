// ~/workspace/ollama-webui/script.js

document.addEventListener("DOMContentLoaded", () => {
  const dropZone = document.getElementById("drop-zone");
  const fileInput = document.getElementById("file-input");
  const fileList = document.getElementById("file-list");
  const statusBox = document.getElementById("upload-status");
  const chatOutput = document.getElementById("chat-output");
  const sendBtn = document.getElementById("send-btn");
  const promptBox = document.getElementById("user-prompt");

  // File drag-drop logic
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
    } catch (err) {
      statusBox.textContent = "Upload failed. Check server logs.";
      console.error(err);
    }

    setTimeout(() => {
      statusBox.classList.add("hidden");
    }, 3000);
  }

  // Chat logic
  sendBtn.addEventListener("click", async () => {
    const prompt = promptBox.value.trim();
    if (!prompt) retu
