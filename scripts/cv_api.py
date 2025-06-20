import os
from pathlib import Path
from typing import Dict, Any
from pydantic import BaseModel
import torch
import torch.nn.functional as F
import numpy as np

from fastapi import APIRouter, UploadFile, File, HTTPException
from PIL import Image

from models.image import get_super_resolution, image_classification
from thefuzz import fuzz
from data_models import (
    ImageRequest,
    ColorTransferRequest,
    SuperResolutionResponse,
    BackgroundRemovalResponse,
    ColorTransferResponse,
    PortraitEffectResponse
)
from utils.image_helpers import (
    validate_uploaded_file,
    process_image_upload,
    generate_unique_filename,
    save_processed_image,
    create_portrait_effect,
    perform_color_transfer,
    save_processed_image_png,
    generate_bg_removal_filename,
    perform_background_removal,
    validate_image_path,
    load_image_from_path,
    generate_filename_from_path
)

router = APIRouter()

@router.post("/api/image/classify")
async def api_image_classify_min(request: ImageRequest):
    validate_image_path(request.image_path)
    pil_image = load_image_from_path(request.image_path)
    top_class = image_classification(pil_image)

    return {
        "top": top_class
    }

class FunRequest(BaseModel):
    """
    Request model for image classification endpoint.
    
    Attributes:
        image_path: Absolute path to the input image file
    """
    file_paths: list[str]
    query_string: str

@router.post("/api/image/classify-and-choose")
async def api_image_classify(request: FunRequest):
    """
    Classify image 
    """
    print("recv")
    if not request.file_paths or not isinstance(request.file_paths, list):
        raise HTTPException(status_code=400, detail="file_paths must be a non-empty list")
    if not request.query_string or not isinstance(request.query_string, str):
        raise HTTPException(status_code=400, detail="query_string must be a non-empty string")
    if len(request.file_paths) == 0:
        print("send back")
        raise HTTPException(status_code=400, detail="file_paths cannot be empty")
    
    request.file_paths = [Path(path).resolve().as_posix() for path in request.file_paths]
    if not request.file_paths:
        raise HTTPException(status_code=400, detail="No image paths provided")
    if not request.query_string:
        raise HTTPException(status_code=400, detail="Query string cannot be empty")


    # simply classify each image at each file path
    classes_returned = []
    for file_path in request.file_paths:
        if (validate_image_path(file_path, return_exception=False)):
            pil_image = load_image_from_path(file_path)
            top_class = image_classification(pil_image)
            classes_returned.append(top_class)
        else:
            classes_returned.append("INVALID_IMAGE_DO_NOT_USE_INVALID_IMAGE")
    
    # Enhanced Fuzzy Search System using thefuzz
    
    # Calculate fuzzy matching scores for each class against the query
    scores = []
    for class_name in classes_returned:
        # Use ratio for basic similarity
        ratio_score = fuzz.ratio(request.query_string.lower(), class_name.lower())
        # Use partial_ratio to find substrings
        partial_score = fuzz.partial_ratio(request.query_string.lower(), class_name.lower())
        # Use token_sort_ratio to handle word order differences
        token_score = fuzz.token_sort_ratio(request.query_string.lower(), class_name.lower())
        
        # Combine scores with weights
        combined_score = (ratio_score * 0.3) + (partial_score * 0.5) + (token_score * 0.2)
        scores.append(combined_score)
    
    # Find the best match
    # If no scores are available, return empty results
    if not scores:
        return {"results": []}
    
    # Create a list of (score, index) tuples
    scored_indices = [(score, idx) for idx, score in enumerate(scores)]
    
    # Sort by score in descending order
    scored_indices.sort(reverse=True)
    
    # Get top 3 (or fewer if less than 3 images were provided)
    top_k = min(3, len(scored_indices))
    top_results = []
    
    for i in range(top_k):
        score, idx = scored_indices[i]
        top_results.append({
            "file_path": request.file_paths[idx],
            "class": classes_returned[idx],
            "score": float(score)
        })
    
    print("top_results", top_results)
    return {
        "results": top_results
    }

@router.post("/api/image/super-resolution")
async def api_image_super_resolution(request: ImageRequest):
    """
    Apply super resolution enhancement to image specified by path.
    
    Accepts an image path, processes it using Real-ESRGAN x4plus model,
    and returns a download link to the enhanced image in assets/public directory.

    Args:
        request: ImageRequest containing the absolute path to the image file
        
    Returns:
        SuperResolutionResponse containing download link and absolute path to processed image
        
    Raises:
        HTTPException: If file validation or processing fails
    """
    try:
        # Validate image path and load image
        validate_image_path(request.image_path)
        pil_image = load_image_from_path(request.image_path)
        
        # Convert PIL image to numpy array for patch processing
        image_array = np.array(pil_image)
        
        # Apply super resolution using patch-based processing for large images
        if image_array.shape[0] > 512 or image_array.shape[1] > 512:
            # Use patch-based processing for large images
            enhanced_array = process_image_with_patches(image_array, patch_size=256, overlap=32)
        else:
            # Apply super resolution directly for smaller images
            enhanced_array = get_super_resolution(pil_image)

        # Generate unique filename and save processed image
        unique_filename = generate_filename_from_path(request.image_path, "sr")
        saved_path = save_processed_image(enhanced_array, unique_filename)
        
        # Construct public download URL and absolute path
        download_url = f"/api/assets/public/{unique_filename}"
        absolute_path = os.path.join(os.getcwd(), "assets", "public", unique_filename)
        
        response_data = SuperResolutionResponse(link=download_url, absolute_path=absolute_path)
        return {"success": True, "data": response_data}
        
    except HTTPException as e:
        return {"success": False, "error": e.detail}
    except Exception as e:
        return {"success": False, "error": f"Processing failed: {str(e)}"}


@router.post("/api/image/remove-bg")
async def api_image_background_removal(request: ImageRequest):
    """
    Remove background from image specified by path using RMBG-1.4 model.
    
    Accepts an image path, removes the background using state-of-the-art
    RMBG-1.4 model, and returns a download link to the PNG image with transparent
    background in assets/public directory.
    
    Args:
        request: ImageRequest containing the absolute path to the image file
        
    Returns:
        BackgroundRemovalResponse containing download link and absolute path to background-removed PNG image
        
    Raises:
        HTTPException: If file validation or processing fails
    """
    try:
        # Validate image path and load image
        validate_image_path(request.image_path)
        pil_image = load_image_from_path(request.image_path)
        
        # Apply background removal using models/image function
        rgba_array = perform_background_removal(pil_image)
        
        # Generate unique PNG filename and save processed image
        unique_filename = generate_filename_from_path(request.image_path, "bg_removed").replace('.jpg', '.png').replace('.jpeg', '.png')
        saved_path = save_processed_image_png(rgba_array, unique_filename)
        
        # Construct public download URL and absolute path
        download_url = f"/api/assets/public/{unique_filename}"
        absolute_path = os.path.join(os.getcwd(), "assets", "public", unique_filename)
        
        response_data = BackgroundRemovalResponse(link=download_url, absolute_path=absolute_path)
        return {"success": True, "data": response_data}
        
    except HTTPException as e:
        return {"success": False, "error": e.detail}
    except Exception as e:
        return {"success": False, "error": f"Background removal failed: {str(e)}"}


@router.post("/api/image/color-transfer")
async def api_image_color_transfer(request: ColorTransferRequest):
    """
    Apply color transfer from reference image to target image.
    
    Accepts paths to two images - a reference image providing the color palette
    and a target image to receive the color transfer. Uses LAB color space statistics
    matching to transfer color characteristics while preserving image structure.
    Returns download link to the processed image in assets/public directory.
    
    Args:
        request: ColorTransferRequest containing paths to reference and target image files
        
    Returns:
        ColorTransferResponse containing download link and absolute path to color-transferred image
        
    Raises:
        HTTPException: If file validation or processing fails
    """
    try:
        # Validate both image paths and load images
        validate_image_path(request.reference_image_path)
        validate_image_path(request.image_path)
        
        reference_image = load_image_from_path(request.reference_image_path)
        target_image = load_image_from_path(request.image_path)
        
        # Apply color transfer from reference to target
        transferred_array = perform_color_transfer(reference_image, target_image)
        
        # Generate unique filename and save processed image
        unique_filename = generate_filename_from_path(request.image_path, "color_transfer")
        saved_path = save_processed_image(transferred_array, unique_filename)
        
        # Construct public download URL and absolute path
        download_url = f"/api/assets/public/{unique_filename}"
        absolute_path = os.path.join(os.getcwd(), "assets", "public", unique_filename)
        
        response_data = ColorTransferResponse(link=download_url, absolute_path=absolute_path)
        return {"success": True, "data": response_data}
        
    except HTTPException as e:
        return {"success": False, "error": e.detail}
    except Exception as e:
        return {"success": False, "error": f"Color transfer processing failed: {str(e)}"}


@router.get("/api/image/image-generation")
def api_image_generate_image():
    """Placeholder endpoint for image generation functionality."""
    pass


@router.post("/api/image/portrait-effect")
async def api_image_portrait_effect(request: ImageRequest):
    """
    Apply portrait effect with depth-based background blur to image specified by path.
    
    Accepts an image path, generates depth map, and applies Gaussian blur
    to background areas (depth < 0.65) while keeping foreground subjects sharp.
    Returns download link to the processed image in assets/public directory.
    
    Args:
        request: ImageRequest containing the absolute path to the image file
        
    Returns:
        PortraitEffectResponse containing download link and absolute path to processed portrait image
        
    Raises:
        HTTPException: If file validation or processing fails
    """
    try:
        # Validate image path and load image
        validate_image_path(request.image_path)
        pil_image = load_image_from_path(request.image_path)
        
        # Apply portrait effect using depth-based blur
        portrait_array = create_portrait_effect(pil_image)
        
        # Generate unique filename and save processed image
        unique_filename = generate_filename_from_path(request.image_path, "portrait")
        saved_path = save_processed_image(portrait_array, unique_filename)
        
        # Construct public download URL and absolute path
        download_url = f"/api/assets/public/{unique_filename}"
        absolute_path = os.path.join(os.getcwd(), "assets", "public", unique_filename)
        
        response_data = PortraitEffectResponse(link=download_url, absolute_path=absolute_path)
        return {"success": True, "data": response_data}
        
    except HTTPException as e:
        return {"success": False, "error": e.detail}
    except Exception as e:
        return {"success": False, "error": f"Portrait effect processing failed: {str(e)}"}


def process_image_with_patches(image_array: np.ndarray, patch_size: int = 128, overlap: int = 0) -> np.ndarray:
    """
    Process image using patch-based approach with proper alignment using torch.nn.functional.unfold.
    
    Args:
        image_array: Input image as numpy array (H, W, C)
        patch_size: Size of each patch
        overlap: Overlap between patches for seamless blending
    
    Returns:
        Processed image array with proper alignment
    """
    # Drop alpha channel if present (PNG images)
    if len(image_array.shape) == 3 and image_array.shape[2] == 4:
        image_array = image_array[:, :, :3]  # Keep only RGB channels
    
    # Convert to torch tensor and add batch dimension
    if len(image_array.shape) == 3:
        tensor = torch.from_numpy(image_array).permute(2, 0, 1).unsqueeze(0).float()  # (1, C, H, W)
    else:
        tensor = torch.from_numpy(image_array).unsqueeze(0).unsqueeze(0).float()  # (1, 1, H, W)
    
    _, C, H, W = tensor.shape
    stride = patch_size - overlap
    
    # Calculate padding to ensure proper alignment
    pad_h = ((H - patch_size) // stride + 1) * stride + patch_size - H
    pad_w = ((W - patch_size) // stride + 1) * stride + patch_size - W
    pad_h = max(0, pad_h)
    pad_w = max(0, pad_w)
    
    # Apply padding for proper alignment
    if pad_h > 0 or pad_w > 0:
        tensor = F.pad(tensor, (0, pad_w, 0, pad_h), mode='reflect')
    
    # Extract patches using unfold
    patches = F.unfold(tensor, kernel_size=patch_size, stride=stride)  # (1, C*patch_size*patch_size, num_patches)
    patches = patches.transpose(1, 2)  # (1, num_patches, C*patch_size*patch_size)
    patches = patches.reshape(-1, C, patch_size, patch_size)  # (num_patches, C, patch_size, patch_size)
    
    # Process each patch with super resolution
    processed_patches = []
    for i in range(patches.shape[0]):
        # Convert patch tensor back to PIL Image for get_super_resolution
        patch_np = patches[i].permute(1, 2, 0).numpy().astype(np.uint8)
        patch_pil = Image.fromarray(patch_np)
        
        # Apply super resolution to this patch
        enhanced_patch = get_super_resolution(patch_pil)
        
        # Convert back to tensor and add to list
        enhanced_tensor = torch.from_numpy(enhanced_patch).permute(2, 0, 1).float()
        processed_patches.append(enhanced_tensor)
    
    # Stack processed patches
    processed_patches = torch.stack(processed_patches)  # (num_patches, C, patch_size*4, patch_size*4)
    
    # Update dimensions for super resolution (4x upscaling)
    sr_patch_size = patch_size * 4
    sr_stride = stride * 4
    sr_H, sr_W = H * 4, W * 4
    sr_pad_h, sr_pad_w = pad_h * 4, pad_w * 4
    
    # Reconstruct image using fold with proper overlap handling
    patches_flat = processed_patches.reshape(1, -1, C * sr_patch_size * sr_patch_size).transpose(1, 2)
    
    # Calculate output dimensions
    out_h = sr_H + sr_pad_h
    out_w = sr_W + sr_pad_w
    
    # Reconstruct using fold
    reconstructed = F.fold(patches_flat, output_size=(out_h, out_w), 
                          kernel_size=sr_patch_size, stride=sr_stride)
    
    # Create normalization tensor for proper blending
    ones = torch.ones_like(patches_flat)
    norm_map = F.fold(ones, output_size=(out_h, out_w), 
                     kernel_size=sr_patch_size, stride=sr_stride)
    
    # Normalize to handle overlaps
    reconstructed = reconstructed / norm_map
    
    # Remove padding and convert back to numpy
    if sr_pad_h > 0 or sr_pad_w > 0:
        reconstructed = reconstructed[:, :, :sr_H, :sr_W]
    
    # Convert back to numpy array
    if C == 1:
        result = reconstructed.squeeze().numpy()
    else:
        result = reconstructed.squeeze(0).permute(1, 2, 0).numpy()
    
    return result.astype(np.uint8)
