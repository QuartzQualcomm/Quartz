import logging
import os
from fastapi import HTTPException, APIRouter
from main import router
from data_models import VideoStabilizationRequest, VideoStabilizationResponse, VideoRequest, VideoResponse, ColorGradingRequest
from utils.video_helpers import (
    generate_unique_filename, extract_video_clip, convert_to_mov,
    stabilize_video, ensure_directories_exist, get_absolute_path, cleanup_temp_files,
    convert_video_to_24fps
)
from utils.image_helpers import (
    validate_image_path, load_image_from_path, perform_background_removal, 
    save_processed_image_png, perform_color_transfer, save_processed_image,
    create_portrait_effect
)
import tempfile
import shutil
import subprocess

router = APIRouter()

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def validate_video_path(video_path: str) -> None:
    """Validate that the video path exists and is a valid file."""
    if not os.path.exists(video_path):
        raise HTTPException(status_code=400, detail=f"Video file not found: {video_path}")
    if not os.path.isfile(video_path):
        raise HTTPException(status_code=400, detail=f"Path is not a file: {video_path}")

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
        
        # Extract audio
        audio_cmd = [
            "ffmpeg", "-i", video_path, "-vn", "-acodec", "aac", audio_path, "-y"
        ]
        audio_result = subprocess.run(audio_cmd, capture_output=True, text=True)
        
        if audio_result.returncode != 0:
            logger.error(f"Failed to extract audio: {audio_result.stderr}")
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

@router.post("/api/video/video-stabilization", response_model=VideoStabilizationResponse)
def api_video_stabilization(request: VideoStabilizationRequest) -> VideoStabilizationResponse:
    """
    Stabilize a video using the VidStab library.
    
    Args:
        request: VideoStabilizationRequest containing the video path.
    Returns:
        JSON object with success status and either data or error message.
    Raises:
        HTTPException: If video processing fails at any step.
    """
    temp_clip_path = None
    temp_mov_path = None
    final_output_path = None
    fps_video_path = None

    try:
        logger.info("🎬 Starting video stabilization API call")
        logger.info(f"📁 Input video path: {request.video_path}")
        
        logger.info("📂 Ensuring directories exist...")
        ensure_directories_exist()

        # Step 1: Convert video to 24 FPS
        logger.info("🔄 Step 1/4: Converting video to 24 FPS...")
        fps_video_name = generate_unique_filename("mp4")
        fps_video_path = f"tmp/{fps_video_name}"
        if not convert_video_to_24fps(request.video_path, fps_video_path):
            logger.error("❌ Failed to convert video to 24 FPS")
            raise Exception("Failed to convert video to 24 FPS")
        logger.info("✅ Video conversion to 24 FPS completed successfully")
        
        # Generate unique filenames for processing steps
        temp_mov_name = generate_unique_filename("mov") 
        final_output_name = generate_unique_filename("mov")
        
        # Define file paths for processing pipeline
        temp_mov_path = f"tmp/{temp_mov_name}"
        final_output_path = f"assets/public/{final_output_name}"
        
        logger.info(f"🔄 Generated processing pipeline:")
        logger.info(f"   • Temp MOV: {temp_mov_path}")
        logger.info(f"   • Final output: {final_output_path}")
        
        # Convert 24fps video to MOV format
        logger.info("🔄 Step 2/4: Converting to MOV format...")
        if not convert_to_mov(fps_video_path, temp_mov_path):
            logger.error("❌ Failed to convert video format")
            cleanup_temp_files(fps_video_path)
            raise Exception("Failed to convert video format")
        logger.info("✅ Video format conversion completed successfully")
        
        # Apply video stabilization using VidStab
        logger.info("🎯 Step 3/4: Applying video stabilization...")
        if not stabilize_video(temp_mov_path, final_output_path):
            logger.error("❌ Failed to stabilize video")
            cleanup_temp_files(fps_video_path, temp_mov_path)
            raise Exception("Failed to stabilize video")
        logger.info("✅ Video stabilization completed successfully")
        
        # Clean up temporary files after successful processing
        logger.info("🧹 Step 4/4: Cleaning up temporary files...")
        cleanup_temp_files(fps_video_path, temp_mov_path)
        logger.info("✅ Temporary files cleaned up")
        
        # Return response with download link and absolute path
        absolute_path = get_absolute_path(final_output_path)
        download_link = f"/api/assets/public/{final_output_name}"
        
        logger.info("🎉 Video stabilization API call completed successfully!")
        logger.info(f"📥 Download link: {download_link}")
        logger.info(f"📍 Absolute path: {absolute_path}")
        
        response_data = VideoStabilizationResponse(
            link=download_link,
            absolute_path=absolute_path
        )
        return response_data
        
    except Exception as e:
        # Clean up any remaining temporary files on unexpected error
        logger.error(f"💥 Unexpected error during video processing: {str(e)}")
        logger.info("🧹 Attempting cleanup of temporary files...")
        cleanup_temp_files(fps_video_path, temp_mov_path, final_output_path)
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
    fps_video_path = None
    try:
        # Validate video path
        validate_video_path(request.video_path)
        
        # Step 1: Convert video to 24 FPS
        logger.info("🔄 Step 1/5: Converting video to 24 FPS...")
        fps_video_name = generate_unique_filename("mp4")
        fps_video_path = os.path.join(tempfile.gettempdir(), fps_video_name)
        if not convert_video_to_24fps(request.video_path, fps_video_path):
            logger.error("❌ Failed to convert video to 24 FPS")
            raise HTTPException(status_code=500, detail="Failed to convert video to 24 FPS")
        logger.info("✅ Video conversion to 24 FPS completed successfully")

        # Create temporary files
        temp_dir = create_temp_directory()
        temp_frames_dir = os.path.join(temp_dir, "frames")
        temp_processed_dir = os.path.join(temp_dir, "processed")
        os.makedirs(temp_frames_dir)
        os.makedirs(temp_processed_dir)
        
        # Extract frames and audio
        logger.info("🔄 Step 2/5: Extracting video frames and audio...")
        audio_path = os.path.join(temp_dir, "audio.aac")
        if not extract_frames_and_audio(fps_video_path, temp_frames_dir, audio_path):
            logger.error("❌ Failed to extract frames and audio")
            cleanup_temp_files(temp_dir, fps_video_path)
            raise HTTPException(status_code=400, detail="Failed to extract video frames")
            
        # Process each frame
        logger.info("🎯 Step 3/5: Processing frames...")
        frame_files = sorted(os.listdir(temp_frames_dir))
        for frame_file in frame_files:
            frame_path = os.path.join(temp_frames_dir, frame_file)
            output_path = os.path.join(temp_processed_dir, frame_file)
            
            # Load frame and remove background
            frame = load_image_from_path(frame_path)
            processed_frame = perform_background_removal(frame)
            save_processed_image_png(processed_frame, output_path)
            
        # Combine processed frames into video
        logger.info("🎬 Step 4/5: Combining processed frames...")
        output_video = os.path.join(temp_dir, "output.mov")
        if not combine_frames_to_video(temp_processed_dir, output_video):
            logger.error("❌ Failed to combine frames")
            cleanup_temp_files(temp_dir, fps_video_path)
            raise HTTPException(status_code=400, detail="Failed to combine frames")
            
        # Add audio to final video
        logger.info("🔊 Step 5/5: Adding audio...")
        final_video_name = generate_video_filename(request.video_path, "bg_removed")
        final_video_path = f"assets/public/{final_video_name}"
        if not add_audio_to_video(output_video, audio_path, final_video_path):
            logger.error("❌ Failed to add audio")
            cleanup_temp_files(temp_dir, fps_video_path)
            raise HTTPException(status_code=400, detail="Failed to add audio")
            
        # Clean up temporary files
        cleanup_temp_files(temp_dir, fps_video_path)
        
        # Return response
        absolute_path = get_absolute_path(final_video_path)
        download_link = f"/api/assets/public/{final_video_name}"
        
        return VideoResponse(
            link=download_link,
            absolute_path=absolute_path
        )
        
    except Exception as e:
        # Ensure cleanup on any exception
        cleanup_temp_files(temp_dir, fps_video_path)
        logger.error(f"💥 Unexpected error in background removal API: {e}")
        raise HTTPException(status_code=500, detail="An unexpected error occurred during background removal.")


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
    fps_video_path = None
    try:
        # Validate paths
        validate_video_path(request.video_path)
        validate_image_path(request.reference_image_path)
        
        # Step 1: Convert video to 24 FPS
        logger.info("🔄 Step 1/5: Converting video to 24 FPS...")
        fps_video_name = generate_unique_filename("mp4")
        fps_video_path = os.path.join(tempfile.gettempdir(), fps_video_name)
        if not convert_video_to_24fps(request.video_path, fps_video_path):
            logger.error("❌ Failed to convert video to 24 FPS")
            raise HTTPException(status_code=500, detail="Failed to convert video to 24 FPS")
        logger.info("✅ Video conversion to 24 FPS completed successfully")

        # Create temporary files
        temp_dir = create_temp_directory()
        temp_frames_dir = os.path.join(temp_dir, "frames")
        temp_processed_dir = os.path.join(temp_dir, "processed")
        os.makedirs(temp_frames_dir)
        os.makedirs(temp_processed_dir)
        
        # Extract frames and audio
        logger.info("🔄 Step 2/5: Extracting video frames and audio...")
        audio_path = os.path.join(temp_dir, "audio.aac")
        if not extract_frames_and_audio(fps_video_path, temp_frames_dir, audio_path):
            logger.error("❌ Failed to extract frames and audio")
            cleanup_temp_files(temp_dir, fps_video_path)
            raise HTTPException(status_code=400, detail="Failed to extract video frames")
            
        # Load reference image for color transfer
        reference_image = load_image_from_path(request.reference_image_path)
            
        # Process each frame
        logger.info("🎯 Step 3/5: Processing frames...")
        frame_files = sorted(os.listdir(temp_frames_dir))
        for frame_file in frame_files:
            frame_path = os.path.join(temp_frames_dir, frame_file)
            output_path = os.path.join(temp_processed_dir, frame_file)
            
            # Load frame and apply color transfer
            frame = load_image_from_path(frame_path)
            processed_frame = perform_color_transfer(frame, reference_image)
            save_processed_image(processed_frame, output_path)
            
        # Combine processed frames into video
        logger.info("🎬 Step 4/5: Combining processed frames...")
        output_video = os.path.join(temp_dir, "output.mov")
        if not combine_frames_to_video(temp_processed_dir, output_video):
            logger.error("❌ Failed to combine frames")
            cleanup_temp_files(temp_dir, fps_video_path)
            raise HTTPException(status_code=400, detail="Failed to combine frames")
            
        # Add audio to final video
        logger.info("🔊 Step 5/5: Adding audio...")
        final_video_name = generate_video_filename(request.video_path, "color_graded")
        final_video_path = f"assets/public/{final_video_name}"
        if not add_audio_to_video(output_video, audio_path, final_video_path):
            logger.error("❌ Failed to add audio")
            cleanup_temp_files(temp_dir, fps_video_path)
            raise HTTPException(status_code=400, detail="Failed to add audio")
            
        # Clean up temporary files
        cleanup_temp_files(temp_dir, fps_video_path)
        
        # Return response
        absolute_path = get_absolute_path(final_video_path)
        download_link = f"/api/assets/public/{final_video_name}"
        
        return VideoResponse(
            link=download_link,
            absolute_path=absolute_path
        )
        
    except Exception as e:
        # Ensure cleanup on any exception
        cleanup_temp_files(temp_dir, fps_video_path)
        logger.error(f"💥 Unexpected error in color grading API: {e}")
        raise HTTPException(status_code=500, detail="An unexpected error occurred during color grading.")


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
    fps_video_path = None
    try:
        # Validate video path
        validate_video_path(request.video_path)
        
        # Step 1: Convert video to 24 FPS
        logger.info("🔄 Step 1/5: Converting video to 24 FPS...")
        fps_video_name = generate_unique_filename("mp4")
        fps_video_path = os.path.join(tempfile.gettempdir(), fps_video_name)
        if not convert_video_to_24fps(request.video_path, fps_video_path):
            logger.error("❌ Failed to convert video to 24 FPS")
            raise HTTPException(status_code=500, detail="Failed to convert video to 24 FPS")
        logger.info("✅ Video conversion to 24 FPS completed successfully")

        # Create temporary directory
        temp_dir = create_temp_directory()
        temp_frames_dir = os.path.join(temp_dir, "frames")
        temp_processed_dir = os.path.join(temp_dir, "processed")
        os.makedirs(temp_frames_dir)
        os.makedirs(temp_processed_dir)
        
        # Extract frames and audio
        logger.info("🔄 Step 2/5: Extracting frames and audio...")
        audio_path = os.path.join(temp_dir, "audio.aac")
        if not extract_frames_and_audio(fps_video_path, temp_frames_dir, audio_path):
            logger.error("❌ Failed to extract video frames")
            cleanup_temp_files(temp_dir, fps_video_path)
            raise HTTPException(status_code=400, detail="Failed to extract video frames")
            
        # Process each frame
        logger.info("🎯 Step 3/5: Processing frames...")
        frame_files = sorted(os.listdir(temp_frames_dir))
        for frame_file in frame_files:
            frame_path = os.path.join(temp_frames_dir, frame_file)
            output_path = os.path.join(temp_processed_dir, frame_file)
            
            # Load frame and apply portrait effect
            frame = load_image_from_path(frame_path)
            processed_frame = create_portrait_effect(frame)
            save_processed_image(processed_frame, output_path)
            
        # Combine processed frames into video
        logger.info("🎬 Step 4/5: Combining processed frames...")
        output_video = os.path.join(temp_dir, "output.mov")
        if not combine_frames_to_video(temp_processed_dir, output_video):
            logger.error("❌ Failed to combine frames")
            cleanup_temp_files(temp_dir, fps_video_path)
            raise HTTPException(status_code=400, detail="Failed to combine frames")
            
        # Add audio to final video
        logger.info("🔊 Step 5/5: Adding audio...")
        final_video_name = generate_video_filename(request.video_path, "portrait")
        final_video_path = f"assets/public/{final_video_name}"
        if not add_audio_to_video(output_video, audio_path, final_video_path):
            logger.error("❌ Failed to add audio")
            cleanup_temp_files(temp_dir, fps_video_path)
            raise HTTPException(status_code=400, detail="Failed to add audio")
            
        # Clean up temporary directory
        cleanup_temp_files(temp_dir, fps_video_path)
        
        # Return response
        absolute_path = get_absolute_path(final_video_path)
        download_link = f"/api/assets/public/{final_video_name}"
        
        return VideoResponse(
            link=download_link,
            absolute_path=absolute_path
        )
        
    except Exception as e:
        cleanup_temp_files(temp_dir, fps_video_path)
        logger.error(f"💥 Unexpected error in portrait effect API: {e}")
        raise HTTPException(status_code=500, detail="An unexpected error occurred during portrait effect.")
