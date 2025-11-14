# Multilingual Speech Correction & TTS Demo

Single Page Web Application + FastAPI backend:

- Records microphone audio in the browser (desktop & mobile)
- Sends audio + email to a REST API
- Backend:
  - Speech-to-Text (STT) with **Whisper**
  - Grammar correction with **LanguageTool** (English + German only)
  - Text-to-Speech (TTS) with **Piper** (English, German, Turkish)
- Returns corrected (or original) text as speech back to the frontend

> ⚠️ This is a **local demo** project – everything runs on your machine (no external paid APIs).

---

## ✨ Features

### Frontend (Vite + TypeScript)

- Record audio using `MediaRecorder` and `getUserMedia`
- Email input + buttons:
  - Start recording
  - Stop recording
  - Send to backend
- Playback:
  - Original audio
  - Processed audio from backend
- Displays corrected text (if ASCII and available)

### Backend (FastAPI, Python)

- Endpoint: `POST /api/upload`
- Receives:
  - `email` (string, form field)
  - `audio` (file, webm)
- Pipeline:
  1. **Whisper** → STT (audio → text + detected language)
  2. Language & grammar logic:
     - `en` → grammar correction via LanguageTool + TTS (Piper EN)
     - `de` → grammar correction via LanguageTool + TTS (Piper DE)
     - `tr` → no grammar correction, but TTS (Piper TR)
     - other languages → no TTS, returns text only as JSON
  3. Returns:
     - For EN/DE/TR: WAV audio (`audio/wav`)
     - For other languages: JSON with text only

---

## 🧰 Tech Stack

- **Frontend**
  - Vite
  - TypeScript
  - Vanilla DOM + `MediaRecorder` API

- **Backend**
  - Python 3.10+ (recommended)
  - FastAPI
  - Uvicorn
  - Whisper
  - LanguageTool (via `language_tool_python`)
  - Piper TTS
  - ffmpeg
  - Java (for LanguageTool local server)

---

## 📁 Project Structure (example)

```text
project-root/
  backend/
    main.py
    models/
      en_US-kristin-medium.onnx
      en_US-kristin-medium.onnx.json
      de_DE-thorsten-medium.onnx
      de_DE-thorsten-medium.onnx.json
      tr_TR-fettah-medium.onnx
      tr_TR-fettah-medium.onnx.json
    .venv/
    requirements.txt   (optional)
  frontend/
    index.html
    vite.config.ts
    package.json
    tsconfig.json
    src/
      main.ts
