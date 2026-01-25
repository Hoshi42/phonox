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

from anthropic import Anthropic
from backend.agent.barcode_utils import validate_barcode, format_barcode_for_search

logger = logging.getLogger(__name__)


class VisionExtractionError(Exception):
    """Raised when vision extraction fails."""

    pass


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
    fallback_on_error: bool = True,
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
        fallback_on_error: If True, return mock data on API error

    Returns:
        Dict with keys: artist, title, year, label, catalog_number, genres, confidence

    Raises:
        VisionExtractionError: If extraction fails and fallback_on_error=False
    """
    client = Anthropic()

    # Construct the prompt for vinyl metadata extraction with enhanced barcode detection
    extraction_prompt = """Analyze this vinyl record image (could be album cover, back cover, spine, or label) and extract the following metadata:

1. Artist/Group Name
2. Album Title
3. Release Year (if visible, otherwise null)
4. Record Label
5. Catalog Number (alphanumeric code like "ABC-123", "DEF 456", etc.)
6. Barcode/UPC (long numeric code, typically 12-13 digits)
7. Genres (comma-separated list)
8. Confidence Score (0.0-1.0) indicating how confident you are in the accuracy

CRITICAL BARCODE IDENTIFICATION INSTRUCTIONS:
- UPC/EAN barcodes appear as BLACK AND WHITE VERTICAL LINES (like |||||| ||| | |||) with numbers below
- Look VERY CAREFULLY for barcode patterns - they are often small and in corners
- Barcode numbers are typically 12-13 digits (examples: 123456789012, 1234567890123)
- Common locations: back cover (bottom left/right corners), spine, inner sleeve
- May be prefixed with "UPC:", "EAN:", or just raw numbers
- DIFFERENT from catalog numbers (which are usually shorter like "ABC-123")
- Even if barcode lines are unclear, try to read any long numeric sequences (12+ digits)

LOOK EXTRA HARD FOR BARCODES - they are critical for identification!

EXAMPLES OF VALID BARCODES:
- "886979578623" (12 digits)
- "4050538642823" (13 digits) 
- "075021234567" (with leading zero)
- "UPC: 123456789012"

IMPORTANT: Return ONLY a valid JSON object with this exact structure:
{
    "artist": "extracted artist name",
    "title": "extracted album title",
    "year": 1969 or null,
    "label": "extracted label name",
    "catalog_number": "extracted catalog number or null",
    "barcode": "extracted barcode/UPC or null",
    "genres": ["genre1", "genre2"],
    "confidence": 0.85
}

Do NOT include any text outside the JSON. FOCUS MAXIMUM ATTENTION on finding barcode numbers!"""

    try:
        logger.info("Starting Claude 3 Sonnet vision extraction...")
        logger.info(f"Image format: {image_format}, Image data length: {len(image_base64)}")

        # Try with the model name - Claude Sonnet 4.5 (vision capable)
        message = client.messages.create(
            model="claude-sonnet-4-5-20250929",
            max_tokens=500,
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

            # Validate and clean barcode if present
            if metadata.get("barcode"):
                is_valid, cleaned_barcode, error = validate_barcode(metadata["barcode"])
                if is_valid and cleaned_barcode:
                    metadata["barcode"] = cleaned_barcode
                    logger.info(f"Vision extraction: Valid barcode detected: {cleaned_barcode}")
                else:
                    logger.warning(f"Vision extraction: Invalid barcode '{metadata['barcode']}': {error}")
                    metadata["barcode"] = None
            
            # Log barcode detection success
            barcode_info = f" (barcode: {metadata.get('barcode', 'none')})" if metadata.get('barcode') else ""
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

        if fallback_on_error:
            logger.warning("Falling back to mock data...")
            return {
                "artist": "Unknown Artist",
                "title": "Unknown Album",
                "year": None,
                "label": "Unknown Label",
                "catalog_number": None,
                "barcode": None,
                "genres": ["Unknown"],
                "confidence": 0.0,  # 0 confidence for fallback
            }
        else:
            raise VisionExtractionError(f"Vision extraction failed: {e}") from e


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
