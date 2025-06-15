import os
from pathlib import Path

from fastapi import APIRouter, HTTPException

from models.audio import transcribe_audio
from data_models import AudioTranscriptionRequest, AudioTranscriptionResponse
from audio_utils import process_media_file

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
            import subprocess
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
        # Validate file path exists
        if not os.path.exists(request.audio_path):
            raise HTTPException(status_code=404, detail=f"File not found: {request.audio_path}")
        
        # Use model from request if specified, otherwise let transcribe_audio use config
        model = request.model if hasattr(request, 'model') and request.model else None
        
        # Process the media file using our utility
        result = process_media_file(
            request.audio_path,
            _transcribe_audio_wrapper,
            model
        )
        
        return result
        
    except HTTPException as e:
        return {"success": False, "error": e.detail}
    except Exception as e:
        return {"success": False, "error": f"Transcription failed: {str(e)}"}