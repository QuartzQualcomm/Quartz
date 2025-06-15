import os
import tempfile
import subprocess
from pathlib import Path
import numpy as np
import soundfile as sf
from scipy import signal as scipy_signal

def process_media_file(file_path: str, process_func, *args, **kwargs):
    """
    Generic function to process media files (audio or video).
    Handles extraction of audio from video if needed.
    
    Args:
        file_path: Path to the input file
        process_func: Function to process the audio
        *args, **kwargs: Additional arguments for process_func
    
    Returns:
        Result from process_func
    """
    try:
        file_path = Path(file_path)
        if not file_path.exists():
            raise FileNotFoundError(f"File not found: {file_path}")
        
        # Determine if input is video
        if file_path.suffix.lower() in ['.mp4', '.mov', '.mkv', '.avi']:
            # Extract audio to temporary WAV
            with tempfile.TemporaryDirectory() as temp_dir:
                wav_path = Path(temp_dir) / "extracted_audio.wav"
                subprocess.run([
                    'ffmpeg', '-i', str(file_path), '-vn', '-acodec', 'pcm_s16le',
                    '-ar', '44100', '-ac', '2', str(wav_path), '-y'
                ], capture_output=True, check=True)
                
                # Process the audio
                result = process_func(str(wav_path), *args, **kwargs)
                
                # If processing was successful and we have a processed audio file
                if result.get("success") and "audio_path" in result.get("data", {}):
                    processed_audio = result["data"]["audio_path"]
                    
                    # Create output filename
                    output_filename = f"processed_{file_path.stem}{file_path.suffix}"
                    output_path = Path("assets/public") / output_filename
                    output_path.parent.mkdir(parents=True, exist_ok=True)
                    
                    # Combine processed audio with original video
                    subprocess.run([
                        'ffmpeg', '-i', str(file_path), '-i', processed_audio,
                        '-c:v', 'copy', '-map', '0:v:0', '-map', '1:a:0',
                        '-shortest', str(output_path), '-y'
                    ], capture_output=True, check=True)
                    
                    # Update result with video path
                    result["data"]["video_path"] = str(output_path)
                    result["data"]["link"] = f"/api/assets/public/{output_filename}"
                    result["data"]["absolute_path"] = str(output_path.resolve())
                
                return result
        else:
            # Input is audio file, process directly
            return process_func(str(file_path), *args, **kwargs)
            
    except Exception as e:
        return {"success": False, "error": f"Media processing failed: {str(e)}"}

def remove_noise(audio_path: str) -> str:
    """
    Remove background noise from audio file using a simple noise gate and low-pass filter.
    
    Args:
        audio_path: Path to the input audio file
        
    Returns:
        Path to the processed audio file
    """
    try:
        # Read the audio file
        audio_data, sample_rate = sf.read(audio_path)
        
        # Convert to mono if stereo
        if len(audio_data.shape) > 1:
            audio_data = np.mean(audio_data, axis=1)
        
        # Apply noise gate (-40dB threshold)
        threshold = 0.01  # -40dB
        audio_data = np.where(np.abs(audio_data) < threshold, 0, audio_data)
        
        # Apply low-pass filter (4kHz cutoff)
        nyquist = sample_rate / 2
        cutoff = 4000 / nyquist
        b, a = scipy_signal.butter(4, cutoff, btype='low')
        audio_data = scipy_signal.filtfilt(b, a, audio_data)
        
        # Create output filename
        input_path = Path(audio_path)
        output_filename = f"denoised_{input_path.stem}.wav"
        output_path = Path("assets/public") / output_filename
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Save the processed audio
        sf.write(str(output_path), audio_data, sample_rate)
        
        return str(output_path)
        
    except Exception as e:
        raise Exception(f"Noise removal failed: {str(e)}") 