import os
import subprocess
from pathlib import Path
from typing import Tuple, Optional
import tempfile

def extract_audio_from_video(video_path: str) -> Tuple[str, bool]:
    """
    Extract audio from a video file and return the path to the extracted audio file.
    Returns a tuple of (audio_path, is_temp_file).
    If the input is already an audio file, returns (input_path, False).
    """
    # Check if input is already an audio file
    audio_extensions = {'.mp3', '.wav', '.m4a', '.aac', '.ogg', '.flac'}
    if Path(video_path).suffix.lower() in audio_extensions:
        return video_path, False

    # Create a temporary file for the audio
    temp_dir = Path(tempfile.gettempdir())
    audio_path = temp_dir / f"extracted_audio_{Path(video_path).stem}.wav"
    
    try:
        # Use ffmpeg to extract audio
        subprocess.run([
            "ffmpeg", "-i", video_path,
            "-vn",  # No video
            "-acodec", "pcm_s16le",  # PCM 16-bit
            "-ar", "44100",  # 44.1kHz sample rate
            "-ac", "2",  # Stereo
            str(audio_path)
        ], check=True, capture_output=True)
        
        return str(audio_path), True
    except subprocess.CalledProcessError as e:
        raise RuntimeError(f"Failed to extract audio from video: {e.stderr.decode()}")

def combine_audio_with_video(video_path: str, audio_path: str, output_path: Optional[str] = None) -> str:
    """
    Combine audio with video and return the path to the output file.
    If output_path is not provided, creates a new file in the same directory as the video.
    """
    if output_path is None:
        video_path_obj = Path(video_path)
        output_path = str(video_path_obj.parent / f"{video_path_obj.stem}_with_new_audio{video_path_obj.suffix}")
    
    try:
        # Use ffmpeg to combine audio and video
        subprocess.run([
            "ffmpeg",
            "-i", video_path,  # Input video
            "-i", audio_path,  # Input audio
            "-c:v", "copy",    # Copy video stream without re-encoding
            "-c:a", "aac",     # Convert audio to AAC
            "-map", "0:v:0",   # Use video from first input
            "-map", "1:a:0",   # Use audio from second input
            "-shortest",       # End when shortest input ends
            output_path
        ], check=True, capture_output=True)
        
        return output_path
    except subprocess.CalledProcessError as e:
        raise RuntimeError(f"Failed to combine audio with video: {e.stderr.decode()}")

def process_media_file(
    input_path: str,
    process_audio_func,
    *args,
    **kwargs
) -> dict:
    """
    Generic function to process media files (audio or video).
    
    Args:
        input_path: Path to input media file
        process_audio_func: Function that processes audio and returns a dict with results
        *args, **kwargs: Additional arguments to pass to process_audio_func
    
    Returns:
        dict: Results from process_audio_func with additional media handling info
    """
    is_video = Path(input_path).suffix.lower() not in {'.mp3', '.wav', '.m4a', '.aac', '.ogg', '.flac'}
    audio_path = None
    is_temp_audio = False
    
    try:
        # Extract audio if it's a video file
        if is_video:
            audio_path, is_temp_audio = extract_audio_from_video(input_path)
        else:
            audio_path = input_path
        
        # Process the audio
        result = process_audio_func(audio_path, *args, **kwargs)
        
        # If processing generated a new audio file and input was video, combine with original video
        if result.get('success') and 'audio_path' in result.get('data', {}):
            new_audio_path = result['data']['audio_path']
            output_video_path = combine_audio_with_video(input_path, new_audio_path)
            result['data']['video_path'] = output_video_path
        
        return result
    
    finally:
        # Clean up temporary audio file if it was created
        if is_temp_audio and audio_path and os.path.exists(audio_path):
            try:
                os.remove(audio_path)
            except:
                pass 