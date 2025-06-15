import os
import subprocess
import uuid
import logging
import cv2
import numpy as np
from typing import Tuple
import sys
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


def stabilize_video_ffmpeg(input_path: str, output_path: str) -> bool:
    """
    Stabilize video using FFmpeg's vidstabdetect and vidstabtransform filters.
    
    Args:
        input_path: Path to input video file
        output_path: Path for output stabilized video
    Returns:
        Boolean indicating success/failure
    """
    console.print(f"[bold magenta]🎯 Stabilizing video with FFmpeg: {Path(input_path).name}[/bold magenta]")
    
    try:
        # Step 1: Detect motion vectors
        transforms_path = "transforms.trf"
        detect_cmd = [
            "ffmpeg", "-i", input_path, "-vf", "vidstabdetect=stepsize=6:shakiness=5:accuracy=15:result=" + transforms_path,
            "-f", "null", "-"
        ]
        console.print("[cyan]🔍 Pass 1/2: Detecting motion vectors...[/cyan]")
        console.print(f"[dim]🔧 Running: {' '.join(detect_cmd)}[/dim]")
        
        detect_process = subprocess.Popen(detect_cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, universal_newlines=True)
        detect_stdout, detect_stderr = detect_process.communicate()

        if detect_process.returncode != 0:
            console.print(f"[bold red]❌ FFmpeg motion detection failed.[/bold red]")
            console.print(f"[dim]{detect_stderr}[/dim]")
            return False

        # Step 2: Apply stabilization transform
        transform_cmd = [
            "ffmpeg", "-i", input_path, "-vf", "vidstabtransform=input=" + transforms_path + ":zoom=0:smoothing=10",
            "-c:v", "libx264", "-preset", "medium", "-crf", "23", "-c:a", "copy", "-y", output_path
        ]
        console.print("[cyan]🔄 Pass 2/2: Applying stabilization transform...[/cyan]")
        console.print(f"[dim]🔧 Running: {' '.join(transform_cmd)}[/dim]")

        transform_process = subprocess.Popen(transform_cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, universal_newlines=True)
        transform_stdout, transform_stderr = transform_process.communicate()
        
        if transform_process.returncode != 0:
            console.print(f"[bold red]❌ FFmpeg stabilization failed.[/bold red]")
            console.print(f"[dim]{transform_stderr}[/dim]")
            return False
            
        console.print(f"[bold green]✅ Video stabilized successfully: {Path(output_path).name}[/bold green]")
        return True

    except Exception as e:
        console.print(f"[bold red]💥 Unexpected error during FFmpeg stabilization: {str(e)}[/bold red]")
        return False
    finally:
        # Clean up the transforms file
        if os.path.exists("transforms.trf"):
            os.remove("transforms.trf")


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
