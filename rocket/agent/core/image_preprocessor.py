"""Image preprocessing for API optimization.

Reduces image size to prevent 522 timeout errors.
"""

from __future__ import annotations

import io
from pathlib import Path
from typing import Optional, Tuple

from PIL import Image


# Configuration
MAX_DIMENSION = 1024  # Max width or height
MAX_FILE_SIZE = 1 * 1024 * 1024  # 1MB
JPEG_QUALITY = 70


def preprocess_image_bytes(image_bytes: bytes) -> Tuple[bytes, dict]:
    """
    Preprocess image bytes for API call.
    
    - Resize if larger than MAX_DIMENSION
    - Convert to JPEG
    - Compress to reduce file size
    
    Returns: (processed_bytes, stats)
    """
    stats = {
        "original_size": len(image_bytes),
        "original_format": None,
        "original_dimensions": None,
        "processed_size": None,
        "processed_dimensions": None,
        "actions": [],
    }
    
    print(f"\n========== [IMAGE PREPROCESSING] ==========")
    print(f"[ORIGINAL SIZE] {len(image_bytes)} bytes ({len(image_bytes)/1024:.1f} KB)")
    
    try:
        # Open image
        img = Image.open(io.BytesIO(image_bytes))
        stats["original_format"] = img.format
        stats["original_dimensions"] = img.size
        
        print(f"[ORIGINAL FORMAT] {img.format}")
        print(f"[ORIGINAL DIMENSIONS] {img.size[0]}x{img.size[1]}")
        
        # Convert to RGB (remove alpha channel)
        if img.mode in ("RGBA", "P", "LA"):
            img = img.convert("RGB")
            stats["actions"].append("convert_to_rgb")
        
        # Resize if too large
        width, height = img.size
        if width > MAX_DIMENSION or height > MAX_DIMENSION:
            # Calculate new size maintaining aspect ratio
            ratio = min(MAX_DIMENSION / width, MAX_DIMENSION / height)
            new_width = int(width * ratio)
            new_height = int(height * ratio)
            
            img = img.resize((new_width, new_height), Image.Resampling.LANCZOS)
            stats["actions"].append(f"resize_to_{new_width}x{new_height}")
            print(f"[RESIZED] {width}x{height} → {new_width}x{new_height}")
        
        # Save as JPEG with compression
        output = io.BytesIO()
        img.save(output, format="JPEG", quality=JPEG_QUALITY, optimize=True)
        processed_bytes = output.getvalue()
        
        stats["processed_size"] = len(processed_bytes)
        stats["processed_dimensions"] = img.size
        stats["actions"].append(f"compress_jpeg_q{JPEG_QUALITY}")
        
        # Further compress if still too large
        quality = JPEG_QUALITY
        while len(processed_bytes) > MAX_FILE_SIZE and quality > 30:
            quality -= 10
            output = io.BytesIO()
            img.save(output, format="JPEG", quality=quality, optimize=True)
            processed_bytes = output.getvalue()
            stats["actions"].append(f"recompress_q{quality}")
            print(f"[RECOMPRESSED] quality={quality}, size={len(processed_bytes)} bytes")
        
        print(f"[PROCESSED SIZE] {len(processed_bytes)} bytes ({len(processed_bytes)/1024:.1f} KB)")
        print(f"[SIZE REDUCTION] {(1 - len(processed_bytes)/len(image_bytes))*100:.1f}%")
        
        return processed_bytes, stats
        
    except Exception as e:
        print(f"[PREPROCESSING ERROR] {e}")
        stats["error"] = str(e)
        return image_bytes, stats  # Return original on error


def preprocess_image_file(image_path: Path) -> Tuple[bytes, dict]:
    """Preprocess image file for API call."""
    image_bytes = image_path.read_bytes()
    return preprocess_image_bytes(image_bytes)


def validate_image_dimensions(image_bytes: bytes) -> Tuple[bool, dict]:
    """
    Validate image dimensions.
    
    Returns: (is_valid, info)
    """
    try:
        img = Image.open(io.BytesIO(image_bytes))
        width, height = img.size
        
        info = {
            "width": width,
            "height": height,
            "format": img.format,
            "mode": img.mode,
            "size_bytes": len(image_bytes),
        }
        
        # Check if reasonable
        is_valid = (
            10 < width < 10000 and
            10 < height < 10000 and
            len(image_bytes) > 100  # Not empty
        )
        
        return is_valid, info
        
    except Exception as e:
        return False, {"error": str(e)}
