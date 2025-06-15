#!/usr/bin/env python3
"""
Simple audio transcription using Whisper with 5-second chunking.
"""

import subprocess
import tempfile
import os
from pathlib import Path
import yaml


def _load_config():
    """Load config from config.yaml, with fallback defaults."""
    try:
        with open("config.yaml", 'r') as f:
            config = yaml.safe_load(f)
            return config.get("audio", {}).get("transcription", {})
    except:
        return {"model": "base", "chunk_duration": 5.0}


def transcribe_audio(audio_path: str, model: str = None) -> str:
    """
    Transcribe audio file using Whisper with smart chunking.
    
    Args:
        audio_path: Path to audio file
        model: Whisper model size (if None, uses config.yaml)
        
    Returns:
        SRT content as string
    """
    # Load config and use model from config if not specified
    config = _load_config()
    if model is None:
        model = config.get("model", "tiny")  # tiny is much faster
    
    # Validate input
    if not os.path.exists(audio_path):
        raise FileNotFoundError(f"Audio file not found: {audio_path}")
    
    # Get audio duration first
    try:
        result = subprocess.run([
            "ffprobe", "-i", audio_path, "-show_entries", "format=duration", 
            "-v", "quiet", "-of", "csv=p=0"
        ], capture_output=True, text=True, check=True)
        duration = float(result.stdout.strip())
    except:
        duration = 999  # Fallback to chunking if can't get duration
    
    # If audio is short (< 30s), process directly without chunking
    if duration < 30:
        print(f"Processing short audio ({duration:.1f}s) directly...")
        with tempfile.TemporaryDirectory() as temp_dir:
            subprocess.run([
                "whisper", audio_path,
                "--model", model,
                "--output_format", "srt",
                "--output_dir", temp_dir
            ], capture_output=True, check=True)
            
            srt_file = next(Path(temp_dir).glob("*.srt"))
            return srt_file.read_text(encoding='utf-8')
    
    # For longer audio, use 30-second chunks (much fewer chunks)
    chunk_duration = 30.0
    print(f"Processing long audio ({duration:.1f}s) in {chunk_duration}s chunks...")
    
    with tempfile.TemporaryDirectory() as temp_dir:
        # Split audio with ffmpeg
        chunk_pattern = os.path.join(temp_dir, "chunk_%03d.wav")
        subprocess.run([
            "ffmpeg", "-i", audio_path,
            "-f", "segment", "-segment_time", str(chunk_duration),
            "-c", "copy", chunk_pattern, "-y"
        ], capture_output=True, check=True)
        
        # Get chunk files
        chunks = sorted(Path(temp_dir).glob("chunk_*.wav"))
        print(f"Processing {len(chunks)} chunks with model: {model}")
        
        # Process chunks sequentially but with minimal overhead
        all_srt = []
        for i, chunk in enumerate(chunks):
            print(f"  Chunk {i+1}/{len(chunks)}")
            
            with tempfile.TemporaryDirectory() as whisper_temp:
                subprocess.run([
                    "whisper", str(chunk),
                    "--model", model,
                    "--output_format", "srt",
                    "--output_dir", whisper_temp
                ], capture_output=True, check=True)
                
                srt_file = next(Path(whisper_temp).glob("*.srt"))
                srt_content = srt_file.read_text(encoding='utf-8')
                
                # Adjust timestamps
                adjusted_srt = _adjust_srt_timing(srt_content, i * chunk_duration)
                all_srt.append(adjusted_srt)
        
        return _combine_srt_chunks(all_srt)


def _adjust_srt_timing(srt_content: str, offset_seconds: float) -> str:
    """Add time offset to all timestamps in SRT content."""
    import re
    
    def adjust_time(match):
        time_str = match.group(0)
        h, m, s_ms = time_str.split(':')
        s, ms = s_ms.split(',')
        
        total_seconds = int(h) * 3600 + int(m) * 60 + int(s) + int(ms) / 1000.0
        total_seconds += offset_seconds
        
        hours = int(total_seconds // 3600)
        minutes = int((total_seconds % 3600) // 60)
        seconds = int(total_seconds % 60)
        milliseconds = int((total_seconds % 1) * 1000)
        
        return f"{hours:02d}:{minutes:02d}:{seconds:02d},{milliseconds:03d}"
    
    return re.sub(r'\d{2}:\d{2}:\d{2},\d{3}', adjust_time, srt_content)


def _combine_srt_chunks(srt_chunks: list) -> str:
    """Combine SRT chunks into single file with sequential numbering."""
    combined = ""
    counter = 1
    
    for srt in srt_chunks:
        lines = srt.strip().split('\n')
        i = 0
        while i < len(lines):
            if lines[i].strip().isdigit():
                combined += f"{counter}\n"
                counter += 1
                i += 1
                # Copy timing and text
                while i < len(lines) and lines[i].strip():
                    combined += lines[i] + "\n"
                    i += 1
                combined += "\n"
            else:
                i += 1
    
    return combined


if __name__ == "__main__":
    import sys
    
    if len(sys.argv) < 2:
        print("Usage: python audio.py <audio_file> [model]")
        print("Example: python audio.py audio.wav")
        print("Example: python audio.py audio.wav large")
        sys.exit(1)
    
    audio_file = sys.argv[1]
    
    # Only use second argument if it looks like a valid model name
    valid_models = ["tiny", "base", "small", "medium", "large"]
    model = None
    if len(sys.argv) > 2 and sys.argv[2] in valid_models:
        model = sys.argv[2]
    
    try:
        srt = transcribe_audio(audio_file, model)
        print("\n" + "="*50)
        print("TRANSCRIPTION RESULT:")
        print("="*50)
        print(srt)
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)
