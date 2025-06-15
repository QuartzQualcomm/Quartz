import os
import tempfile
import subprocess
from pathlib import Path

from fastapi import APIRouter, HTTPException

from models.audio import transcribe_audio
from data_models import AudioTranscriptionRequest, AudioTranscriptionResponse, VideoRequest, VideoResponse

router = APIRouter()

def _transcribe_audio_wrapper(audio_path: str, model: str = None) -> dict:
    """
    Wrapper function for transcribe_audio to be used with process_media_file
    """
    try:
        srt_content = transcribe_audio(audio_path, model)
        
        # Generate unique filename and save
        original_name = Path(audio_path).stem
        transcription_filename = f"transcription_{original_name}.srt"
        
        # Ensure absolute path for assets/public directory
        public_dir = Path("assets/public").resolve()
        public_dir.mkdir(parents=True, exist_ok=True)
        
        transcription_path = public_dir / transcription_filename
        transcription_path.write_text(srt_content, encoding='utf-8')
        
        # Simple duration estimation (fallback)
        try:
            result = subprocess.run([
                "ffprobe", "-i", audio_path, 
                "-show_entries", "format=duration", "-v", "quiet", "-of", "csv=p=0"
            ], capture_output=True, text=True)
            duration = float(result.stdout.strip()) if result.returncode == 0 else 0.0
        except:
            duration = 0.0
        
        return {
            "success": True,
            "data": {
                "link": f"/api/assets/public/{transcription_filename}",
                "absolute_path": str(transcription_path.resolve()),
                "content": srt_content[:500] + "..." if len(srt_content) > 500 else srt_content,
                "language": "auto-detected",
                "duration": duration
            }
        }
    except Exception as e:
        return {"success": False, "error": f"Transcription failed: {str(e)}"}

@router.post("/api/audio/transcribe")
async def api_audio_transcribe(request: AudioTranscriptionRequest):
    """
    Transcribe audio or video file using Whisper with chunked processing.

    Uses config.yaml settings for model and chunk duration.
    Supports both audio and video files - if video is provided, audio will be extracted first.
    """
    try:
        file_path = Path(request.audio_path)
        if not file_path.exists():
            raise HTTPException(status_code=404, detail=f"File not found: {file_path}")

        # Determine if input is video (e.g., .mp4)
        if file_path.suffix.lower() in ['.mp4', '.mov', '.mkv', '.avi']:
            # Extract audio to temporary WAV
            with tempfile.TemporaryDirectory() as temp_dir:
                wav_path = Path(temp_dir) / "extracted_audio.wav"
                subprocess.run([
                    'ffmpeg', '-i', str(file_path), '-vn', '-acodec', 'pcm_s16le',
                    '-ar', '44100', '-ac', '2', str(wav_path), '-y'
                ], capture_output=True, check=True)
                path_to_transcribe = str(wav_path)
                # Perform transcription
                result = _transcribe_audio_wrapper(path_to_transcribe, request.model)
                return result
        else:
            # Input is audio file
            result = _transcribe_audio_wrapper(str(file_path), request.model)
            return result

    except HTTPException as e:
        return {"success": False, "error": e.detail}
    except Exception as e:
        return {"success": False, "error": f"Transcription failed: {str(e)}"}

@router.post("/api/video/denoise")
async def api_video_denoise(request: VideoRequest):
    """
    Remove background noise from video audio and return processed video path.
    """
    try:
        from models.audio import remove_noise_from_video
        # Validate video path
        if not os.path.exists(request.video_path):
            raise HTTPException(status_code=404, detail=f"Video file not found: {request.video_path}")

        output_path = remove_noise_from_video(request.video_path)
        link = f"/api/assets/public/{Path(output_path).name}"
        response = VideoResponse(link=link, absolute_path=str(Path(output_path).resolve()))
        return {"success": True, "data": response}
    except HTTPException as e:
        return {"success": False, "error": e.detail}
    except Exception as e:
        return {"success": False, "error": f"Denoise failed: {str(e)}"}