import os
import subprocess
import uuid
import logging
import cv2
import numpy as np
from vidstab import VidStab
from typing import Tuple
import sys
import time
from pathlib import Path
from datetime import datetime
from rich.console import Console
from rich.panel import Panel
from rich.text import Text
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TaskProgressColumn
from rich.logging import RichHandler
import shutil

# Add the project root to the Python path to import from models
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# Initialize Rich console
console = Console()

# Configure logging with Rich
logging.basicConfig(
    level=logging.INFO,
    format="%(message)s",
    datefmt="[%X]",
    handlers=[RichHandler(console=console, rich_tracebacks=True)]
)
logger = logging.getLogger(__name__)

def generate_unique_filename(extension: str = "mov") -> str:
    """
    Generate unique filename with specified extension.
    
    Args:
        extension: File extension (default: "mov")
    Returns:
        Unique filename string
    """
    filename = f"{uuid.uuid4().hex}.{extension}"
    logger.debug(f"[cyan]🏷️  Generated unique filename: {filename}[/cyan]")
    return filename


def extract_video_clip(input_path: str, start_time: float, end_time: float, output_path: str) -> bool:
    """
    Extract video clip using FFmpeg with specified time range and convert to MOV with H264.
    
    Args:
        input_path: Path to input video file
        start_time: Start timestamp in seconds
        end_time: End timestamp in seconds 
        output_path: Path for output video clip
    Returns:
        Boolean indicating success/failure
    """
    console.print(f"[bold cyan]✂️  Extracting clip from {Path(input_path).name} ({start_time}s - {end_time}s)[/bold cyan]")
    console.print(f"[cyan]🎬 Converting to MOV with H264[/cyan]")
    
    try:
        cmd = [
            "ffmpeg", "-i", input_path, "-ss", str(start_time),
            "-to", str(end_time), "-c:v", "libx264", 
            "-preset", "medium", "-crf", "23", "-c:a", "aac", "-y", output_path
        ]
        console.print(f"[dim]🔧 Running: {' '.join(cmd)}[/dim]")
        
        # Stream FFmpeg output
        process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, 
                                 universal_newlines=True, bufsize=1)
        
        with console.status("[bold green]Extracting and converting to MOV..."):
            for line in process.stdout:
                if line.strip():
                    logger.debug(f"[dim]📺 {line.strip()}[/dim]")
        
        process.wait()
        
        if process.returncode == 0:
            console.print(f"[bold green]✅ Video clip extracted and converted to MOV[/bold green]")
            return True
        else:
            console.print(f"[bold red]❌ FFmpeg extraction failed with return code {process.returncode}[/bold red]")
            return False
            
    except Exception as e:
        console.print(f"[bold red]💥 Unexpected error during video extraction: {str(e)}[/bold red]")
        return False


def convert_to_mov(input_path: str, output_path: str) -> bool:
    """
    Convert video to MOV format with H264 encoding.
    
    Args:
        input_path: Path to input video file
        output_path: Path for output MOV file
    Returns:
        Boolean indicating success/failure
    """
    console.print(f"[bold blue]🔄 Converting to MOV format[/bold blue]")
    
    try:
        cmd = [
            "ffmpeg", "-i", input_path, "-c:v", "libx264", 
            "-c:a", "aac", "-movflags", "+faststart", "-y", output_path
        ]
        console.print(f"[dim]🔧 Running: {' '.join(cmd)}[/dim]")
        
        # Stream FFmpeg output
        process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, 
                                 universal_newlines=True, bufsize=1)
        
        with console.status("[bold blue]Converting video format..."):
            for line in process.stdout:
                if line.strip():
                    logger.debug(f"[dim]📺 {line.strip()}[/dim]")
        
        process.wait()
        
        if process.returncode == 0:
            console.print(f"[bold green]✅ Video converted successfully[/bold green]")
            return True
        else:
            console.print(f"[bold red]❌ FFmpeg conversion failed with return code {process.returncode}[/bold red]")
            return False
            
    except Exception as e:
        console.print(f"[bold red]💥 Unexpected error during video conversion: {str(e)}[/bold red]")
        return False


def stabilize_video(input_path: str, output_path: str) -> bool:
    """
    Stabilize video using VidStab library with ORB keypoint detection.
    
    Args:
        input_path: Path to input video file
        output_path: Path for output stabilized video
    Returns:
        Boolean indicating success/failure
    """
    console.print(f"[bold magenta]🎯 Stabilizing video: {Path(input_path).name}[/bold magenta]")
    console.print(f"[cyan]🔍 Method: ORB keypoint detection with inpainting[/cyan]")
    
    try:
        # Ensure tmp directory exists for frame storage
        temp_frames_dir = "tmp/frames"
        temp_mask_dir = "tmp/mask"
        os.makedirs(temp_frames_dir, exist_ok=True)
        os.makedirs(temp_mask_dir, exist_ok=True)
        
        # Initialize VidStab with ORB keypoint detection
        smoothing_window = 30
        stabilizer = VidStab(kp_method='ORB')
        
        # Get video properties for output
        vidcap = cv2.VideoCapture(input_path)
        fps = vidcap.get(cv2.CAP_PROP_FPS)
        total_frames = int(vidcap.get(cv2.CAP_PROP_FRAME_COUNT))
        
        console.print(f"[cyan]📹 Video info: {total_frames} frames at {fps} FPS[/cyan]")
        
        # Initialize video capture for frame-by-frame processing
        vidcap = cv2.VideoCapture(input_path)
        frame_count = 0
        saved_frame_count = 0
        
        frame_size = None
        while True:
            grabbed_frame, frame = vidcap.read()
            if frame_size is None and frame is not None:
                frame_size = frame.shape[:2]
            
            if frame is not None:
                # Perform any pre-processing of frame before stabilization here
                pass
            
            # Pass frame to stabilizer even if frame is None
            # stabilized_frame will be an all black frame until iteration smoothing_window
            stabilized_frame = stabilizer.stabilize_frame(input_frame=frame,
                                                        smoothing_window=smoothing_window)
            
            if stabilized_frame is None:
                # There are no more frames available to stabilize
                break
            
            mask = np.ones(frame_size, dtype=np.uint8) * 255
            if frame_count >= smoothing_window and stabilizer.transforms is not None:
                # The stabilized frame we just got corresponds to a transform from earlier
                # due to the smoothing window delay
                transform_index = frame_count - smoothing_window
                if transform_index < len(stabilizer.transforms):
                    transform = stabilizer.transforms[transform_index]
                    dx, dy, da = transform
                    da = -da
                    
                    # Apply the same transformation to the mask
                    # Create transformation matrix for translation and rotation
                    center = (frame_size[1] // 2, frame_size[0] // 2)  # (width//2, height//2)
                    rotation_matrix = cv2.getRotationMatrix2D(center, np.degrees(da), 1.0)
                    
                    # Add translation to the transformation matrix
                    rotation_matrix[0, 2] += dx
                    rotation_matrix[1, 2] += dy
                    
                    # Apply transformation to mask
                    transformed_mask = cv2.warpAffine(mask, rotation_matrix, (frame_size[1], frame_size[0]), 
                                                    flags=cv2.INTER_NEAREST, borderMode=cv2.BORDER_CONSTANT, 
                                                    borderValue=0)
                    
                    # Clip to initial image size (mask is already the right size)
                    h, w = frame_size
                    transformed_mask = transformed_mask[:h, :w]
                    
                    # Create inversion mask for inpainting (black areas need to be filled)
                    inpaint_mask = 255 - transformed_mask
                    
                    # Save masks with zero-padded numbering
                    transformed_mask_filename = f"{temp_mask_dir}/transformed_mask_{saved_frame_count:06d}.png"
                    inpaint_mask_filename = f"{temp_mask_dir}/inpaint_mask_{saved_frame_count:06d}.png"
                    cv2.imwrite(transformed_mask_filename, transformed_mask)
                    cv2.imwrite(inpaint_mask_filename, inpaint_mask)
                    
                    # Perform inpainting on the stabilized frame
                    inpainted_frame = cv2.inpaint(stabilized_frame, inpaint_mask, 3, cv2.INPAINT_TELEA)
                    
                    # Save inpainted frame with zero-padded numbering
                    frame_filename = f"{temp_frames_dir}/frame_{saved_frame_count:06d}.png"
                    cv2.imwrite(frame_filename, inpainted_frame)
                    saved_frame_count += 1
                    
                    if saved_frame_count % 30 == 0:  # Progress update every 30 frames
                        console.print(f"[cyan]📸 Processed {saved_frame_count} frames[/cyan]")

            frame_count += 1

        # Clean up video capture
        vidcap.release()
        
        console.print(f"[green]✅ Generated {saved_frame_count} inpainted frames and masks[/green]")
        
        # Convert frames back to video using FFmpeg
        if saved_frame_count > 0:
            console.print(f"[cyan]🎬 Converting {saved_frame_count} frames to video...[/cyan]")
            
            # Create temp output with .avi extension first
            temp_output = output_path.replace('.mov', '_temp.avi')
            
            cmd = [
                "ffmpeg", "-framerate", str(fps), "-i", f"{temp_frames_dir}/frame_%06d.png",
                "-c:v", "libx264", "-preset", "medium", "-crf", "23", "-pix_fmt", "yuv420p",
                "-y", temp_output
            ]
            console.print(f"[dim]🔧 Running: {' '.join(cmd)}[/dim]")
            
            # Stream FFmpeg output
            process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, 
                                     universal_newlines=True, bufsize=1)
            
            with console.status("[bold blue]Creating video from frames..."):
                for line in process.stdout:
                    if line.strip():
                        logger.debug(f"[dim]📺 {line.strip()}[/dim]")
            
            process.wait()
            
            if process.returncode == 0:
                console.print("[green]✅ Successfully created video from frames[/green]")
                
                # If output should be MOV, convert using FFmpeg
                if output_path.endswith('.mov') and temp_output != output_path:
                    console.print(f"[cyan]🔄 Converting to MOV format...[/cyan]")
                    
                    cmd = [
                        "ffmpeg", "-i", temp_output, "-c:v", "libx264",
                        "-preset", "medium", "-crf", "23", "-c:a", "aac", "-y", output_path
                    ]
                    console.print(f"[dim]🔧 Running: {' '.join(cmd)}[/dim]")
                    
                    # Stream FFmpeg output
                    process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, 
                                             universal_newlines=True, bufsize=1)
                    
                    with console.status("[bold blue]Converting to MOV format..."):
                        for line in process.stdout:
                            if line.strip():
                                logger.debug(f"[dim]📺 {line.strip()}[/dim]")
                    
                    process.wait()
                    
                    if process.returncode == 0:
                        # Remove temp file and keep final output
                        os.remove(temp_output)
                        console.print("[green]✅ Successfully converted to MOV format[/green]")
                    else:
                        console.print(f"[yellow]⚠️  MOV conversion failed, keeping AVI format[/yellow]")
                        # Rename temp file to final output if conversion fails
                        os.rename(temp_output, output_path.replace('.mov', '.avi'))
                
                # Clean up temporary frame files
                console.print("[cyan]🧹 Cleaning up temporary frames...[/cyan]")
                for i in range(saved_frame_count):
                    frame_file = f"{temp_frames_dir}/frame_{i:06d}.png"
                    if os.path.exists(frame_file):
                        os.remove(frame_file)
                
                # Clean up temporary mask files
                console.print("[cyan]🧹 Cleaning up temporary masks...[/cyan]")
                for i in range(saved_frame_count):
                    transformed_mask_file = f"{temp_mask_dir}/transformed_mask_{i:06d}.png"
                    inpaint_mask_file = f"{temp_mask_dir}/inpaint_mask_{i:06d}.png"
                    if os.path.exists(transformed_mask_file):
                        os.remove(transformed_mask_file)
                    if os.path.exists(inpaint_mask_file):
                        os.remove(inpaint_mask_file)
                
                # Remove temp directories if empty
                try:
                    os.rmdir(temp_frames_dir)
                    os.rmdir(temp_mask_dir)
                except OSError:
                    pass  # Directory not empty or doesn't exist
                
                console.print(f"[bold green]✅ Video stabilized successfully: {Path(output_path).name}[/bold green]")
                return True
            else:
                console.print(f"[bold red]❌ FFmpeg frame-to-video conversion failed with return code {process.returncode}[/bold red]")
                return False
        else:
            console.print("[bold red]❌ No frames were generated for stabilization[/bold red]")
            return False
        
    except Exception as e:
        console.print(f"[bold red]❌ Video stabilization failed: {str(e)}[/bold red]")
        console.print("[yellow]💡 Check if input file exists and is a valid video format[/yellow]")
        return False


def ensure_directories_exist() -> None:
    """
    Ensure required directories exist for video processing.
    Creates tmp and assets/public directories if they don't exist.
    """
    directories = ["tmp", "assets/public"]
    console.print("[bold blue]📂 Checking directories...[/bold blue]")
    
    for directory in directories:
        if not os.path.exists(directory):
            console.print(f"[cyan]📁 Creating directory: {directory}[/cyan]")
            os.makedirs(directory, exist_ok=True)
        else:
            logger.debug(f"[dim]✅ Directory already exists: {directory}[/dim]")
    
    console.print("[bold green]✅ All directories ready[/bold green]")


def get_absolute_path(relative_path: str) -> str:
    """
    Convert relative path to absolute path.
    
    Args:
        relative_path: Relative file path
    Returns:
        Absolute file path
    """
    absolute_path = os.path.abspath(relative_path)
    logger.debug(f"📍 Converted {relative_path} to absolute path: {absolute_path}")
    return absolute_path


def cleanup_temp_files(*file_paths: str) -> None:
    """
    Clean up temporary files after processing.
    
    Args:
        *file_paths: Variable number of file paths to delete
    """
    console.print(f"[bold yellow]🧹 Cleaning up {len(file_paths)} temporary files...[/bold yellow]")
    
    for file_path in file_paths:
        if os.path.exists(file_path):
            try:
                os.remove(file_path)
                logger.debug(f"[dim]🗑️  Deleted: {Path(file_path).name}[/dim]")
            except Exception as e:
                logger.warning(f"[yellow]⚠️  Failed to delete {Path(file_path).name}: {str(e)}[/yellow]")
        else:
            logger.debug(f"[dim]⏭️  File doesn't exist (already cleaned?): {Path(file_path).name}[/dim]")
    
    console.print("[bold green]✅ Cleanup completed[/bold green]")


def convert_video_to_24fps(input_path: str, output_path: str) -> bool:
    """Convert a video to 24 FPS using FFmpeg."""
    console.print(f"[bold cyan]🔄 Converting {Path(input_path).name} to 24 FPS[/bold cyan]")
    try:
        cmd = [
            "ffmpeg", "-i", input_path, "-r", "24",
            "-c:v", "libx264", "-c:a", "aac", "-y", output_path
        ]
        console.print(f"[dim]🔧 Running: {' '.join(cmd)}[/dim]")

        process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                                 universal_newlines=True, bufsize=1)

        with console.status("[bold green]Converting to 24 FPS..."):
            for line in process.stdout:
                if line.strip():
                    logger.debug(f"[dim]📺 {line.strip()}[/dim]")

        process.wait()

        if process.returncode == 0:
            console.print(f"[bold green]✅ Video converted to 24 FPS successfully[/bold green]")
            return True
        else:
            console.print(f"[bold red]❌ FFmpeg 24 FPS conversion failed with return code {process.returncode}[/bold red]")
            return False

    except Exception as e:
        console.print(f"[bold red]💥 Unexpected error during 24 FPS conversion: {str(e)}[/bold red]")
        return False
