import numpy as np
import os
import queue
import sounddevice as sd
import sys
import threading
import time
import tkinter as tk
import yaml

from tkinter import scrolledtext
from model import WhisperBaseEnONNX
from qai_hub_models.models.whisper_base_en import App as WhisperApp

class GuiTranscriber:
    def __init__(self, root):
        self.root = root
        self.root.title("Whisper Transcription")

        with open("config.yaml", "r") as f:
            config = yaml.safe_load(f)
        
        # audio settings
        self.sample_rate = config.get("sample_rate", 16000)
        self.channels = config.get("channels", 1)
        self.chunk_duration = config.get("chunk_duration", 4)  # seconds
        self.chunk_samples = int(self.sample_rate * self.chunk_duration)

        # processing settings
        self.silence_threshold = config.get("silence_threshold", 0.001)
        self.queue_timeout = config.get("queue_timeout", 1.0)

        # model paths
        self.encoder_path = config.get("encoder_path", "models/WhisperEncoder.onnx")
        self.decoder_path = config.get("decoder_path", "models/WhisperDecoder.onnx")

        # check that the model paths exist
        if not os.path.exists(self.encoder_path):
            sys.exit(f"Encoder model not found at {self.encoder_path}.")
        if not os.path.exists(self.decoder_path):
            sys.exit(f"Decoder model not found at {self.decoder_path}.")

        # GUI widgets -----------------------------------------------------
        self.status_label = tk.Label(self.root, text="Loading model...", anchor="w")
        self.status_label.pack(fill="x", padx=10, pady=5)

        self.transcription_display = scrolledtext.ScrolledText(
            self.root, wrap=tk.WORD, state="disabled", height=15
        )
        self.transcription_display.pack(padx=10, pady=10, fill="both", expand=True)

        self.button_frame = tk.Frame(self.root)
        self.button_frame.pack(pady=5)

        self.start_button = tk.Button(
            self.button_frame, text="Start Recording", command=self.start_recording, state="disabled"
        )
        self.start_button.pack(side="left", padx=5)

        self.stop_button = tk.Button(
            self.button_frame, text="Stop Recording", command=self.stop_recording, state="disabled"
        )
        self.stop_button.pack(side="left", padx=5)

        self.inference_time_label = tk.Label(self.root, text="Inference time: N/A", anchor="w")
        self.inference_time_label.pack(fill="x", padx=10, pady=5)

        # Initialize runtime variables -----------------------------------
        self.audio_queue: queue.Queue[np.ndarray] | None = None
        self.stop_event: threading.Event | None = None
        self.process_thread: threading.Thread | None = None
        self.stream: sd.InputStream | None = None

        # load model asynchronously so GUI loads fast --------------------
        self.model: WhisperApp | None = None
        self.model_loading_thread = threading.Thread(target=self._load_model, daemon=True)
        self.model_loading_thread.start()

    def _load_model(self):
        """Load the model in a background thread."""
        try:
            self.model = WhisperApp(WhisperBaseEnONNX(self.encoder_path, self.decoder_path))
            self._update_status("Model loaded. Ready to record.")
            self.root.after(0, lambda: self.start_button.config(state="normal"))
        except Exception as exc:
            self._update_status(f"Failed to load model: {exc}")

    # ------------------------------------------------------------------
    # Audio callbacks & worker threads
    # ------------------------------------------------------------------

    def _audio_callback(self, indata, frames, time_info, status):
        if status:
            print(f"Status: {status}")
        if self.stop_event is None or self.stop_event.is_set():
            return
        # Flatten to 1-D float32 array (mono)
        chunk = indata.copy().flatten()
        self.audio_queue.put(chunk)

    def _process_audio(self):
        """Continuously process audio from the queue and transcribe."""
        buffer = np.empty((0,), dtype=np.float32)
        while not self.stop_event.is_set():
            try:
                chunk = self.audio_queue.get(timeout=self.queue_timeout)
                buffer = np.concatenate([buffer, chunk])

                while len(buffer) >= self.chunk_samples:
                    current_chunk = buffer[: self.chunk_samples]
                    buffer = buffer[self.chunk_samples :]

                    # Skip silent chunks to save compute
                    if np.abs(current_chunk).mean() <= self.silence_threshold:
                        continue

                    start = time.time()
                    try:
                        transcript = self.model.transcribe(current_chunk, self.sample_rate)
                    except Exception as exc:
                        self.root.after(0, self._update_status, f"Transcription error: {exc}")
                        continue

                    end = time.time()
                    if transcript.strip():
                        self.root.after(0, self._append_transcription, transcript, end - start)

            except queue.Empty:
                continue

    # ------------------------------------------------------------------
    # GUI update helpers (must be called from main thread)
    # ------------------------------------------------------------------

    def _append_transcription(self, transcript: str, inference_time: float):
        self.transcription_display.config(state="normal")
        self.transcription_display.insert(tk.END, transcript + "\n\n")
        self.transcription_display.see(tk.END)
        self.transcription_display.config(state="disabled")
        self.inference_time_label.config(text=f"Inference time (last chunk): {inference_time:.2f} s")

    def _update_status(self, text: str):
        self.status_label.config(text=text)

    # ------------------------------------------------------------------
    # Public GUI callbacks
    # ------------------------------------------------------------------

    def start_recording(self):
        if self.model is None:
            self._update_status("Model is still loading. Please wait…")
            return

        # Prepare runtime variables
        self.audio_queue = queue.Queue()
        self.stop_event = threading.Event()

        # Start processing thread
        self.process_thread = threading.Thread(target=self._process_audio, daemon=True)
        self.process_thread.start()

        # Start audio stream
        self.stream = sd.InputStream(
            samplerate=self.sample_rate,
            channels=self.channels,
            callback=self._audio_callback,
        )
        self.stream.start()

        # Update GUI state
        self.start_button.config(state="disabled")
        self.stop_button.config(state="normal")
        self._update_status("Recording…")

    def stop_recording(self):
        # Guard: nothing to stop
        if self.stop_event is None or self.stop_event.is_set():
            return

        self._update_status("Stopping…")

        # Signal threads to stop
        self.stop_event.set()

        # Stop audio stream
        if self.stream is not None:
            self.stream.stop()
            self.stream.close()
            self.stream = None

        # Wait for processing thread to finish remaining work
        if self.process_thread is not None:
            self.process_thread.join()
            self.process_thread = None

        # Reset buttons
        self.start_button.config(state="normal")
        self.stop_button.config(state="disabled")
        self._update_status("Ready to record.")

    # ------------------------------------------------------------------
    # Legacy methods (kept for external callers, now do nothing)
    # ------------------------------------------------------------------

    def transcribe_audio(self, *_args, **_kwargs):
        """Deprecated: kept for backward compatibility."""
        pass

    def update_gui_with_transcription(self, *_args, **_kwargs):
        pass

    def update_gui_with_error(self, *_args, **_kwargs):
        pass

def main():
    root = tk.Tk()
    app = GuiTranscriber(root)
    root.mainloop()

if __name__ == "__main__":
    main() 