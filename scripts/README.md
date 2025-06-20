# FastAPI backend

## Setup

1. install `uv`

```bash
pip install uv
```

2. execute using `./run_server`

3. add packages using `uv add <packages>`

4. run using `uv run <file>`


# Testing stuff
## Video
### /api/video/video-stabilization
sample request
```bash
curl -X POST "http://localhost:8000/api/video/video-stabilization" \
     -H "accept: application/json" \
     -H "Content-Type: application/json" \
     -d '{
       "video_path": "assets/demo_video.mp4",
       "time_stamp": [0.0, 30.0]
     }'
```

### /api/video/remove-bg
sample request
```bash
curl -X POST "http://localhost:8000/api/video/remove-bg" \
     -H "accept: application/json" \
     -H "Content-Type: application/json" \
     -d '{
       "video_path": "assets/demo_video.mp4"
     }'
```

### /api/video/color-grading
sample request
```bash
curl -X POST "http://localhost:8000/api/video/color-grading" \
     -H "accept: application/json" \
     -H "Content-Type: application/json" \
     -d '{
       "video_path": "assets/demo_video.mp4",
       "reference_image_path": "assets/demo_reference.jpg"
     }'
```

### /api/video/portrait-effect
sample request
```bash
curl -X POST "http://localhost:8000/api/video/portrait-effect" \
     -H "accept: application/json" \
     -H "Content-Type: application/json" \
     -d '{
       "video_path": "assets/demo_video.mp4"
     }'
```
### /api/video/denoise

Remove background noise from the audio track of a video file (MP4) using the noisereduce library. The cleaned audio is remuxed with the original video and a new MP4 is returned.

**Sample request:**

```bash
curl -X POST "http://localhost:8000/api/video/denoise" \
     -H "accept: application/json" \
     -H "Content-Type: application/json" \
     -d '{
       "video_path": "/absolute/path/to/your/video.mp4"
     }'
```

**Sample response:**
```json
{
  "success": true,
  "data": {
    "link": "/api/assets/public/denoised_yourvideo.mp4",
    "absolute_path": "/full/path/to/assets/public/denoised_yourvideo.mp4"
  }
}
```

## Image
### /api/image/super-resolution

sample request

```bash
curl -X POST "http://localhost:8000/api/image/super-resolution" \
     -H "accept: application/json" \
     -H "Content-Type: application/json" \
     -d '{
       "image_path": "/absolute/path/to/your/image.jpg"
     }'
```

### /api/image/portrait-effect/

sample request

```bash
curl -X POST "http://localhost:8000/api/image/portrait-effect" \
     -H "accept: application/json" \
     -H "Content-Type: application/json" \
     -d '{
       "image_path": "/absolute/path/to/your/image.jpg"
     }'
```

### /api/image/color-transfer/

sample request

```bash
curl -X POST "http://localhost:8000/api/image/color-transfer" \
     -H "accept: application/json" \
     -H "Content-Type: application/json" \
     -d '{
       "image_path": "/absolute/path/to/target/image.jpg",
       "reference_image_path": "/absolute/path/to/reference/image.jpg"
     }'
```

### /api/image/background-removal/
sample request
```bash
curl -X POST "http://localhost:8000/api/image/remove-bg" \
     -H "accept: application/json" \
     -H "Content-Type: application/json" \
     -d '{
       "image_path": "/absolute/path/to/your/image.jpg"
     }'
```

### /api/image/image-generation/

```bash
uv run python models/image.py generate_image -p "a beautiful sunset over mountains" -o test_generation.png --steps 20
```

## Audio
### /api/audio/transcribe

Transcribe audio files using OpenAI Whisper with automatic chunking for efficient processing.

**Features:**
- Supports multiple audio formats (wav, mp3, m4a, flac, aac, ogg, mp4)
- Automatic chunking for long audio files
- Configurable Whisper model selection
- Returns SRT subtitle format
- Uses config.yaml settings by default

**Sample request:**

```bash
# Basic transcription (uses config.yaml model: "base")
curl -X POST "http://localhost:8000/api/audio/transcribe" \
     -H "accept: application/json" \
     -H "Content-Type: application/json" \
     -d '{
       "audio_path": "/absolute/path/to/your/audio.wav"
     }'
```
### /api/audio/text-to-speech

Generate speech audio from input text using Bark by Suno.

**Sample request:**

```bash
curl -X POST "http://localhost:8000/api/audio/text-to-speech" \
     -H "Content-Type: application/json" \
     -d '{
       "text": "Hello, my name is Suno. And, uh — and I like pizza.",
       "voice_preset": "v2/en_speaker_6"
     }'
```

**Sample response:**
```json
{
  "success": true,
  "data": {
    "link": "/api/assets/public/tts_1234567890_v2_en_speaker_6.wav",
    "absolute_path": "/full/path/to/assets/public/tts_1234567890_v2_en_speaker_6.wav",
    "text": "Hello, my name is Suno. And, uh — and I like pizza.",
    "voice_preset": "v2/en_speaker_6"
  }
}
```

