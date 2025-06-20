---
---
# Ollama WebUI

**Ollama WebUI** is a **lightweight**, **manual query interface** that allows users to interact with **pre-trained LLMs** for security data analysis. It provides a simple, **under 1MB** front-end that enables users to upload files for analysis, offering an efficient way to process and analyze security tool outputs.

---

## 📁 File Structure

```plaintext
ollama-webui/
├── favicon.ico               # The favicon for the Web UI
├── index.html                # The main HTML file for the user interface
├── models.json               # Contains model data and metadata used for dropdown and UI functionality
├── script.js                 # JavaScript file for frontend logic and interactions
├── style.css                 # CSS file for styling the user interface
└── scripts/
    ├── deploy_full_ollama_ui.py  # Script to deploy the entire Ollama WebUI setup
    └── pull_model.py             # Script to launch the Ollama model server for processing
```

---

## 🚀 Getting Started

### Requirements:

* **Python 3.9+**
* **Ollama model** (set up as per your local environment)

### Installation:

1. Clone the repository:

   ```bash
   git clone https://github.com/unattributed/ollama-webui.git
   cd ollama-webui
   ```

2. Install the required dependencies:

   ```bash
   pip install -r requirements.txt 
   ```

3. Run the WebUI locally:

   ```bash
   python3 scripts/pull_model.py
   ```

4. Open your browser at [http://127.0.0.1:11435](http://127.0.0.1:11435) to access the interface.

### Running the Backend:

The backend listens on **localhost:11435**. Ensure that the **Ollama model** is set up and accessible from your environment. 

---

## 🔧 Features

* **Lightweight Front-End**: The **Ollama WebUI** is a **lightweight** front-end (less than 1MB) that provides an easy-to-use interface for interacting with pre-trained LLMs.

* **File Uploads for Analysis**: Users can **upload files** (such as text, CSV, or PDF) for analysis, allowing the platform to process and analyze the content.

* **Integration with Ollama LLMs**: The platform can utilize **any Ollama LLM** to analyze the uploaded data, making it versatile for different use cases in cybersecurity and security analysis.

---

## 🤝 Contributing

1. Fork this repository.
2. Create a new branch (`git checkout -b feature-name`).
3. Commit your changes (`git commit -am 'Add new feature'`).
4. Push to your fork (`git push origin feature-name`).
5. Create a pull request.

---

## 📜 License

This project is licensed under the **MIT License** – see the [LICENSE](LICENSE) file for details.

---

