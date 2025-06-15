import fastapi
import numpy as np
import os
import sys
import time
import uvicorn
import yaml
import ffmpeg
import base64
import tempfile

from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from pydantic import BaseModel

from model import WhisperBaseEnONNX
from qai_hub_models.models.whisper_base_en import App as WhisperApp

# ------------------------------------------------------------------
# Globals
# ------------------------------------------------------------------

# Will be loaded with the model on startup
MODEL: WhisperApp | None = None
# Will be loaded with the config on startup
CONFIG: dict = {}
# Sample rate the model expects
SAMPLE_RATE = 16000

app = FastAPI()

# ------------------------------------------------------------------
# Pydantic Models for OpenAI compatibility
# ------------------------------------------------------------------

class TranscriptionResponse(BaseModel):
    text: str

class AudioDataRequest(BaseModel):
    audioData: str

class ClientTranscriptionResponse(BaseModel):
    data: str

# ------------------------------------------------------------------
# Lifespan events
# ------------------------------------------------------------------

@app.on_event("startup")
def load_on_startup():
    """Load the model and config when the server starts."""
    global MODEL, CONFIG, SAMPLE_RATE

    # Load config from YAML
    try:
        with open("config.yaml", "r") as f:
            CONFIG = yaml.safe_load(f)
    except FileNotFoundError:
        sys.exit("Could not find config.yaml. Please create it based on the README.")

    # Get model and audio settings from config
    encoder_path = CONFIG.get("encoder_path", "models/WhisperEncoder.onnx")
    decoder_path = CONFIG.get("decoder_path", "models/WhisperDecoder.onnx")
    SAMPLE_RATE = CONFIG.get("sample_rate", 16000)

    # Check that model files exist
    if not os.path.exists(encoder_path) or not os.path.exists(decoder_path):
        sys.exit(f"Model files not found. Searched for encoder at '{encoder_path}' and decoder at '{decoder_path}'. Please follow README to download models.")
    
    # Load the Whisper model
    print("Loading Whisper model...")
    MODEL = WhisperApp(WhisperBaseEnONNX(encoder_path, decoder_path))
    print("Model loaded successfully.")

# ------------------------------------------------------------------
# API Endpoints
# ------------------------------------------------------------------

@app.post("/api/transcribe", response_model=ClientTranscriptionResponse)
async def transcribeAudio(request: AudioDataRequest):
    """
    Endpoint to handle audio transcription requests from the client.
    """
    print("Received audio data for transcription")
    
    # Clean and validate base64 audio data
    print("Cleaning and decoding base64 audio data...")
    audio_data = request.audioData
    
    if audio_data.startswith('data:'):
        audio_data = audio_data.split(',', 1)[1]
    
    audio_data = audio_data.strip()
    
    missing_padding = len(audio_data) % 4
    if missing_padding:
        audio_data += '=' * (4 - missing_padding)
    
    try:
        audio_bytes = base64.b64decode(audio_data)
    except Exception as decode_error:
        print(f"Base64 decode error: {decode_error}")
        raise HTTPException(status_code=400, detail=f"Invalid base64 audio data: {str(decode_error)}")
    
    if not audio_bytes:
        raise HTTPException(status_code=400, detail="No audio data received after decoding")

    try:
        # Use ffmpeg to convert the audio to 16kHz mono PCM s16le format
        out, _ = (
            ffmpeg
            .input("pipe:0")
            .output("pipe:1", format="s16le", ac=1, ar=SAMPLE_RATE)
            .run(input=audio_bytes, capture_stdout=True, capture_stderr=True)
        )
    except ffmpeg.Error as e:
        print(f"FFmpeg error occurred: {e.stderr.decode()}")
        raise HTTPException(status_code=500, detail=f"FFmpeg conversion failed: {e.stderr.decode()}")

    # Convert the raw PCM data to a float32 numpy array
    audio_np = np.frombuffer(out, np.int16).astype(np.float32) / 32768.0

    # Transcribe the audio
    print("Transcribing audio...")
    start_time = time.time()
    transcript = MODEL.transcribe(audio_np, SAMPLE_RATE)
    end_time = time.time()
    
    print(f"Transcription complete in {end_time - start_time:.2f}s: \"{transcript}\"")

    return {"data": transcript}

@app.post("/v1/audio/transcriptions", response_model=TranscriptionResponse)
async def create_transcription(
    file: UploadFile = File(...),
    model: str = Form("whisper-1")  # Ignored, but here for OpenAI compatibility
):
    """
    Transcribes an audio file.
    """
    if MODEL is None:
        raise HTTPException(status_code=503, detail="Model is not loaded yet. Please wait a moment and try again.")
    
    # Read the uploaded file into memory
    audio_bytes = await file.read()

    # Use ffmpeg to convert the audio to 16kHz mono PCM s16le format
    try:
        out, _ = (
            ffmpeg
            .input("pipe:0")
            .output("pipe:1", format="s16le", ac=1, ar=SAMPLE_RATE)
            .run(input=audio_bytes, capture_stdout=True, capture_stderr=True)
        )
    except ffmpeg.Error as e:
        raise HTTPException(status_code=500, detail=f"FFmpeg error: {e.stderr.decode()}")
    
    # Convert the raw PCM data to a float32 numpy array
    audio_np = np.frombuffer(out, np.int16).astype(np.float32) / 32768.0

    # Transcribe the audio
    start_time = time.time()
    transcript = MODEL.transcribe(audio_np, SAMPLE_RATE)
    end_time = time.time()
    
    print(f"Transcription complete in {end_time - start_time:.2f}s: \"{transcript}\"")

    return {"text": transcript}

# ------------------------------------------------------------------
# Main
# ------------------------------------------------------------------

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8001) 