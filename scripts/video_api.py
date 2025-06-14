import logging
import os
from fastapi import HTTPException
from main import router
from data_models import VideoStabilizationRequest, VideoStabilizationResponse, VideoRequest, VideoResponse, ColorGradingRequest
from utils.video_helpers import (
    generate_unique_filename, extract_video_clip, convert_to_mov,
    stabilize_video, ensure_directories_exist, get_absolute_path, cleanup_temp_files
)
from utils.image_helpers import (
    validate_image_path, load_image_from_path, perform_background_removal, 
    save_processed_image_png, perform_color_transfer, save_processed_image,
    create_portrait_effect
)
from PIL import Image
import shutil
import subprocess
import uuid
import tempfile

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def validate_video_path(video_path: str) -> None:
    """Validate that the video path exists and is a valid file."""
    if not os.path.exists(video_path):
        raise HTTPException(status_code=400, detail=f"Video file not found: {video_path}")
    if not os.path.isfile(video_path):
        raise HTTPException(status_code=400, detail=f"Path is not a file: {video_path}")

def get_video_framerate(video_path: str) -> float:
    """Get the framerate of the original video."""
    try:
        cmd = [
            "ffprobe", "-v", "quiet", "-select_streams", "v:0", 
            "-show_entries", "stream=r_frame_rate", "-of", "csv=p=0", video_path
        ]
        result = subprocess.run(cmd, capture_output=True, text=True)
        
        if result.returncode == 0 and result.stdout.strip():
            framerate_str = result.stdout.strip()
            # Handle fractional framerates like "30000/1001"
            if '/' in framerate_str:
                numerator, denominator = framerate_str.split('/')
                framerate = float(numerator) / float(denominator)
            else:
                framerate = float(framerate_str)
            
            logger.info(f"📺 Detected video framerate: {framerate} fps")
            return framerate
        else:
            logger.warning("⚠️ Could not detect framerate, defaulting to 30 fps")
            return 30.0
            
    except Exception as e:
        logger.error(f"Error getting video framerate: {str(e)}")
        return 30.0

def create_temp_directory() -> str:
    """Create a temporary directory and return its path."""
    return tempfile.mkdtemp()

def extract_frames_and_audio(video_path: str, frames_dir: str, audio_path: str) -> bool:
    """Extract frames and audio from video using FFmpeg."""
    try:
        # Extract frames
        frames_cmd = [
            "ffmpeg", "-i", video_path, "-vf", "fps=30", 
            os.path.join(frames_dir, "frame_%06d.png"), "-y"
        ]
        frames_result = subprocess.run(frames_cmd, capture_output=True, text=True)
        
        if frames_result.returncode != 0:
            logger.error(f"Failed to extract frames: {frames_result.stderr}")
            return False
        
        # Check if video has audio stream before extracting
        check_audio_cmd = [
            "ffprobe", "-v", "quiet", "-select_streams", "a:0", 
            "-show_entries", "stream=codec_type", "-of", "csv=p=0", video_path
        ]
        audio_check_result = subprocess.run(check_audio_cmd, capture_output=True, text=True)
        
        if audio_check_result.returncode == 0 and audio_check_result.stdout.strip() == "audio":
            # Video has audio stream, extract it
            audio_cmd = [
                "ffmpeg", "-i", video_path, "-vn", "-acodec", "aac", audio_path, "-y"
            ]
            audio_result = subprocess.run(audio_cmd, capture_output=True, text=True)
            
            if audio_result.returncode != 0:
                logger.error(f"Failed to extract audio: {audio_result.stderr}")
                return False
        else:
            # Video has no audio stream, create a silent audio file
            logger.info("🔇 Video has no audio stream, creating silent audio track...")
            # Get video duration first
            duration_cmd = [
                "ffprobe", "-v", "quiet", "-show_entries", "format=duration", 
                "-of", "default=noprint_wrappers=1:nokey=1", video_path
            ]
            duration_result = subprocess.run(duration_cmd, capture_output=True, text=True)
            
            if duration_result.returncode == 0:
                duration = float(duration_result.stdout.strip())
                # Create silent audio
                silent_audio_cmd = [
                    "ffmpeg", "-f", "lavfi", "-i", f"anullsrc=channel_layout=stereo:sample_rate=48000", 
                    "-t", str(duration), "-c:a", "aac", audio_path, "-y"
                ]
                silent_result = subprocess.run(silent_audio_cmd, capture_output=True, text=True)
                
                if silent_result.returncode != 0:
                    logger.error(f"Failed to create silent audio: {silent_result.stderr}")
                    return False
            else:
                logger.error("Could not determine video duration")
                return False
            
        return True
    except Exception as e:
        logger.error(f"Error extracting frames and audio: {str(e)}")
        return False

def combine_frames_to_video(frames_dir: str, output_path: str) -> bool:
    """Combine processed frames back into a video."""
    try:
        cmd = [
            "ffmpeg", "-framerate", "30", "-i", os.path.join(frames_dir, "frame_%06d.png"),
            "-c:v", "libx264", "-pix_fmt", "yuv420p", output_path, "-y"
        ]
        result = subprocess.run(cmd, capture_output=True, text=True)
        
        if result.returncode != 0:
            logger.error(f"Failed to combine frames: {result.stderr}")
            return False
            
        return True
    except Exception as e:
        logger.error(f"Error combining frames: {str(e)}")
        return False

def generate_video_filename(video_path: str, suffix: str) -> str:
    """Generate a filename for processed video."""
    base_name = os.path.splitext(os.path.basename(video_path))[0]
    return f"{base_name}_{suffix}_{generate_unique_filename('mov')}"

def add_audio_to_video(video_path: str, audio_path: str, output_path: str) -> bool:
    """Add audio track to video."""
    try:
        cmd = [
            "ffmpeg", "-i", video_path, "-i", audio_path, "-c:v", "copy", 
            "-c:a", "aac", "-map", "0:v:0", "-map", "1:a:0", output_path, "-y"
        ]
        result = subprocess.run(cmd, capture_output=True, text=True)
        
        if result.returncode != 0:
            logger.error(f"Failed to add audio: {result.stderr}")
            return False
            
        return True
    except Exception as e:
        logger.error(f"Error adding audio: {str(e)}")
        return False

def combine_frames_to_video_with_audio(frames_dir: str, audio_path: str, output_path: str, framerate: float) -> bool:
    """Combine processed frames with audio into final video using specified framerate."""
    try:
        cmd = [
            "ffmpeg", "-framerate", str(framerate), "-i", os.path.join(frames_dir, "frame_%06d.png"),
            "-i", audio_path, "-c:v", "libx264", "-pix_fmt", "yuv420p", "-shortest", output_path, "-y"
        ]
        result = subprocess.run(cmd, capture_output=True, text=True)
        
        if result.returncode != 0:
            logger.error(f"Failed to combine frames with audio: {result.stderr}")
            return False
            
        return True
    except Exception as e:
        logger.error(f"Error combining frames with audio: {str(e)}")
        return False

@router.post("/api/video/video-stabilization", response_model=VideoStabilizationResponse)
def api_video_stabilization(request: VideoStabilizationRequest) -> VideoStabilizationResponse:
    """
    Stabilize video segment using VidStab library.
    
    Args:
        request: VideoStabilizationRequest containing video path and timestamps
    Returns:
        VideoStabilizationResponse with download link and absolute path
    Raises:
        HTTPException: If video processing fails at any step
    """
    logger.info("🎬 Starting video stabilization API call")
    logger.info(f"📁 Input video path: {request.video_path}")
    logger.info(f"⏱️  Time range: {request.time_stamp[0]}s - {request.time_stamp[1]}s")
    
    logger.info("📂 Ensuring directories exist...")
    ensure_directories_exist()
    
    # Generate unique filenames for processing steps
    temp_clip_name = generate_unique_filename("mp4")
    temp_mov_name = generate_unique_filename("mov") 
    final_output_name = generate_unique_filename("mov")
    
    # Define file paths for processing pipeline
    temp_clip_path = f"tmp/{temp_clip_name}"
    temp_mov_path = f"tmp/{temp_mov_name}"
    final_output_path = f"assets/public/{final_output_name}"
    
    logger.info(f"🔄 Generated processing pipeline:")
    logger.info(f"   • Temp clip: {temp_clip_path}")
    logger.info(f"   • Temp MOV: {temp_mov_path}")
    logger.info(f"   • Final output: {final_output_path}")
    
    try:
        # Extract video segment from specified time range
        logger.info("✂️  Step 1/3: Extracting video clip...")
        if not extract_video_clip(request.video_path, request.time_stamp[0], 
                                 request.time_stamp[1], temp_clip_path):
            logger.error("❌ Failed to extract video clip")
            raise HTTPException(status_code=400, detail="Failed to extract video clip")
        logger.info("✅ Video clip extraction completed successfully")
        
        # Convert extracted clip to MOV format
        logger.info("🔄 Step 2/3: Converting to MOV format...")
        if not convert_to_mov(temp_clip_path, temp_mov_path):
            logger.error("❌ Failed to convert video format")
            cleanup_temp_files(temp_clip_path)
            raise HTTPException(status_code=400, detail="Failed to convert video format")
        logger.info("✅ Video format conversion completed successfully")
        
        # Apply video stabilization using VidStab
        logger.info("🎯 Step 3/3: Applying video stabilization...")
        if not stabilize_video(temp_mov_path, final_output_path):
            logger.error("❌ Failed to stabilize video")
            cleanup_temp_files(temp_clip_path, temp_mov_path)
            raise HTTPException(status_code=400, detail="Failed to stabilize video")
        logger.info("✅ Video stabilization completed successfully")
        
        # Clean up temporary files after successful processing
        logger.info("🧹 Cleaning up temporary files...")
        cleanup_temp_files(temp_clip_path, temp_mov_path)
        logger.info("✅ Temporary files cleaned up")
        
        # Return response with download link and absolute path
        absolute_path = get_absolute_path(final_output_path)
        download_link = f"/api/assets/public/{final_output_name}"
        
        logger.info("🎉 Video stabilization API call completed successfully!")
        logger.info(f"📥 Download link: {download_link}")
        logger.info(f"📍 Absolute path: {absolute_path}")
        
        return VideoStabilizationResponse(
            link=download_link,
            absolute_path=absolute_path
        )
        
    except HTTPException:
        # Re-raise HTTP exceptions as-is
        logger.error("❌ HTTP exception occurred during video processing")
        raise
    except Exception as e:
        # Clean up any remaining temporary files on unexpected error
        logger.error(f"💥 Unexpected error during video processing: {str(e)}")
        logger.info("🧹 Attempting cleanup of temporary files...")
        cleanup_temp_files(temp_clip_path, temp_mov_path)
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


@router.post("/api/video/remove-bg")
async def api_video_background_removal(request: VideoRequest) -> VideoResponse:
    """
    Remove background from video frames using RMBG-1.4 model.
    
    Processes video frame by frame, removes background from each frame,
    and combines frames back into a video with original audio.
    
    Args:
        request: VideoRequest containing path to input video
        
    Returns:
        VideoResponse with download link and absolute path to processed video
        
    Raises:
        HTTPException: If processing fails
    """
    temp_dir = None
    try:
        # Validate video path
        validate_video_path(request.video_path)
        
        # Get original video framerate
        original_framerate = get_video_framerate(request.video_path)
        
        # Create temporary files
        temp_dir = "./tmp"
        temp_frames_dir = os.path.join(temp_dir, "frames")
        temp_processed_dir = os.path.join(temp_dir, "processed")
        os.makedirs(temp_frames_dir, exist_ok=True)
        os.makedirs(temp_processed_dir, exist_ok=True)
        
        # Extract frames and audio
        logger.info("🔄 Step 1/3: Extracting video frames and audio...")
        audio_path = os.path.join(temp_dir, "audio.aac")
        if not extract_frames_and_audio(request.video_path, temp_frames_dir, audio_path):
            logger.error("❌ Failed to extract frames and audio")
            cleanup_temp_files(temp_dir)
            raise HTTPException(status_code=400, detail="Failed to extract video frames")
            
        # Process each frame
        logger.info("🎯 Step 2/3: Processing frames...")
        frame_files = sorted(os.listdir(temp_frames_dir))
        for frame_file in frame_files:
            frame_path = os.path.join(temp_frames_dir, frame_file)
            output_path = os.path.join(temp_processed_dir, frame_file)
            
            # Load frame and remove background
            frame = load_image_from_path(frame_path)
            processed_frame = perform_background_removal(frame)
            
            # Save processed frame directly as PNG with transparency
            processed_pil = Image.fromarray(processed_frame, mode='RGBA')
            processed_pil.save(output_path, format='PNG')
            
        # Combine processed frames with audio
        logger.info("🎬 Step 3/3: Combining processed frames with audio...")
        ensure_directories_exist()
        final_output_name = generate_video_filename(request.video_path, "bg_removed")
        final_output_path = os.path.join("assets", "public", final_output_name)
        if not combine_frames_to_video_with_audio(temp_processed_dir, audio_path, final_output_path, original_framerate):
            logger.error("❌ Failed to combine frames with audio")
            cleanup_temp_files(temp_dir)
            raise HTTPException(status_code=400, detail="Failed to combine frames with audio")
            
        # Clean up temporary files
        logger.info("🧹 Cleaning up temporary files...")
        cleanup_temp_files(temp_dir)
        
        # Return response
        absolute_path = get_absolute_path(final_output_path)
        download_link = f"/api/assets/public/{final_output_name}"
        
        return VideoResponse(
            link=download_link,
            absolute_path=absolute_path
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"💥 Unexpected error: {str(e)}")
        if temp_dir:
            cleanup_temp_files(temp_dir)
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


@router.post("/api/video/color-grading")
async def api_video_color_grading(request: ColorGradingRequest) -> VideoResponse:
    """
    Apply color grading to video using reference image.
    
    Processes video frame by frame, applies color transfer from reference image
    to each frame, and combines frames back into a video with original audio.
    
    Args:
        request: ColorGradingRequest containing video path and reference image path
        
    Returns:
        VideoResponse with download link and absolute path to processed video
        
    Raises:
        HTTPException: If processing fails
    """
    temp_dir = None
    try:
        # Validate paths
        validate_video_path(request.video_path)
        validate_image_path(request.reference_image_path)
        
        # Get original video framerate
        original_framerate = get_video_framerate(request.video_path)
        
        # Load reference image
        reference_image = load_image_from_path(request.reference_image_path)
        
        # Create temporary files
        temp_dir = "./tmp"
        temp_frames_dir = os.path.join(temp_dir, "frames")
        temp_processed_dir = os.path.join(temp_dir, "processed")
        os.makedirs(temp_frames_dir, exist_ok=True)
        os.makedirs(temp_processed_dir, exist_ok=True)
        
        # Extract frames and audio
        logger.info("🔄 Step 1/3: Extracting video frames and audio...")
        audio_path = os.path.join(temp_dir, "audio.aac")
        if not extract_frames_and_audio(request.video_path, temp_frames_dir, audio_path):
            logger.error("❌ Failed to extract frames and audio")
            cleanup_temp_files(temp_dir)
            raise HTTPException(status_code=400, detail="Failed to extract video frames")
            
        # Process each frame
        logger.info("🎨 Step 2/3: Applying color grading...")
        frame_files = sorted(os.listdir(temp_frames_dir))
        for frame_file in frame_files:
            frame_path = os.path.join(temp_frames_dir, frame_file)
            output_path = os.path.join(temp_processed_dir, frame_file)
            
            # Load frame and apply color transfer
            frame = load_image_from_path(frame_path)
            processed_frame = perform_color_transfer(reference_image, frame)
            save_processed_image(processed_frame, output_path, root_path="./")
            
        # Combine processed frames with audio
        logger.info("🎬 Step 3/3: Combining processed frames with audio...")
        ensure_directories_exist()
        final_output_name = generate_video_filename(request.video_path, "color_graded")
        final_output_path = os.path.join("assets", "public", final_output_name)
        if not combine_frames_to_video_with_audio(temp_processed_dir, audio_path, final_output_path, original_framerate):
            logger.error("❌ Failed to combine frames with audio")
            cleanup_temp_files(temp_dir)
            raise HTTPException(status_code=400, detail="Failed to combine frames with audio")
            
        # Clean up temporary files
        logger.info("🧹 Cleaning up temporary files...")
        cleanup_temp_files(temp_dir)
        
        # Return response
        absolute_path = get_absolute_path(final_output_path)
        download_link = f"/api/assets/public/{final_output_name}"
        
        return VideoResponse(
            link=download_link,
            absolute_path=absolute_path
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"💥 Unexpected error: {str(e)}")
        if temp_dir:
            cleanup_temp_files(temp_dir)
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


@router.post("/api/video/portrait-effect")
async def api_video_portrait_effect(request: VideoRequest) -> VideoResponse:
    """
    Apply portrait effect with depth-based blur to video.
    
    Processes video frame by frame, applies depth-based background blur
    to each frame, and combines frames back into a video with original audio.
    
    Args:
        request: VideoRequest containing path to input video
        
    Returns:
        VideoResponse with download link and absolute path to processed video
        
    Raises:
        HTTPException: If processing fails
    """
    temp_dir = None
    try:
        # Validate video path
        validate_video_path(request.video_path)
        
        # Get original video framerate
        original_framerate = get_video_framerate(request.video_path)
        
        # Create temporary files
        temp_dir = "./tmp"
        temp_frames_dir = os.path.join(temp_dir, "frames")
        temp_processed_dir = os.path.join(temp_dir, "processed")
        os.makedirs(temp_frames_dir, exist_ok=True)
        os.makedirs(temp_processed_dir, exist_ok=True)
        
        # Extract frames and audio
        logger.info("🔄 Step 1/3: Extracting video frames and audio...")
        audio_path = os.path.join(temp_dir, "audio.aac")
        if not extract_frames_and_audio(request.video_path, temp_frames_dir, audio_path):
            logger.error("❌ Failed to extract frames and audio")
            cleanup_temp_files(temp_dir)
            raise HTTPException(status_code=400, detail="Failed to extract video frames")
            
        # Process each frame
        logger.info("🎯 Step 2/3: Applying portrait effect...")
        frame_files = sorted(os.listdir(temp_frames_dir))
        for frame_file in frame_files:
            frame_path = os.path.join(temp_frames_dir, frame_file)
            output_path = os.path.join(temp_processed_dir, frame_file)
            
            # Load frame and apply portrait effect
            frame = load_image_from_path(frame_path)
            processed_frame = create_portrait_effect(frame)
            save_processed_image(processed_frame, output_path)
            
        # Combine processed frames with audio
        logger.info("🎬 Step 3/3: Combining processed frames with audio...")
        ensure_directories_exist()
        final_output_name = generate_video_filename(request.video_path, "portrait_effect")
        final_output_path = os.path.join("assets", "public", final_output_name)
        if not combine_frames_to_video_with_audio(temp_processed_dir, audio_path, final_output_path, original_framerate):
            logger.error("❌ Failed to combine frames with audio")
            cleanup_temp_files(temp_dir)
            raise HTTPException(status_code=400, detail="Failed to combine frames with audio")
            
        # Clean up temporary files
        logger.info("🧹 Cleaning up temporary files...")
        cleanup_temp_files(temp_dir)
        
        # Return response
        absolute_path = get_absolute_path(final_output_path)
        download_link = f"/api/assets/public/{final_output_name}"
        
        return VideoResponse(
            link=download_link,
            absolute_path=absolute_path
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"💥 Unexpected error: {str(e)}")
        if temp_dir:
            cleanup_temp_files(temp_dir)
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")
