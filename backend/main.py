# main.py

import os
from typing import Optional

# JAVA settings (your JDK path)
os.environ["JAVA_HOME"] = r"C:\Program Files\Eclipse Adoptium\jdk-17.0.17.10-hotspot"
os.environ["PATH"] = os.environ["JAVA_HOME"] + r"\bin;" + os.environ.get("PATH", "")

from fastapi import FastAPI, UploadFile, File, Form
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response, JSONResponse

import tempfile
import io
import wave

import whisper
import language_tool_python
from piper import PiperVoice

# ==========================
#  CONFIG
# ==========================

WHISPER_MODEL_NAME = "small"  # tiny/base/small/medium/large

# Piper models for EN + DE + TR
PIPER_MODELS = {
    "en": "models/en_US-kristin-medium.onnx",     # English TTS model
    "de": "models/de_DE-thorsten-medium.onnx",    # German TTS model
    "tr": "models/tr_TR-fettah-medium.onnx",      # Turkish TTS model (TTS only)
}

DEFAULT_LANG = "en"  # fallback language if detection fails

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

print("Loading Whisper model...")
whisper_model = whisper.load_model(WHISPER_MODEL_NAME)
print("Whisper model loaded.")

print("Starting LanguageTool locally (EN + DE)...")
lt_tool_en = language_tool_python.LanguageTool("en-US")
lt_tool_de = language_tool_python.LanguageTool("de-DE")
print("LanguageTool ready (EN + DE).")

# Cache for Piper voices
piper_voices: dict[str, PiperVoice] = {}


# ==========================
#  HELPER FUNCTIONS
# ==========================

def stt_with_whisper(audio_bytes: bytes) -> tuple[str, str]:
    """
    Convert audio bytes (webm) → temp file → Whisper → (text, language)
    """
    with tempfile.NamedTemporaryFile(suffix=".webm", delete=False) as tmp:
        tmp.write(audio_bytes)
        tmp_path = tmp.name

    result = whisper_model.transcribe(tmp_path)
    text = result.get("text", "").strip()
    detected_lang = result.get("language", "en")
    print(f"Whisper text output: {text}")
    print(f"Whisper detected language (raw): {detected_lang}")
    return text, detected_lang


def detect_lang_for_tts(detected: str) -> Optional[str]:
    """
    Map Whisper languages (en, de, tr, pt, hy, etc.)
    to supported TTS languages:
      - en → "en"
      - de → "de"
      - tr → "tr"
      - others → None (no TTS, return text only)
    """
    if not detected:
        return DEFAULT_LANG
    d = detected.lower()
    if d.startswith("en"):
        return "en"
    if d.startswith("de"):
        return "de"
    if d.startswith("tr"):
        return "tr"
    # pt, hy, ru, ar, etc → unsupported for TTS
    return None


def correct_grammar(text: str, lang_key: Optional[str]) -> str:
    """
    Grammar correction for EN/DE.
    TR and other languages return text unchanged.
    """
    if lang_key == "en":
        matches = lt_tool_en.check(text)
        corrected = language_tool_python.utils.correct(text, matches)
        print(f"Corrected text (en): {corrected}")
        return corrected
    elif lang_key == "de":
        matches = lt_tool_de.check(text)
        corrected = language_tool_python.utils.correct(text, matches)
        print(f"Corrected text (de): {corrected}")
        return corrected

    # TR or unsupported languages → no correction
    print(f"Skipping grammar correction (lang={lang_key}), returning text unchanged.")
    return text


def get_piper_voice(lang_key: str) -> PiperVoice:
    """
    Return PiperVoice instance for EN/DE/TR (cached).
    """
    if lang_key not in PIPER_MODELS:
        lang_key = DEFAULT_LANG

    if lang_key in piper_voices:
        return piper_voices[lang_key]

    model_path = PIPER_MODELS[lang_key]
    print(f"Loading Piper model ({lang_key}): {model_path}")
    voice = PiperVoice.load(model_path)
    piper_voices[lang_key] = voice
    print(f"Piper model loaded ({lang_key}).")
    return voice


def tts_with_piper(text: str, lang_key: str) -> bytes:
    """
    Convert text to WAV audio using Piper.
    """
    voice = get_piper_voice(lang_key)

    buffer = io.BytesIO()
    with wave.open(buffer, "wb") as wav_file:
        wav_file.setnchannels(1)
        wav_file.setsampwidth(2)
        wav_file.setframerate(22050)
        voice.synthesize_wav(text, wav_file)

    buffer.seek(0)
    wav_bytes = buffer.read()
    print(f"Piper WAV generated ({lang_key}). Byte length: {len(wav_bytes)}")
    return wav_bytes


# ==========================
#  ENDPOINT
# ==========================

@app.post("/api/upload")
async def upload_audio(
    email: str = Form(...),
    audio: UploadFile = File(...),
):
    """
    Pipeline:
      1) Audio → Whisper STT → text + detected_lang_raw
      2) detected_lang_raw → tts_lang (en/de/tr or None)
      3) Grammar correction for EN/DE only
      4) Piper TTS for EN/DE/TR
      5) If no TTS available → return only JSON text (no audio)
    """
    try:
        print("Received email:", email)
        print("File name:", audio.filename)
        print("Content-Type:", audio.content_type)

        audio_bytes = await audio.read()
        print("Byte size:", len(audio_bytes))

        # 1) STT
        original_text, detected_lang_raw = stt_with_whisper(audio_bytes)
        tts_lang = detect_lang_for_tts(detected_lang_raw)
        print(f"Language used for TTS (tts_lang): {tts_lang}")

        # 2) If language unsupported → return text only
        if tts_lang is None:
            print("No TTS/grammar model for this language. Returning text only.")
            return JSONResponse(
                status_code=200,
                content={
                    "original_text": original_text,
                    "detected_lang_raw": detected_lang_raw,
                    "normalized_lang": None,
                    "tts_available": False,
                },
            )

        # 3) Grammar correction (EN/DE only)
        corrected_text = correct_grammar(original_text, tts_lang)

        # 4) TTS
        corrected_wav = tts_with_piper(corrected_text, tts_lang)

        # ASCII-only headers (avoid Unicode header crash)
        headers = {
            "X-Detected-Lang": tts_lang,
        }
        if corrected_text.isascii():
            headers["X-Corrected-Text"] = corrected_text
        else:
            print("Warning: corrected_text contains non-ASCII characters, skipping header.")

        return Response(
            content=corrected_wav,
            media_type="audio/wav",
            headers=headers,
        )

    except Exception as e:
        print("Error:", repr(e))
        return JSONResponse(
            status_code=500,
            content={"error": str(e)},
        )
