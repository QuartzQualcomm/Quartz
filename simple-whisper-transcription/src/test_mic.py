import time
import numpy as np
import sounddevice as sd

# Adjust SAMPLE_RATE if your built-in mic uses a different rate (e.g., 44100)
SAMPLE_RATE = 16000  
DURATION = 10  # seconds to test

def audio_callback(indata, frames, time_info, status):
    if status:
        print("Status:", status)
    # Compute and print RMS value for the current audio chunk.
    rms = np.sqrt(np.mean(indata**2))
    print("RMS:", rms)

if __name__ == "__main__":
    print("Starting microphone test for {} seconds...".format(DURATION))
    with sd.InputStream(samplerate=SAMPLE_RATE, channels=1, callback=audio_callback):
        time.sleep(DURATION)
    print("Microphone test finished.")