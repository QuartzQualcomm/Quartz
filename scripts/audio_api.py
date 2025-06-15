import os
import tempfile
import subprocess
from pathlib import Path

from fastapi import APIRouter, HTTPException

from models.audio import transcribe_audio, bark_text_to_speech
from data_models import (
    AudioTranscriptionRequest,
    AudioTranscriptionResponse,
    VideoRequest,
    VideoResponse,
)
from data_models import TextToSpeechRequest, TextToSpeechResponse
from audio_utils import process_media_file, remove_noise

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
        transcription_path.write_text(srt_content, encoding="utf-8")

        # Simple duration estimation (fallback)
        try:
            result = subprocess.run(
                [
                    "ffprobe",
                    "-i",
                    audio_path,
                    "-show_entries",
                    "format=duration",
                    "-v",
                    "quiet",
                    "-of",
                    "csv=p=0",
                ],
                capture_output=True,
                text=True,
            )
            duration = float(result.stdout.strip()) if result.returncode == 0 else 0.0
        except:
            duration = 0.0

        return {
            "success": True,
            "data": {
                "link": f"/api/assets/public/{transcription_filename}",
                "absolute_path": str(transcription_path.resolve()),
                "content": (
                    srt_content[:500] + "..." if len(srt_content) > 500 else srt_content
                ),
                "language": "auto-detected",
                "duration": duration,
            },
        }
    except Exception as e:
        return {"success": False, "error": f"Transcription failed: {str(e)}"}


def _remove_noise_wrapper(audio_path: str) -> dict:
    """
    Wrapper function for noise removal to be used with process_media_file
    """
    try:
        # Process the audio
        processed_audio_path = remove_noise(audio_path)

        # Move to public directory
        public_dir = Path("assets/public").resolve()
        public_dir.mkdir(parents=True, exist_ok=True)

        # Generate unique filename
        original_name = Path(audio_path).stem
        output_filename = f"denoised_{original_name}.wav"
        output_path = public_dir / output_filename

        # Move the processed file to public directory
        os.rename(processed_audio_path, output_path)

        # Get absolute paths
        abs_output_path = str(output_path.resolve())
        abs_original_path = str(Path(audio_path).resolve())

        return {
            "success": True,
            "data": {
                "audio_path": abs_output_path,
                "link": f"/api/assets/public/{output_filename}",
                "absolute_path": abs_output_path,
                "original_file_absolute_path": abs_original_path,
            },
        }
    except Exception as e:
        return {"success": False, "error": f"Noise removal failed: {str(e)}"}


@router.post("/api/audio/transcribe")
async def api_audio_transcribe(request):
    """
    Transcribe audio or video file using Whisper with chunked processing.

    Uses config.yaml settings for model and chunk duration.
    Supports both audio and video files - if video is provided, audio will be extracted first.
    """
    try:
        # Validate file path exists
        if not os.path.exists(request.audio_path):
            raise HTTPException(
                status_code=404, detail=f"File not found: {request.audio_path}"
            )

        # Use model from request if specified, otherwise let transcribe_audio use config
        model = request.model if hasattr(request, "model") and request.model else None

        # Process the media file using our utility
        result = process_media_file(
            request.audio_path, _transcribe_audio_wrapper, model
        )

        # Add original file absolute path to response
        if result.get("success"):
            result["data"]["original_file_absolute_path"] = str(
                Path(request.audio_path).resolve()
            )

        return result

    except HTTPException as e:
        return {"success": False, "error": e.detail}
    except Exception as e:
        return {"success": False, "error": f"Transcription failed: {str(e)}"}


@router.post("/api/audio/remove-noise")
async def api_remove_noise(request: AudioTranscriptionRequest):
    """
    Remove background noise from audio or video file.

    Supports both audio and video files - if video is provided, audio will be extracted first,
    processed, and then combined back with the original video.
    """
    try:
        # Validate file path exists
        if not os.path.exists(request.audio_path):
            raise HTTPException(
                status_code=404, detail=f"File not found: {request.audio_path}"
            )

        # Process the media file using our utility
        result = process_media_file(request.audio_path, _remove_noise_wrapper)

        # Add original file absolute path to response if not already present
        if (
            result.get("success")
            and "original_file_absolute_path" not in result["data"]
        ):
            result["data"]["original_file_absolute_path"] = str(
                Path(request.audio_path).resolve()
            )

        return result

    except HTTPException as e:
        return {"success": False, "error": e.detail}
    except Exception as e:
        return {"success": False, "error": f"Noise removal failed: {str(e)}"}


@router.post("/api/audio/text-to-speech")
async def api_text_to_speech(text: str):
    """
    Generate speech audio from input text using Bark by Suno.
    """
    try:
        public_dir = Path("assets/public").resolve()
        public_dir.mkdir(parents=True, exist_ok=True)
        # Use default preset if not provided
        voice_preset = "v2/en_speaker_6"
        filename = f"tts_{hash(text)}_{voice_preset.replace('/', '_')}.wav"
        output_path = public_dir / filename

        # Generate audio
        result_path = bark_text_to_speech(text, str(output_path), voice_preset)
        abs_path = str(Path(result_path).resolve())
        link = f"/api/assets/public/{filename}"
        response = TextToSpeechResponse(
            link=link,
            absolute_path=abs_path,
            text=text,
            voice_preset=voice_preset,
        )
        return response
    except Exception as e:
        return {"success": False, "error": f"Text-to-speech failed: {str(e)}"}


@router.post("/api/video/denoise")
async def api_video_denoise(path: str):
    """
    Remove background noise from video audio and return processed video path.
    """
    try:
        from models.audio import remove_noise_from_video

        # Validate video path
        if not os.path.exists(path):
            raise HTTPException(
                status_code=404, detail=f"Video file not found: {path}"
            )

        output_path = remove_noise_from_video(path)
        link = f"/api/assets/public/{Path(output_path).name}"
        response = VideoResponse(
            link=link, absolute_path=str(Path(output_path).resolve())
        )
        return {"success": True, "data": response}
    except HTTPException as e:
        return {"success": False, "error": e.detail}
    except Exception as e:
        return {"success": False, "error": f"Denoise failed: {str(e)}"}
