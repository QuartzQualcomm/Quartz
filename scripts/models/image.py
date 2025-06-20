#!/usr/bin/env python3
"""
Image processing models for computer vision tasks.

This module provides implementations for various image processing tasks including:
- Depth estimation (MiDaS from Qualcomm AI Hub)
- Super resolution (Real-ESRGAN x4plus)
- Background/object segmentation (RMBG-1.4 from BRIA AI, YOLOv8)
- Background removal (RMBG-1.4 state-of-the-art model)
- Inpainting (LaMa dilated from Qualcomm AI Hub)
- Image generation (Stable Diffusion 2.1)
- Image classification

All functions are implemented with modular design and proper type hints.

Installation requirements:
- qai-hub-models[lama-dilated] for LaMa inpainting model
"""

import argparse
import sys
from pathlib import Path
from typing import Union, Tuple, List, Optional, Dict, Any
import warnings
import yaml

import numpy as np
from PIL import Image
import torch
import cv2
from transformers import pipeline
from ultralytics import YOLO
import torchvision.transforms as transforms
from rich.console import Console
from rich.panel import Panel
from rich.text import Text
import qai_hub as hub
import os
import onnxruntime

# Suppress warnings for cleaner output
warnings.filterwarnings("ignore", category=UserWarning)
warnings.filterwarnings("ignore", category=FutureWarning)

# Initialize Rich console
console = Console()

# Model placeholders
MIDAS_MODEL = None
ESRGAN_MODEL = None
SAM_MODEL = None
RMBG_MODEL = None
LAMA_MODEL = None
STABLE_DIFFUSION_MODEL = None
YOLO_MODEL = None
CLASSIFICATION_MODEL = None

# Type aliases for better readability
ImageType = Union[Image.Image, np.ndarray]
ImageArray = np.ndarray

# Global model cache
MODELS = {
    "midas": MIDAS_MODEL,
    "esrgan": ESRGAN_MODEL,
    "sam": SAM_MODEL,
    "rmbg": RMBG_MODEL,
    "lama": LAMA_MODEL,
    "stable_diffusion": STABLE_DIFFUSION_MODEL,
    "yolo": YOLO_MODEL,
    "classification": CLASSIFICATION_MODEL
}

# Load configuration from config.yaml
def load_config() -> Dict[str, Any]:
    """Load configuration from config.yaml file."""
    config_path = Path("config.yaml")
    if config_path.exists():
        with open(config_path, 'r') as f:
            return yaml.safe_load(f)
    else:
        # Return default config if file doesn't exist
        return {
            "device": "cpu",
            "image": {
                "portrait_effect": {
                    "depth_threshold": 0.65,
                    "blur_kernel": 8
                },
                "super_resolution": {
                    "target_size": 128,
                    "scale_factor": 1.5,
                    "upscale_factor": 4
                },
                "background_removal": {
                    "confidence_threshold": 0.5,
                    "use_fp16": True
                }
            }
        }

# Load config once at module level
CONFIG = load_config()


def load_all_models():
    """
    Load all computer vision models into memory.
    This function is intended to be called at application startup.
    """
    # Check for QAI Hub API token
    try:
        hub.get_api_token()
    except Exception:
        print("\nQualcomm AI Hub API token not found.")
        print("Please configure it by running: 'qai-hub configure --api_token YOUR_API_TOKEN'")
        print("You can obtain a token from: https://aihub.qualcomm.com/account/settings#api-token\n")
        # Decide if you want to exit or continue without NPU acceleration
        # For now, we'll just print a warning and continue.
        pass

    global MODELS
    if not MODELS["sam"]:
        MODELS["sam"] = _load_sam_model()

    console.print("[bold yellow]Initializing and loading all computer vision models...[/bold yellow]")

    try:
        console.print("[cyan]Loading MiDaS (depth estimation) model...[/cyan]")
        MODELS["midas"] = _load_midas_model()
    except Exception as e:
        console.print(f"[bold red]Failed to load MiDaS model: {e}[/bold red]")

    try:
        console.print("[cyan]Loading Real-ESRGAN (super resolution) model...[/cyan]")
        MODELS["esrgan"] = _load_esrgan_model()
    except Exception as e:
        console.print(f"[bold red]Failed to load Real-ESRGAN model: {e}[/bold red]")
    
    try:
        console.print("[cyan]Loading RMBG-1.4 (background removal) model...[/cyan]")
        MODELS["rmbg"] = _load_rmbg_model()
    except Exception as e:
        console.print(f"[bold red]Failed to load RMBG-1.4 model: {e}[/bold red]")

    try:
        console.print("[cyan]Loading LaMa (inpainting) model...[/cyan]")
        MODELS["lama"] = _load_lama_model()
    except Exception as e:
        console.print(f"[bold red]Failed to load LaMa model: {e}[/bold red]")

    try:
        console.print("[cyan]Loading Stable Diffusion (image generation) model...[/cyan]")
        MODELS["stable_diffusion"] = _load_stable_diffusion_model()
    except Exception as e:
        console.print(f"[bold red]Failed to load Stable Diffusion model: {e}[/bold red]")

    try:
        console.print("[cyan]Loading YOLOv8 (object segmentation) model...[/cyan]")
        MODELS["yolo"] = _load_yolo_model()
    except Exception as e:
        console.print(f"[bold red]Failed to load YOLOv8 model: {e}[/bold red]")

    try:
        console.print("[cyan]Loading ViT (image classification) model...[/cyan]")
        MODELS["classification"] = _load_classification_model()
    except Exception as e:
        console.print(f"[bold red]Failed to load ViT model: {e}[/bold red]")

    console.print("[bold green]All computer vision models have been loaded and are ready.[/bold green]")


def _apply_gradient(text: Text, start_hex: str, end_hex: str):
    """Apply a gradient effect to Rich Text."""
    # Parse hex colors manually
    start_r = int(start_hex[1:3], 16)
    start_g = int(start_hex[3:5], 16)
    start_b = int(start_hex[5:7], 16)
    
    end_r = int(end_hex[1:3], 16)
    end_g = int(end_hex[3:5], 16)
    end_b = int(end_hex[5:7], 16)
    
    for i in range(len(text)):
        blend = i / (len(text) - 1) if len(text) > 1 else 0.5
        r = int(start_r * (1 - blend) + end_r * blend)
        g = int(start_g * (1 - blend) + end_g * blend)
        b = int(start_b * (1 - blend) + end_b * blend)
        text.stylize(f"rgb({r},{g},{b})", i, i + 1)


def _validate_image_input(img: ImageType) -> Image.Image:
    """Validate and convert image input to PIL Image format."""
    if isinstance(img, np.ndarray):
        return Image.fromarray(img)
    elif isinstance(img, Image.Image):
        return img
    else:
        raise TypeError(f"Unsupported image type: {type(img)}")


def _load_midas_model():
    """Load MiDaS depth estimation model from Qualcomm AI Hub."""
    from qai_hub_models.models.midas import Model
    return Model.from_pretrained()


def _prepare_midas_input(model, img: Image.Image):
    """Prepare input tensor for MiDaS model."""
    # Get expected input size (256x256 for MiDaS)
    resized_img = img.resize((256, 256))
    # Convert to tensor format expected by the model
    img_tensor = transforms.ToTensor()(resized_img).unsqueeze(0)
    return img_tensor


def _process_midas_output(output_data, original_size):
    """Process MiDaS model output to depth map."""
    # Convert tensor to numpy array
    depth_map = output_data.squeeze().detach().cpu().numpy()
    # Normalize depth values
    depth_map = (depth_map - depth_map.min()) / (depth_map.max() - depth_map.min())
    # Resize to original dimensions
    return cv2.resize(depth_map, original_size)


def _run_midas_inference(model, input_data):
    """Run inference on MiDaS model."""
    with torch.no_grad():
        output = model(input_data)
    return output


class ONNXSuperResolutionWrapper:
    """A wrapper for a local ONNX ESRGAN model to make it callable like a PyTorch model."""

    def __init__(self, model_path: str):
        print(f"Loading local ONNX ESRGAN model from: {model_path}")
        if not os.path.exists(model_path):
            raise FileNotFoundError(f"The specified model file does not exist: {model_path}")

        provider_options = [{"backend_path": "QnnHtp.dll", "htp_performance_mode": "burst"}]
        self.session = onnxruntime.InferenceSession(
            model_path,
            providers=["QNNExecutionProvider"],
            provider_options=provider_options,
        )
        self.input_name = self.session.get_inputs()[0].name
        self.output_name = self.session.get_outputs()[0].name
        print("ONNX ESRGAN model loaded successfully with NPU.")

    def __call__(self, input_tensor: torch.Tensor) -> torch.Tensor:
        """Runs inference on the ONNX model."""
        input_feed = {self.input_name: input_tensor.cpu().numpy()}
        result = self.session.run([self.output_name], input_feed)
        return torch.from_numpy(result[0])


def _load_esrgan_model():
    """
    Load a locally compiled Real-ESRGAN super resolution model for the NPU.
    
    NOTE: This function expects a pre-compiled ONNX model located at the path 
    specified in `model_path`.
    """
    # Please place your compiled ONNX model at this path or update the path accordingly.
    model_path = "C:\\Users\\Qualcomm\\Desktop\\dev\\Quartz\\scripts\\models\\npu\\esrgan.onnx"
    
    try:
        return ONNXSuperResolutionWrapper(model_path)
    except FileNotFoundError as e:
        console.print(f"[bold red]Error: {e}[/bold red]")
        console.print(f"[bold yellow]Please place your compiled ESRGAN NPU model at '{model_path}' or update the path in `scripts/models/image.py`.[/bold yellow]")
        return None
    except Exception as e:
        console.print(f"[bold red]Failed to load local ONNX model: {e}[/bold red]")
        console.print("[bold yellow]Ensure ONNX Runtime and the Qualcomm AI Engine Direct SDK are correctly installed.[/bold yellow]")
        return None


def _load_sam_model():
    """Load SAM segmentation model from HuggingFace."""
    return pipeline("mask-generation", model="facebook/sam-vit-base")


def _load_rmbg_model():
    """Load RMBG-1.4 background removal model from BRIA AI."""
    device = CONFIG.get("device", "cpu")
    use_fp16 = CONFIG.get("image", {}).get("background_removal", {}).get("use_fp16", True)
    
    # Check device availability and raise error if not available
    if device == "cuda" and not torch.cuda.is_available():
        raise RuntimeError("CUDA device requested but not available")
    elif device == "mps" and not torch.backends.mps.is_available():
        raise RuntimeError("MPS device requested but not available")
    
    # For MPS, disable fp16 to avoid precision issues
    if device == "mps":
        torch_dtype = torch.float32
        console.print("[yellow]Using fp32 on MPS to avoid precision issues[/yellow]")
    elif use_fp16 and device == "cuda":
        torch_dtype = torch.float16
    else:
        torch_dtype = torch.float32
    
    console.print(f"[cyan]Loading RMBG-1.4 on device: {device} with dtype: {torch_dtype}[/cyan]")
    
    return pipeline(
        "image-segmentation", 
        model="briaai/RMBG-1.4", 
        trust_remote_code=True,
        device=device,
        torch_dtype=torch_dtype
    )


def _process_rmbg_output(pillow_mask, original_size):
    """Process RMBG model output to segmentation mask."""
    # Get confidence threshold from config
    confidence_threshold = CONFIG.get("image", {}).get("background_removal", {}).get("confidence_threshold", 0.5)
    threshold_value = int(confidence_threshold * 255)
    
    # Convert PIL mask to numpy array
    mask_array = np.array(pillow_mask)
    
    # Convert to binary mask (1 for foreground, 0 for background)
    if len(mask_array.shape) == 3:
        # If RGB mask, convert to grayscale
        mask_array = cv2.cvtColor(mask_array, cv2.COLOR_RGB2GRAY)
    
    # Apply configurable threshold
    binary_mask = (mask_array > threshold_value).astype(np.uint8)
    
    return binary_mask


def _load_lama_model():
    """Load LaMa dilated inpainting model from Qualcomm AI Hub."""
    try:
        from qai_hub_models.models.lama_dilated import Model
        return Model.from_pretrained()
    except ImportError as e:
        raise RuntimeError(f"Failed to import LaMa model from qai-hub-models. Make sure qai-hub-models[lama-dilated] is installed: {str(e)}")


def _load_stable_diffusion_model():
    """Load Stable Diffusion 2.1 model from HuggingFace."""
    from diffusers import StableDiffusionPipeline
    device = CONFIG.get("device", "cpu")
    model_id = "stabilityai/stable-diffusion-2-1"
    
    # Check device availability and fallback appropriately
    if device == "cuda" and not torch.cuda.is_available():
        device = "cpu"
        console.print("[yellow]CUDA not available, using CPU instead[/yellow]")
    elif device == "mps" and not torch.backends.mps.is_available():
        device = "cpu"
        console.print("[yellow]MPS not available, using CPU instead[/yellow]")
    
    # Determine appropriate dtype based on device
    if device == "cuda":
        torch_dtype = torch.float16
    elif device == "mps":
        torch_dtype = torch.float16  # MPS supports float16
    else:
        torch_dtype = torch.float32
    
    console.print(f"[cyan]Loading Stable Diffusion 2.1 on device: {device}[/cyan]")
    
    pipe = StableDiffusionPipeline.from_pretrained(
        model_id,
        torch_dtype=torch_dtype,
        safety_checker=None,
        requires_safety_checker=False
    )
    pipe = pipe.to(device)
    
    # Enable memory efficient attention if available
    if hasattr(pipe.unet, "set_attn_processor"):
        try:
            from diffusers.models.attention_processor import AttnProcessor2_0
            pipe.unet.set_attn_processor(AttnProcessor2_0())
        except ImportError:
            pass
    
    # Enable memory efficient settings for MPS
    if device == "mps":
        pipe.enable_attention_slicing()
    
    return pipe


def _load_yolo_model() -> YOLO:
    """Load YOLOv8 segmentation model from Ultralytics."""
    return YOLO('yolov8n-seg.pt')


def _load_classification_model():
    """Load image classification model from HuggingFace."""
    return pipeline("image-classification", model="google/vit-base-patch16-224")


def _calculate_tile_size(image_size: Tuple[int, int], *, target_size: int = 128, scale_factor = 1.5) -> Tuple[int, int]:
    """Calculate optimal tile dimensions for super resolution processing."""
    width, height = image_size 
    
    if max(width, height) <= target_size:
        return (1, 1)
    elif max(width, height) <= target_size * scale_factor:
        return (1, 1)
    else:
        tiles_x = int(np.ceil((width / target_size) - 0.1))
        tiles_y = int(np.ceil((height / target_size)-0.1))
        return (tiles_x, tiles_y)


def _split_image_for_processing(img: Image.Image, tiles: Tuple[int, int]) -> List[Image.Image]:
    """Split image into tiles for processing."""
    tiles_x, tiles_y = tiles
    width, height = img.size
    tile_width = width // tiles_x
    tile_height = height // tiles_y
    
    image_tiles = []
    for y in range(tiles_y):
        for x in range(tiles_x):
            left = x * tile_width
            top = y * tile_height
            right = min((x + 1) * tile_width, width)
            bottom = min((y + 1) * tile_height, height)
            tile = img.crop((left, top, right, bottom))
            image_tiles.append(tile)
    
    return image_tiles


def _merge_processed_tiles(tiles: List[np.ndarray], original_size: Tuple[int, int], 
                          tile_dims: Tuple[int, int], upscale_factor: int = 4) -> np.ndarray:
    """Merge processed tiles back into single image."""
    tiles_x, tiles_y = tile_dims
    width, height = original_size
    
    # Calculate output dimensions using configurable upscale factor
    output_width = width * upscale_factor
    output_height = height * upscale_factor
    
    merged = np.zeros((output_height, output_width, 3), dtype=np.uint8)
    tile_output_width = output_width // tiles_x
    tile_output_height = output_height // tiles_y
    
    for i, tile in enumerate(tiles):
        y = i // tiles_x
        x = i % tiles_x
        start_y = y * tile_output_height
        start_x = x * tile_output_width
        end_y = min(start_y + tile.shape[0], output_height)
        end_x = min(start_x + tile.shape[1], output_width)
        
        merged[start_y:end_y, start_x:end_x] = tile[:end_y-start_y, :end_x-start_x]
    
    return merged


def get_depth_map(img: ImageType) -> np.ndarray:
    """
    Generate depth map from input image using MiDaS model from Qualcomm AI Hub.
    
    Args:
        img: Input image as PIL Image or numpy array
        
    Returns:
        Depth map as numpy array with normalized depth values (0-1)
        where higher values represent objects closer to the camera
        
    Raises:
        TypeError: If input image format is not supported
        RuntimeError: If depth estimation fails or model is not loaded
    """
    global MODELS
    if MODELS["midas"] is None:
        raise RuntimeError("MiDaS model is not loaded. Please ensure `load_all_models()` is called at startup.")

    try:
        # Validate and convert input to PIL Image
        pil_img = _validate_image_input(img)
        
        # Use the pre-loaded MiDaS model
        model = MODELS["midas"]
        
        # Prepare input for the model
        console.print("[cyan]Preparing input for MiDaS model...[/cyan]")
        input_data = _prepare_midas_input(model, pil_img)
        
        # Run inference
        console.print("[cyan]Running MiDaS inference...[/cyan]")
        output = _run_midas_inference(model, input_data)
        
        # Process output to get depth map
        console.print("[cyan]Processing depth map output...[/cyan]")
        depth_map = _process_midas_output(output, pil_img.size)
        
        console.print("[bold green]Depth estimation completed successfully.[/bold green]")
        return depth_map
    except ImportError as e:
        raise RuntimeError(f"Failed to import QAI Hub MiDaS model. Make sure qai-hub-models is installed: {str(e)}")
    except ValueError as e:
        raise RuntimeError(f"Invalid input for MiDaS model: {str(e)}")
    except Exception as e:
        raise RuntimeError(f"Depth estimation failed: {str(e)}")


def get_super_resolution(img: ImageType) -> np.ndarray:
    """
    Apply super resolution to input image using Real-ESRGAN x4plus model.
    
    For images smaller than target_size: scale to target_size and process
    For images larger than target_size * scale_factor: split into tiles and process
    For images between target_size and target_size * scale_factor: downscale to target_size and process
    
    Args:
        img: Input image as PIL Image or numpy array
        
    Returns:
        Super resolution image as numpy array (upscaled by upscale_factor)
        
    Raises:
        TypeError: If input image format is not supported
        RuntimeError: If super resolution processing fails or model is not loaded
    """
    global MODELS
    if MODELS["esrgan"] is None:
        raise RuntimeError("Real-ESRGAN model is not loaded. Please ensure `load_all_models()` is called at startup.")

    try:
        pil_img = _validate_image_input(img)
        original_size = pil_img.size
        
        # Load configuration values
        target_size = CONFIG["image"]["super_resolution"]["target_size"]
        scale_factor = CONFIG["image"]["super_resolution"]["scale_factor"]
        upscale_factor = CONFIG["image"]["super_resolution"]["upscale_factor"]
        
        # Calculate processing strategy based on image size
        tiles = _calculate_tile_size(original_size, target_size=target_size, scale_factor=scale_factor)
        
        console.print("[cyan]Running Real-ESRGAN inference for super resolution...[/cyan]")
        
        if tiles == (1, 1):
            # Single tile processing
            img_tensor = transforms.ToTensor()(pil_img).unsqueeze(0)
            with torch.no_grad():
                output = MODELS["esrgan"](img_tensor)

            if isinstance(output, torch.Tensor):
                output_array = output.squeeze(0).permute(1, 2, 0).cpu().numpy()
            else:
                output_array = output[0].squeeze(0).permute(1, 2, 0).cpu().numpy()

            upscaled_image = np.clip(output_array * 255, 0, 255).astype(np.uint8)
            return upscaled_image
        else:
            # Multi-tile processing
            image_tiles = _split_image_for_processing(pil_img, tiles)
            processed_tiles = []
            
            console.print(f"[cyan]Processing image in {len(image_tiles)} tiles...[/cyan]")
            for i, tile in enumerate(image_tiles):
                console.print(f"  - Processing tile {i+1}/{len(image_tiles)}", style="cyan")
                tile_tensor = transforms.ToTensor()(tile).unsqueeze(0)
                with torch.no_grad():
                    output = MODELS["esrgan"](tile_tensor)

                if isinstance(output, torch.Tensor):
                    output_array = output.squeeze(0).permute(1, 2, 0).cpu().numpy()
                else:
                    output_array = output[0].squeeze(0).permute(1, 2, 0).cpu().numpy()

                upscaled_tile = np.clip(output_array * 255, 0, 255).astype(np.uint8)
                processed_tiles.append(upscaled_tile)
            
            console.print("[bold green]Super resolution completed successfully.[/bold green]")
            merged_image = _merge_processed_tiles(processed_tiles, original_size, tiles, upscale_factor)
            return merged_image
            
    except Exception as e:
        raise RuntimeError(f"Super resolution failed: {str(e)}")


def background_segmentation(img: ImageType) -> np.ndarray:
    """
    Perform background segmentation using RMBG-1.4 model from BRIA AI.
    
    RMBG-1.4 is a state-of-the-art background removal model designed to effectively 
    separate foreground from background across various categories including objects, 
    people, animals, and text. It was trained on over 12,000 high-quality, manually 
    labeled images.
    
    Args:
        img: Input image as PIL Image or numpy array
        
    Returns:
        Segmentation mask as numpy array (1 for foreground, 0 for background)
        
    Raises:
        TypeError: If input image format is not supported  
        RuntimeError: If segmentation fails or model is not loaded
    """
    global MODELS
    if MODELS["rmbg"] is None:
        raise RuntimeError("RMBG-1.4 model is not loaded. Please ensure `load_all_models()` is called at startup.")

    try:
        pil_img = _validate_image_input(img)
        
        # Use the pre-loaded RMBG-1.4 model
        pipe = MODELS["rmbg"]
        
        # Run inference to get mask
        console.print("[cyan]Running RMBG-1.4 inference for background segmentation...[/cyan]")
        pillow_mask = pipe(pil_img, return_mask=True)
        
        # Process output to get segmentation mask
        console.print("[cyan]Processing segmentation mask...[/cyan]")
        mask = _process_rmbg_output(pillow_mask, pil_img.size)
        
        console.print("[bold green]Background segmentation completed successfully using RMBG-1.4.[/bold green]")
        return mask
        
    except Exception as e:
        raise RuntimeError(f"Background segmentation failed: {str(e)}")


def inpainting(img: ImageType, mask: np.ndarray) -> np.ndarray:
    """
    Perform image inpainting using LaMa dilated model from Qualcomm AI Hub.
    
    Args:
        img: Input image as PIL Image or numpy array
        mask: Binary mask (0 for areas to inpaint, 1 for areas to preserve)
        
    Returns:
        Inpainted image as numpy array
        
    Raises:
        TypeError: If input formats are not supported
        ValueError: If mask dimensions don't match image
        RuntimeError: If inpainting fails or model is not loaded
    """
    global MODELS
    if MODELS["lama"] is None:
        raise RuntimeError("LaMa model is not loaded. Please ensure `load_all_models()` is called at startup.")

    try:
        pil_img = _validate_image_input(img)
        img_array = np.array(pil_img)
        
        if img_array.shape[:2] != mask.shape[:2]:
            raise ValueError("Mask dimensions must match image dimensions")
        
        # Use the pre-loaded LaMa model
        model = MODELS["lama"]
        
        # Prepare inputs for LaMa model
        console.print("[cyan]Preparing inputs for LaMa model...[/cyan]")
        
        # Convert to RGB if necessary
        if pil_img.mode != 'RGB':
            pil_img = pil_img.convert('RGB')
        
        # Resize image to 512x512 (LaMa expected input size)
        original_size = pil_img.size
        resized_img = pil_img.resize((512, 512), Image.Resampling.LANCZOS)
        
        # Resize mask to match
        resized_mask = cv2.resize(mask.astype(np.uint8), (512, 512), interpolation=cv2.INTER_NEAREST)
        
        # Convert mask: LaMa expects 0 for areas to keep, 1 for areas to inpaint
        # Our input mask is 0 for areas to inpaint, 1 for areas to preserve
        # So we need to invert it
        lama_mask = (1 - resized_mask).astype(np.uint8) * 255
        
        # Convert to PIL Image for mask
        mask_pil = Image.fromarray(lama_mask, mode='L')
        
        # Prepare model inputs
        console.print("[cyan]Running LaMa dilated inference...[/cyan]")
        
        # The model expects image and mask inputs.
        # We need to construct tensors in the correct format.
        # This part is complex due to model-specific input requirements.
        # Let's retain the logic but remove the sample_inputs part for clarity.
        
        # Get the input specification
        input_spec = model.get_input_spec()
        
        # Convert PIL images to tensors in the format expected by the model
        import torch
        import torchvision.transforms as transforms
        
        # Transform for image: normalize to [0, 1] and convert to tensor
        img_transform = transforms.Compose([
            transforms.ToTensor(),
        ])
        
        # Transform for mask: convert to tensor
        mask_transform = transforms.Compose([
            transforms.ToTensor(),
        ])
        
        # Apply transforms
        img_tensor = img_transform(resized_img).unsqueeze(0)  # Add batch dimension
        mask_tensor = mask_transform(mask_pil).unsqueeze(0)   # Add batch dimension
        
        # Run inference
        with torch.no_grad():
            # The model expects image and mask inputs
            result = model(img_tensor, mask_tensor)
        
        # Process output
        console.print("[cyan]Processing inpainting result...[/cyan]")
        
        # Convert result tensor back to numpy array
        if isinstance(result, torch.Tensor):
            result_array = result.squeeze(0).permute(1, 2, 0).cpu().numpy()
        else:
            # If result is a tuple/list, take the first element
            result_array = result[0].squeeze(0).permute(1, 2, 0).cpu().numpy()
        
        # Denormalize from [0, 1] to [0, 255]
        result_array = np.clip(result_array * 255, 0, 255).astype(np.uint8)
        
        # Resize back to original dimensions
        result_pil = Image.fromarray(result_array)
        final_result = result_pil.resize(original_size, Image.Resampling.LANCZOS)
        
        console.print("[bold green]LaMa dilated inpainting completed successfully.[/bold green]")
        return np.array(final_result)
        
    except ImportError as e:
        console.print(f"[bold red]Error: LaMa model not available. {str(e)}[/bold red]")
        raise RuntimeError(f"LaMa dilated model is required for inpainting. Please install with: pip install 'qai-hub-models[lama-dilated]'. Error: {str(e)}")
        
    except Exception as e:
        console.print(f"[bold red]Error: Inpainting failed. {str(e)}[/bold red]")
        raise RuntimeError(f"Inpainting failed: {str(e)}")


def generate_image(prompt: str, negative_prompt: Optional[str] = None, 
                  num_inference_steps: int = 50, guidance_scale: float = 7.5,
                  width: int = 512, height: int = 512, seed: Optional[int] = None) -> np.ndarray:
    """
    Generate image from text prompt using Stable Diffusion 2.1.
    
    Args:
        prompt: Text description of desired image
        negative_prompt: Optional negative prompt to avoid certain features
        num_inference_steps: Number of denoising steps (default: 50)
        guidance_scale: How closely to follow the prompt (default: 7.5)
        width: Output image width (default: 512)
        height: Output image height (default: 512)
        seed: Optional random seed for reproducible results
        
    Returns:
        Generated image as numpy array
        
    Raises:
        ValueError: If prompt is empty or invalid
        RuntimeError: If image generation fails or model is not loaded
    """
    global MODELS
    if MODELS["stable_diffusion"] is None:
        raise RuntimeError("Stable Diffusion model is not loaded. Please ensure `load_all_models()` is called at startup.")

    try:
        if not prompt or not prompt.strip():
            raise ValueError("Prompt cannot be empty")
        
        pipe = MODELS["stable_diffusion"]
        
        # Set random seed if provided
        if seed is not None:
            torch.manual_seed(seed)
            np.random.seed(seed)
        
        console.print(f"[cyan]Generating image with prompt: '{prompt}'[/cyan]")
        console.print(f"[cyan]Parameters: steps={num_inference_steps}, guidance={guidance_scale}, size={width}x{height}[/cyan]")
        
        # Generate image
        with torch.no_grad():
            result = pipe(
                prompt=prompt,
                negative_prompt=negative_prompt,
                num_inference_steps=num_inference_steps,
                guidance_scale=guidance_scale,
                width=width,
                height=height,
                generator=torch.Generator().manual_seed(seed) if seed is not None else None
            )
        
        # Convert PIL image to numpy array
        generated_image = result.images[0]
        console.print("[bold green]Image generation completed successfully.[/bold green]")
        return np.array(generated_image)
        
    except Exception as e:
        raise RuntimeError(f"Image generation failed: {str(e)}")


def remove_background(img: ImageType, return_mask: bool = False) -> Union[np.ndarray, Image.Image]:
    """
    Remove background from images using RMBG-1.4 model from BRIA AI.
    
    This function uses the RMBG-1.4 model to segment the foreground from the background
    across various categories (objects, people, animals, text) and returns an image 
    with transparent background or the segmentation mask.
    
    Args:
        img: Input image as PIL Image or numpy array
        return_mask: If True, return the segmentation mask instead of the processed image
        
    Returns:
        If return_mask=False: Image with transparent background as numpy array (RGBA)
        If return_mask=True: Segmentation mask as numpy array (1 for foreground, 0 for background)
        
    Raises:
        TypeError: If input image format is not supported
        RuntimeError: If background removal fails or model is not loaded
    """
    global MODELS
    if MODELS["rmbg"] is None:
        raise RuntimeError("RMBG-1.4 model is not loaded. Please ensure `load_all_models()` is called at startup.")
        
    try:
        pil_img = _validate_image_input(img)
        
        if return_mask:
            # Get segmentation mask using RMBG-1.4
            console.print("[cyan]Generating segmentation mask for background removal...[/cyan]")
            mask = background_segmentation(pil_img)
            return mask
        
        # Use the pre-loaded RMBG-1.4 model
        pipe = MODELS["rmbg"]
        
        # Get image with background removed (applies mask automatically)
        console.print("[cyan]Running RMBG-1.4 inference for background removal...[/cyan]")
        no_bg_image = pipe(pil_img)  # Returns PIL image with transparent background
        
        console.print("[bold green]Background removal completed successfully using RMBG-1.4.[/bold green]")
        return np.array(no_bg_image)
        
    except Exception as e:
        raise RuntimeError(f"Background removal failed: {str(e)}")


def object_segmentation(img: ImageType) -> np.ndarray:
    """
    Perform object segmentation using YOLOv8 segmentation model.
    
    Args:
        img: Input image as PIL Image or numpy array
        
    Returns:
        Segmentation masks as numpy array with different values for each object
        
    Raises:
        TypeError: If input image format is not supported
        RuntimeError: If object segmentation fails or model is not loaded
    """
    global MODELS
    if MODELS["yolo"] is None:
        raise RuntimeError("YOLOv8 model is not loaded. Please ensure `load_all_models()` is called at startup.")

    try:
        pil_img = _validate_image_input(img)
        model = MODELS["yolo"]
        
        console.print("[cyan]Running YOLOv8 inference...[/cyan]")
        results = model(pil_img)
        
        # Extract segmentation masks
        console.print("[cyan]Processing segmentation masks...[/cyan]")
        if results[0].masks is not None:
            masks = results[0].masks.data.cpu().numpy()
            combined_mask = np.zeros(masks.shape[1:], dtype=np.uint8)
            
            for i, mask in enumerate(masks):
                combined_mask[mask > 0.5] = i + 1
            
            console.print(f"[bold green]Object segmentation completed successfully. Found {len(masks)} objects.[/bold green]")
            return combined_mask
        else:
            console.print("[yellow]No objects found in the image.[/yellow]")
            return np.zeros((*pil_img.size[::-1],), dtype=np.uint8)
            
    except Exception as e:
        raise RuntimeError(f"Object segmentation failed: {str(e)}")


def _convert_to_lab(img: np.ndarray) -> np.ndarray:
    """Convert BGR image to LAB color space."""
    return cv2.cvtColor(img, cv2.COLOR_BGR2LAB).astype("float32")


def _convert_to_bgr(img: np.ndarray) -> np.ndarray:
    """Convert LAB image back to BGR color space."""
    return cv2.cvtColor(img.astype("uint8"), cv2.COLOR_LAB2BGR)


def _compute_color_stats(img: np.ndarray) -> Tuple[float, float, float, float, float, float]:
    """Compute mean and standard deviation for each LAB channel."""
    l, a, b = cv2.split(img)
    return (l.mean(), l.std(), a.mean(), a.std(), b.mean(), b.std())


def _apply_color_mapping(target: np.ndarray, source_stats: Tuple[float, ...], 
                        target_stats: Tuple[float, ...]) -> np.ndarray:
    """Apply Reinhard color transfer mapping."""
    l_mean_src, l_std_src, a_mean_src, a_std_src, b_mean_src, b_std_src = source_stats
    l_mean_tar, l_std_tar, a_mean_tar, a_std_tar, b_mean_tar, b_std_tar = target_stats
    
    l, a, b = cv2.split(target)
    
    # Subtract target means, scale by std ratios, add source means
    l = (l_std_src / l_std_tar) * (l - l_mean_tar) + l_mean_src
    a = (a_std_src / a_std_tar) * (a - a_mean_tar) + a_mean_src
    b = (b_std_src / b_std_tar) * (b - b_mean_tar) + b_mean_src
    
    # Clip values and merge channels
    l = np.clip(l, 0, 255)
    a = np.clip(a, 0, 255)
    b = np.clip(b, 0, 255)
    
    return cv2.merge([l, a, b])


def color_transfer(target: ImageType, reference: ImageType) -> Image.Image:
    """
    Apply Reinhard color transfer from reference to target image.
    
    Uses the Reinhard et al. color transfer algorithm in LAB color space
    to transfer color characteristics from reference to target image.
    
    Args:
        target: Target image as PIL Image or numpy array
        reference: Reference image as PIL Image or numpy array
        
    Returns:
        Color-transferred image as PIL Image
        
    Raises:
        TypeError: If input image format is not supported
        RuntimeError: If color transfer fails or model is not loaded
    """
    global MODELS
    if MODELS["esrgan"] is None:
        raise RuntimeError("Real-ESRGAN model is not loaded. Please ensure `load_all_models()` is called at startup.")

    try:
        target_pil = _validate_image_input(target)
        reference_pil = _validate_image_input(reference)
        
        console.print("[cyan]Applying Reinhard color transfer...[/cyan]")
        
        # Convert PIL to numpy arrays in BGR format
        target_bgr = cv2.cvtColor(np.array(target_pil), cv2.COLOR_RGB2BGR)
        reference_bgr = cv2.cvtColor(np.array(reference_pil), cv2.COLOR_RGB2BGR)
        
        # Convert to LAB color space
        target_lab = _convert_to_lab(target_bgr)
        reference_lab = _convert_to_lab(reference_bgr)
        
        # Compute color statistics
        source_stats = _compute_color_stats(reference_lab)
        target_stats = _compute_color_stats(target_lab)
        
        # Apply color mapping
        result_lab = _apply_color_mapping(target_lab, source_stats, target_stats)
        
        # Convert back to BGR then RGB
        result_bgr = _convert_to_bgr(result_lab)
        result_rgb = cv2.cvtColor(result_bgr, cv2.COLOR_BGR2RGB)
        
        console.print("[bold green]Color transfer completed successfully.[/bold green]")
        return Image.fromarray(result_rgb)
        
    except Exception as e:
        raise RuntimeError(f"Color transfer failed: {str(e)}")


def image_classification(img: ImageType) -> str:
    """
    Classify input image using Vision Transformer model.
    
    Args:
        img: Input image as PIL Image or numpy array
        
    Returns:
        Classification result as string (top predicted class)
        
    Raises:
        TypeError: If input image format is not supported
        RuntimeError: If classification fails or model is not loaded
    """
    global MODELS
    if MODELS["classification"] is None:
        raise RuntimeError("Classification model is not loaded. Please ensure `load_all_models()` is called at startup.")

    try:
        pil_img = _validate_image_input(img)
        classifier = MODELS["classification"]
        
        console.print("[cyan]Running classification inference...[/cyan]")
        results = classifier(pil_img)
        print(results[0])
        top_result = results[0]['label'] if results else "unknown"
        console.print("[bold green]Image classification completed.[/bold green]")
        return top_result
        
    except Exception as e:
        raise RuntimeError(f"Image classification failed: {str(e)}")


def main() -> None:
    """
    Command line interface for image processing tasks.
    
    Examples:
        python models/image.py get_depth_map -i assets/test_image.jpg
        python models/image.py background_segmentation -i assets/test_image.jpg
        python models/image.py remove_background -i assets/photo.jpg
        python models/image.py remove_background -i assets/photo.jpg --return-mask
        python models/image.py inpainting -m assets/mask.png -i assets/test_image.jpg
        python models/image.py color_transfer -i assets/target.jpg -r assets/reference.jpg
        python models/image.py generate_image -p "a beautiful sunset over mountains"
        python models/image.py generate_image -p "a cute cat" -n "blurry, low quality" --steps 30 --width 768 --height 768
    """
    parser = argparse.ArgumentParser(
        description="A command-line tool for various image processing tasks.",
        formatter_class=argparse.RawTextHelpFormatter
    )
    parser.add_argument("task", choices=[
        "get_depth_map", "get_super_resolution", "background_segmentation",
        "remove_background", "inpainting", "generate_image", "object_segmentation", 
        "image_classification", "color_transfer"
    ], help="Image processing task to perform")
    
    parser.add_argument("-i", "--image", type=str, help="Input image path")
    parser.add_argument("-r", "--reference", type=str, help="Reference image path (for color_transfer)")
    parser.add_argument("-m", "--mask", type=str, help="Mask image path (for inpainting)")
    parser.add_argument("-p", "--prompt", type=str, help="Text prompt (for image generation)")
    parser.add_argument("-n", "--negative-prompt", type=str, help="Negative prompt (for image generation)")
    parser.add_argument("-o", "--output", type=str, default="output.png", help="Output path (default: output.png)")
    parser.add_argument("--steps", type=int, default=50, help="Number of inference steps (default: 50)")
    parser.add_argument("--guidance", type=float, default=7.5, help="Guidance scale (default: 7.5)")
    parser.add_argument("--width", type=int, default=512, help="Output width (default: 512)")
    parser.add_argument("--height", type=int, default=512, help="Output height (default: 512)")
    parser.add_argument("--seed", type=int, help="Random seed for reproducible results")
    parser.add_argument("--return-mask", action="store_true", help="Return segmentation mask instead of processed image (for remove_background)")
    
    args = parser.parse_args()
    
    title_text = "Image Processing AI System"
    title = Text(title_text, justify="center", style="bold")
    _apply_gradient(title, "#8A2BE2", "#4169E1")  # BlueViolet to RoyalBlue
    console.print(Panel(title, border_style="green", expand=False))

    # Load all models for standalone script execution
    load_all_models()

    try:
        if args.task == "generate_image":
            if not args.prompt:
                console.print("[bold red]Error: --prompt is required for the 'generate_image' task.[/bold red]")
                sys.exit(1)
            result = generate_image(
                prompt=args.prompt,
                negative_prompt=args.negative_prompt,
                num_inference_steps=args.steps,
                guidance_scale=args.guidance,
                width=args.width,
                height=args.height,
                seed=args.seed
            )
            
        elif args.task == "inpainting":
            if not args.image or not args.mask:
                console.print("[bold red]Error: --image and --mask are required for the 'inpainting' task.[/bold red]")
                sys.exit(1)
            img = Image.open(args.image)
            mask = np.array(Image.open(args.mask).convert('L')) / 255
            result = inpainting(img, mask)
            
        elif args.task == "color_transfer":
            if not args.image or not args.reference:
                console.print("[bold red]Error: --image and --reference are required for the 'color_transfer' task.[/bold red]")
                sys.exit(1)
            target_img = Image.open(args.image)
            reference_img = Image.open(args.reference)
            result = color_transfer(target_img, reference_img)
            
        else:
            if not args.image:
                console.print(f"[bold red]Error: --image is required for the '{args.task}' task.[/bold red]")
                sys.exit(1)
            img = Image.open(args.image)
            
            task_map = {
                "get_depth_map": get_depth_map,
                "get_super_resolution": get_super_resolution,
                "background_segmentation": background_segmentation,
                "object_segmentation": object_segmentation,
                "image_classification": image_classification,
            }
            
            # Special handling for remove_background with return_mask option
            if args.task == "remove_background":
                result = remove_background(img, return_mask=args.return_mask)
            elif args.task in task_map:
                result = task_map[args.task](img)
            else:
                # This path should not be reached due to argparse `choices`
                console.print(f"[bold red]Error: Unknown task '{args.task}'[/bold red]")
                sys.exit(1)

            if args.task == "image_classification":
                console.print(Panel(f"[bold green]Classification Result: [white]{result}[/white][/bold green]", 
                                    title="[yellow]Result[/yellow]", border_style="magenta"))
                return
        
        # Save result
        console.print(f"[cyan]Saving result to [bold]'{args.output}'[/bold]...[/cyan]")
        
        if isinstance(result, Image.Image):
            # PIL Image - save directly
            result.save(args.output)
        elif isinstance(result, np.ndarray):
            # Numpy array - convert to PIL and save
            if result.dtype != np.uint8:
                # Normalize non-uint8 arrays (e.g., depth maps)
                if result.max() > result.min():
                    result = ((result - result.min()) / (result.max() - result.min()) * 255).astype(np.uint8)
                else:
                    result = np.zeros_like(result, dtype=np.uint8)
            
            if len(result.shape) == 2:
                Image.fromarray(result, mode='L').save(args.output)
            elif len(result.shape) == 3 and result.shape[2] == 4:
                # RGBA image (e.g., from remove_background)
                # Force PNG format for transparency support
                output_path = args.output
                if not output_path.lower().endswith('.png'):
                    output_path = output_path.rsplit('.', 1)[0] + '.png'
                    console.print(f"[yellow]Changing output format to PNG for transparency support: {output_path}[/yellow]")
                Image.fromarray(result, mode='RGBA').save(output_path)
            else:
                Image.fromarray(result).save(args.output)
        
        console.print(Panel(f"[bold green]Output successfully saved to [white]'{args.output}'[/white][/bold green]",
                            title="[yellow]Success[/yellow]", border_style="green"))
        
    except FileNotFoundError as e:
        console.print(f"[bold red]Error: Input file not found - {e}[/bold red]")
        sys.exit(1)
    except Exception as e:
        console.print(f"[bold red]An unexpected error occurred: {e}[/bold red]")
        console.print_exception(show_locals=True)
        sys.exit(1)


if __name__ == "__main__":
    main()