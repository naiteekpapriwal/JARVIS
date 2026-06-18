# 🤖 JARVIS: Your macOS-Native AI Agent

![Jarvis](https://img.shields.io/badge/Status-Active-brightgreen)
![Platform](https://img.shields.io/badge/Platform-macOS-lightgrey)
![LLM](https://img.shields.io/badge/LLM-Gemini-blue)

JARVIS is a truly local, privacy-first AI assistant deeply woven into the macOS ecosystem. Unlike generic cloud-based chatbots, Jarvis has native access to your operating system, acting as an autonomous extension of your machine with local memory and full system context.

---

## 🔥 Exceptional Features

### 👻 Ghost Cursor (GUI Automation)
Jarvis can literally see and control your screen. By taking local screenshots and using on-device OCR, it locates specific text on your screen, physically moves the mouse to click it, types text, and triggers keyboard shortcuts automatically.

### 📱 Digital Life Sync (iMessage)
Jarvis connects directly to your native macOS `chat.db`. By ingesting your recent texts, it builds long-term context, allowing it to remember conversations you've had with friends and colleagues.

### 🔍 Omnipresent System Search
Hooked directly into macOS Spotlight (`mdfind`), Jarvis can instantly search your **entire laptop** (code, PDFs, notes, images) and read the contents to answer questions on the fly. 

### 📅 Native Apple Integrations
Jarvis natively pops open your Apple Calendar to schedule events and manages a local archive of your personal notes, completely bypassing cloud APIs.

### 🎙️ Local Voice Transcription
Utilizing a local instance of OpenAI's Whisper model, Jarvis transcribes your audio commands without ever sending your voice data to the cloud.

### 💻 Safe OS Execution
Jarvis can execute bash commands and control your system directly from the terminal, protected by a safety loop that prompts for your confirmation before running anything dangerous.

---

## 🛠️ Architecture & Tech Stack

* **Core AI:** [Google Gemini](https://deepmind.google/technologies/gemini/)
* **Memory:** [Mem0](https://github.com/mem0ai/mem0) (Local Vector DB via Chroma)
* **Backend:** FastAPI (Python)
* **Frontend:** React + Vite
* **Integrations:** Discord API, macOS Spotlight (`mdfind`), PyAutoGUI, Tesseract OCR, Whisper.

---

## 🚀 Getting Started

### Prerequisites
* macOS (Required for Spotlight, iMessage, and Apple Calendar integrations)
* Python 3.10+
* Node.js & npm

### Installation

1. **Clone the repository:**
   ```bash
   git clone https://github.com/naiteekpapriwal/JARVIS.git
   cd JARVIS
   ```

2. **Backend Setup:**
   ```bash
   python -m venv .venv
   source .venv/bin/activate
   pip install -r requirements.txt
   ```
   *Update `config.yaml` with your preferred models and (optional) API keys.*

3. **Frontend Setup:**
   ```bash
   cd frontend
   npm install
   ```

### Running Jarvis Locally

Start the backend:
```bash
source .venv/bin/activate
python api.py
```

Start the frontend UI:
```bash
cd frontend
npm run dev
```
Visit `http://localhost:5174` (or the port specified in your terminal) in your browser!

---

## 🔒 Privacy First
By default, your memory, vector database, LLM processing, and screen captures stay entirely on your local machine.

---
*Built by [Naiteek Papriwal](https://github.com/naiteekpapriwal).*
