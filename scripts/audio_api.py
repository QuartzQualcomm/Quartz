import os
from pathlib import Path

from fastapi import APIRouter, HTTPException

from models.audio import transcribe_audio
from data_models import AudioTranscriptionRequest, AudioTranscriptionResponse

router = APIRouter()

@router.post("/api/audio/transcribe")
async def api_audio_transcribe(request: AudioTranscriptionRequest):
    """
    Transcribe audio file using Whisper with chunked processing.
    
    Uses config.yaml settings for model and chunk duration.
    """
    try:
        # Validate audio path exists
        if not os.path.exists(request.audio_path):
            raise HTTPException(status_code=404, detail=f"Audio file not found: {request.audio_path}")
        
        # Use model from request if specified, otherwise let transcribe_audio use config
        model = request.model if hasattr(request, 'model') and request.model else None
        srt_content = transcribe_audio(request.audio_path, model)
        
        # Generate unique filename and save
        original_name = Path(request.audio_path).stem
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
                "ffprobe", "-i", request.audio_path, 
                "-show_entries", "format=duration", "-v", "quiet", "-of", "csv=p=0"
            ], capture_output=True, text=True)
            duration = float(result.stdout.strip()) if result.returncode == 0 else 0.0
        except:
            duration = 0.0
        
        response_data = AudioTranscriptionResponse(
            link=f"/api/assets/public/{transcription_filename}",
            absolute_path=str(transcription_path.resolve()),
            content=srt_content[:500] + "..." if len(srt_content) > 500 else srt_content,
            language="auto-detected",
            duration=duration
        )
        
        return {"success": True, "data": response_data}
        
    except HTTPException as e:
        return {"success": False, "error": e.detail}
    except Exception as e:
        return {"success": False, "error": f"Transcription failed: {str(e)}"}