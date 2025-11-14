// src/main.ts

interface RecordedAudio {
  blob: Blob;
  url: string;
  mimeType: string;
  createdAt: Date;
}

const BACKEND_URL = "http://localhost:3000/api/upload";

const startBtn = document.getElementById("startBtn") as HTMLButtonElement;
const stopBtn = document.getElementById("stopBtn") as HTMLButtonElement;
const sendBtn = document.getElementById("sendBtn") as HTMLButtonElement;
const player = document.getElementById("player") as HTMLAudioElement;
const correctedPlayer = document.getElementById("correctedPlayer") as HTMLAudioElement;
const emailInput = document.getElementById("emailInput") as HTMLInputElement;
const statusEl = document.getElementById("status") as HTMLParagraphElement;

// If you put <span id="correctedText"></span> in HTML we will fill it from there
const correctedTextSpan = document.getElementById("correctedText") as HTMLSpanElement | null;

let mediaRecorder: MediaRecorder | null = null;
let chunks: BlobPart[] = [];
let currentRecording: RecordedAudio | null = null;

async function startRecording() {
  try {
    const stream = await navigator.mediaDevices.getUserMedia({ audio: true });

    mediaRecorder = new MediaRecorder(stream);
    chunks = [];

    mediaRecorder.ondataavailable = (e) => {
      if (e.data.size > 0) {
        chunks.push(e.data);
      }
    };

    mediaRecorder.onstop = () => {
      const blob = new Blob(chunks, {
        type: mediaRecorder?.mimeType || "audio/webm",
      });
      const url = URL.createObjectURL(blob);

      currentRecording = {
        blob,
        url,
        mimeType: blob.type,
        createdAt: new Date(),
      };

      console.log("Record created:", currentRecording);

      player.src = url;
      sendBtn.disabled = false;
      statusEl.textContent = "Record Ready. You cand send it to backend.";
    };

    mediaRecorder.start();

    startBtn.disabled = true;
    stopBtn.disabled = false;
    sendBtn.disabled = true;

    statusEl.textContent = "Record started...";
  } catch (error) {
    console.error("Microphone could not be accessed:", error);
    alert("You need to allow access to the microphone.");
  }
}

function stopRecording() {
  if (mediaRecorder && mediaRecorder.state === "recording") {
    mediaRecorder.stop();

    startBtn.disabled = false;
    stopBtn.disabled = true;
    statusEl.textContent = "Record Stopped.";
  }
}

async function sendToBackend() {
  if (!currentRecording) {
    alert("You have to make a voice recording first.");
    return;
  }

  const email = emailInput.value.trim();
  if (!email) {
    alert("Please enter your email address.");
    return;
  }

  statusEl.textContent = "Sending to backend...";
  sendBtn.disabled = true;

  try {
    const formData = new FormData();
    formData.append("email", email);
    formData.append("audio", currentRecording.blob, "recording.webm");

    const response = await fetch(BACKEND_URL, {
      method: "POST",
      body: formData,
    });

    if (!response.ok) {
      throw new Error("Backend error returned: " + response.status);
    }

    // Pull corrected text from header
    const correctedTextHeader = response.headers.get("x-corrected-text");
    if (correctedTextHeader) {
      console.log("Corrected text:", correctedTextHeader);
      if (correctedTextSpan) {
        correctedTextSpan.textContent = correctedTextHeader;
      }
    }

    // Pull corrected text from header
    const langHeader = response.headers.get("x-detected-lang");
    if (langHeader) {
      console.log("Perceived language:", langHeader);
    }

    // Body: WAV audio
    const arrayBuffer = await response.arrayBuffer();
    const correctedBlob = new Blob([arrayBuffer], { type: "audio/wav" });
    const correctedUrl = URL.createObjectURL(correctedBlob);

    correctedPlayer.src = correctedUrl;
    statusEl.textContent = "Corrected audio received.";
  } catch (err: any) {
    console.error(err);
    statusEl.textContent = "An error occurred while sending: " + err.message;
  } finally {
    sendBtn.disabled = false;
  }
}


startBtn.addEventListener("click", startRecording);
stopBtn.addEventListener("click", stopRecording);
sendBtn.addEventListener("click", sendToBackend);
