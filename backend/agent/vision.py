"""
Claude 3 Sonnet-powered vision extraction for vinyl record analysis.

This module provides multimodal analysis of album artwork using Claude 3 Sonnet
to extract structured metadata: artist, title, year, label, catalog_number, genres.

Cost: ~$0.002 per image (Claude 3 Sonnet pricing)
"""

import base64
import logging
import os
import json
from typing import Optional, Dict, Any, cast
from io import BytesIO

from anthropic import Anthropic
from backend.agent.barcode_utils import validate_barcode, validate_catalog_number, format_barcode_for_search

# Claude API timeout configuration
CLAUDE_API_TIMEOUT = int(os.getenv("CLAUDE_API_TIMEOUT", "60"))  # seconds, default 60s

logger = logging.getLogger(__name__)


class VisionExtractionError(Exception):
    """Raised when vision extraction fails."""

    pass


def compress_image_to_claude_limits(image_base64: str, image_format: str = "jpeg", max_size_mb: float = 4.5) -> str:
    """
    Compress image to fit within Claude's 5MB limit.
    
    Claude has a hard limit of 5MB per image. This function compresses it.
    IMPORTANT: Claude measures the BASE64-ENCODED string size, not the binary size.
    
    Args:
        image_base64: Base64-encoded image string
        image_format: Image format (jpeg, png, webp, gif)
        max_size_mb: Target max size in MB (default 4.5 to stay under 5MB limit)
    
    Returns:
        Compressed base64-encoded image string
    """
    try:
        from PIL import Image
        
        # Decode base64
        image_data = base64.b64decode(image_base64)
        image = Image.open(BytesIO(image_data))
        
        # Convert RGBA to RGB if needed (for JPEG compatibility)
        if image.mode in ("RGBA", "LA", "P"):
            rgb_image = Image.new("RGB", image.size, (255, 255, 255))
            rgb_image.paste(image, mask=image.split()[-1] if image.mode == "RGBA" else None)
            image = rgb_image
        
        max_size_bytes = int(max_size_mb * 1024 * 1024)
        # IMPORTANT: Base64 string is ~33% larger than binary, Claude checks the base64 string size
        current_base64_size = len(image_base64)
        
        if current_base64_size <= max_size_bytes:
            logger.info(f"Image already under {max_size_mb}MB ({current_base64_size / 1024:.1f}KB base64), no compression needed")
            return image_base64
        
        logger.info(f"Image exceeds {max_size_mb}MB ({current_base64_size / 1024 / 1024:.2f}MB base64), compressing...")
        
        # Compress by reducing quality
        quality = 95
        output = BytesIO()
        target_format = "JPEG" if image_format.lower() in ("jpg", "jpeg") else image_format.upper()
        
        while True:
            output.seek(0)
            output.truncate(0)
            
            image.save(output, format=target_format, quality=quality, optimize=True)
            compressed_bytes = output.getvalue()
            compressed_base64 = base64.b64encode(compressed_bytes).decode("utf-8")
            compressed_base64_size = len(compressed_base64)
            
            logger.info(f"Compression attempt: quality={quality}, base64 size={compressed_base64_size / 1024:.1f}KB")
            
            if compressed_base64_size <= max_size_bytes or quality <= 60:
                break
            
            quality -= 5
        
        logger.info(
            f"Image compressed: {current_base64_size / 1024 / 1024:.2f}MB → {compressed_base64_size / 1024 / 1024:.2f}MB "
            f"(quality={quality})"
        )
        
        return compressed_base64
        
    except Exception as e:
        logger.warning(f"Image compression failed: {e}. Attempting to send original image.")
        return image_base64


def encode_image_to_base64(image_path: str) -> str:
    """
    Encode image file to base64 string.

    Args:
        image_path: Path to image file

    Returns:
        Base64-encoded image string

    Raises:
        FileNotFoundError: If image file not found
        ValueError: If file is not a valid image format
    """
    if not os.path.exists(image_path):
        raise FileNotFoundError(f"Image not found: {image_path}")

    valid_formats = {".jpg", ".jpeg", ".png", ".webp", ".gif"}
    _, ext = os.path.splitext(image_path)

    if ext.lower() not in valid_formats:
        raise ValueError(f"Unsupported image format: {ext}")

    with open(image_path, "rb") as image_file:
        return base64.standard_b64encode(image_file.read()).decode("utf-8")


def extract_vinyl_metadata(
    image_base64: str,
    image_format: str = "jpeg",
    fallback_on_error: bool = False,  # Changed to False - errors should be reported, not silenced
) -> Dict[str, Any]:
    """
    Extract vinyl record metadata from album artwork using Claude 3 Sonnet.

    Extracts:
    - Artist name
    - Album title
    - Release year
    - Record label
    - Catalog number
    - Genres
    - Confidence score (0.0-1.0)

    Args:
        image_base64: Base64-encoded image string
        image_format: Image format (jpeg, png, webp, gif)
        fallback_on_error: If False (default), raise VisionExtractionError on failure.
                          If True, return mock data on error (NOT RECOMMENDED)

    Returns:
        Dict with keys: artist, title, year, label, catalog_number, genres, confidence

    Raises:
        VisionExtractionError: If extraction fails (with meaningful error message)
    """
    client = Anthropic()

    # System prompt for consistent expert behavior
    system_prompt = """You are an expert vinyl record cataloguer with deep knowledge of:
- Album cover design and typography across decades and genres
- Record labels and their visual branding
- Barcode standards and formats (UPC-A, EAN-13)
- Vinyl condition grading (Goldmine standard)
- International music metadata standards
- Text recognition and OCR interpretation

Your task is to extract metadata from vinyl record images with maximum accuracy and consistency.
Be thorough in examining all visible text, especially prominent text that might be artist or title.
Focus on finding barcodes and correctly identifying metadata fields."""

    # Chain-of-thought extraction prompt
    extraction_prompt = """Analyze this vinyl record image step-by-step:

STEP 1: DESCRIBE THE IMAGE
- What do you see? (front cover, back cover, label, sleeve, etc.)
- What is the overall layout and design?
- What colors and visual elements dominate?
- Note any text visible, even if artistic or stylized

STEP 2: EXTRACT ALL VISIBLE TEXT - AGGRESSIVE OCR
This is CRITICAL. Extract EVERY piece of text visible, including:
- ANY large letters at top, middle, bottom (regardless of color/style)
- Artistic/stylized text (punk, grunge, metal styles often have creative fonts)
- Colored text (green, red, yellow, white, etc.) - don't ignore color variations
- Text in corners, edges, or overlaid on images
- Text that might be partially obscured or noisy
- Even if image is grainy/noisy, extract what you can read
- For each text element, note: position (top/middle/bottom), color, size

IMPORTANT FOR PUNK/HARDCORE COVERS:
- Punk and hardcore covers often have artist name in LARGE stylized text at top
- Album title may be in smaller or different colored text below
- Text may be in unusual colors (green, red, orange) or artistic fonts
- Grainy/noisy backgrounds are common - don't let noise prevent reading text
- Extract text AS WRITTEN, exactly as it appears (including any creative spelling)

STEP 3: IDENTIFY PRIMARY TEXT ELEMENTS
From all text extracted, identify the most prominent:
- What is the LARGEST text? (Usually artist)
- What is the SECOND largest? (Usually album title)
- What other text appears? (Label, catalog, year, etc.)

STEP 4: MAP TO METADATA FIELDS
- Artist/Group Name: The LARGEST text (even if artistic/stylized)
- Album Title: Second-largest or red/colored text below artist
- Record Label: Smaller text, often distinctive
- Catalog Number: Alphanumeric codes
- Release Year: 4-digit numbers
- Genres: Based on cover style (e.g., punk, metal, jazz)

STEP 5: FIND BARCODES
Look for UPC/EAN barcodes:
- Black and white vertical lines pattern (|||||| structure)
- Usually 12-13 digit numbers
- Common locations: corners, edges, inside covers

STEP 6: ASSESS PHYSICAL CONDITION
Examine for visible wear:
- Scratches (radial or circular patterns)
- Dust, dirt, stains
- Warping or deformation
- Rate on Goldmine scale (M/NM/VG+/VG/G+/G/F/P)

STEP 7: RATE CONFIDENCE
How confident are you in your extraction?
- High (0.8-1.0): Clear text, standard format, multiple confirmations
- Medium (0.5-0.8): Some text clear, some inferred
- Low (0.0-0.5): Unclear, ambiguous, or uncertain

STEP 8: RETURN STRUCTURED JSON
{
    "artist": "LARGEST visible text from step 2, exactly as written",
    "title": "second-largest or distinctly different colored text",
    "year": 1969 or null if not visible,
    "label": "extracted label name",
    "catalog_number": "extracted catalog code or null",
    "barcode": "extracted barcode/UPC or null",
    "genres": ["genre1", "genre2"],
    "all_visible_text": "complete list of all text found in step 2",
    "condition": "Mint (M)" through "Poor (P)" based on visible damage,
    "condition_notes": "brief description of wear/damage observed",
    "confidence": 0.75
}

CRITICAL: 
- Return ONLY valid JSON
- Prioritize LARGEST text as artist
- Don't miss stylized/colored text
- Extract text from noisy/grainy images
- No additional text before or after JSON"""

    try:
        logger.info("Starting Claude 3 Sonnet vision extraction...")
        logger.info(f"Image format: {image_format}, Image data length: {len(image_base64)}")

        # Compress image to fit within Claude's 5MB limit
        logger.info("Compressing image to Claude API limits (5MB max)...")
        image_base64 = compress_image_to_claude_limits(image_base64, image_format)
        logger.info(f"After compression, image data length: {len(image_base64)}")

        # Get vision model from environment, with fallback
        vision_model = os.getenv("ANTHROPIC_VISION_MODEL", "claude-sonnet-4-5-20250929")
        logger.info(f"Using vision model: {vision_model}")

        # Try with the model name - Claude Sonnet 4.5 (vision capable)
        message = client.messages.create(
            model=vision_model,
            max_tokens=1500,  # Increased for detailed chain-of-thought analysis
            temperature=0.3,  # Deterministic output for consistent metadata extraction
            system=system_prompt,  # Expert context for better analysis
            timeout=CLAUDE_API_TIMEOUT,  # Configurable timeout from environment
            messages=cast(
                Any,
                [
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "image",
                                "source": {
                                    "type": "base64",
                                    "media_type": f"image/{image_format}",
                                    "data": image_base64,
                                },
                            },
                            {
                                "type": "text",
                                "text": extraction_prompt,
                            },
                        ],
                    }
                ],
            ),
        )

        # Parse the response
        response_text: str = ""
        
        if message.content and len(message.content) > 0:
            first_content = message.content[0]
            if hasattr(first_content, "text"):
                response_text = first_content.text  # type: ignore

        logger.debug(f"Claude 3 response: {response_text}")

        # Extract JSON from response (in case there's extra text)
        try:
            # Try to find JSON in the response
            json_start = response_text.find("{")
            json_end = response_text.rfind("}") + 1

            if json_start == -1 or json_end == 0:
                raise ValueError("No JSON found in response")

            json_str = response_text[json_start:json_end]
            metadata = json.loads(json_str)

            # Validate required fields
            required_fields = ["artist", "title", "label", "genres", "confidence"]
            missing_fields = [f for f in required_fields if f not in metadata]

            if missing_fields:
                raise ValueError(f"Missing required fields: {missing_fields}")

            # Normalize data types
            if isinstance(metadata.get("year"), str):
                try:
                    metadata["year"] = int(metadata["year"])
                except (ValueError, TypeError):
                    metadata["year"] = None

            if not isinstance(metadata.get("genres"), list):
                metadata["genres"] = []

            # Ensure confidence is a float
            try:
                metadata["confidence"] = float(metadata.get("confidence", 0.5))
            except (ValueError, TypeError):
                metadata["confidence"] = 0.5

            # Preserve all_visible_text if present (for multi-image aggregation)
            if "all_visible_text" not in metadata:
                metadata["all_visible_text"] = ""

            # Validate and clean barcode if present
            if metadata.get("barcode"):
                is_valid, cleaned_barcode, error = validate_barcode(metadata["barcode"])
                if is_valid and cleaned_barcode:
                    metadata["barcode"] = cleaned_barcode
                    logger.info(f"Vision extraction: Valid barcode detected: {cleaned_barcode}")
                else:
                    logger.warning(f"Vision extraction: Invalid barcode '{metadata['barcode']}': {error}")
                    metadata["barcode"] = None
            
            # Validate and clean catalog_number if present
            if metadata.get("catalog_number"):
                is_valid, cleaned_catalog, error = validate_catalog_number(metadata["catalog_number"])
                if is_valid and cleaned_catalog:
                    metadata["catalog_number"] = cleaned_catalog
                    logger.info(f"Vision extraction: Valid catalog number detected: {cleaned_catalog}")
                else:
                    logger.warning(f"Vision extraction: Invalid catalog number '{metadata['catalog_number']}': {error}")
                    metadata["catalog_number"] = None
            
            # Log barcode detection success
            barcode_info = f" (barcode: {metadata.get('barcode', 'none')})" if metadata.get('barcode') else ""
            logger.info(
                f"Vision extraction successful: {metadata['artist']} - {metadata['title']} "
                f"(confidence: {metadata['confidence']:.2f}){barcode_info}"
            )

            return metadata

        except (json.JSONDecodeError, ValueError) as e:
            logger.error(f"Failed to parse Claude 3 response as JSON: {e}")
            raise VisionExtractionError(f"Invalid response format: {e}") from e

    except Exception as e:
        logger.error(f"Vision extraction failed: {type(e).__name__}: {e}")
        import traceback
        logger.error(f"Traceback: {traceback.format_exc()}")

        # Provide meaningful error messages instead of fallback data
        error_msg = str(e)
        
        # Check for specific error types
        if "image exceeds" in error_msg.lower() and "MB maximum" in error_msg.lower():
            error_details = "Image file is too large. Please ensure the image is under 5 MB."
        elif "timeout" in error_msg.lower():
            error_details = "Image analysis request timed out. Please try again or with a smaller image."
        elif "invalid_request_error" in error_msg.lower():
            error_details = "Invalid image format or data. Please upload a valid JPEG, PNG, or WebP image."
        elif "rate_limit" in error_msg.lower():
            error_details = "API rate limit reached. Please wait a moment and try again."
        elif "authentication" in error_msg.lower() or "api" in error_msg.lower():
            error_details = "API authentication error. Please check your configuration."
        else:
            error_details = f"Image analysis failed: {error_msg}"
        
        if fallback_on_error:
            logger.warning(f"Raising error instead of falling back: {error_details}")
            raise VisionExtractionError(error_details) from e
        else:
            raise VisionExtractionError(error_details) from e


def extract_vinyl_metadata_from_file(
    image_path: str,
    fallback_on_error: bool = True,
) -> Dict[str, Any]:
    """
    Extract vinyl metadata from image file.

    Args:
        image_path: Path to image file
        fallback_on_error: If True, return mock data on error

    Returns:
        Dict with extracted metadata

    Raises:
        VisionExtractionError: If extraction fails
        FileNotFoundError: If image file not found
    """
    logger.info(f"Extracting metadata from: {image_path}")

    # Determine image format
    _, ext = os.path.splitext(image_path)
    image_format = ext[1:].lower() if ext else "jpeg"

    if image_format == "jpg":
        image_format = "jpeg"

    # Encode image
    image_base64 = encode_image_to_base64(image_path)

    # Extract metadata
    return extract_vinyl_metadata(image_base64, image_format, fallback_on_error)


if __name__ == "__main__":
    """Quick test of vision extraction."""
    import sys

    logging.basicConfig(level=logging.INFO)

    if len(sys.argv) < 2:
        print("Usage: python vision.py <image_path>")
        sys.exit(1)

    image_path = sys.argv[1]

    try:
        metadata = extract_vinyl_metadata_from_file(image_path)
        print("\nExtracted Metadata:")
        print(json.dumps(metadata, indent=2))
    except VisionExtractionError as e:
        print(f"Error: {e}")
        sys.exit(1)
