"""
Unit tests for Claude 3 Sonnet vision extraction module.

Tests for:
- extract_vinyl_metadata: Main extraction function
- encode_image_to_base64: Image encoding
- extract_vinyl_metadata_from_file: File-based extraction
- Error handling and fallback
"""

import json
import pytest
import tempfile
import os
from pathlib import Path
from unittest.mock import patch, MagicMock

from backend.agent.vision import (
    extract_vinyl_metadata,
    extract_vinyl_metadata_from_file,
    encode_image_to_base64,
    VisionExtractionError,
)


# ============================================================================
# FIXTURES
# ============================================================================


@pytest.fixture
def mock_image_base64():
    """Mock base64-encoded image."""
    return "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg=="


@pytest.fixture
def sample_image_file():
    """Create a temporary image file for testing."""
    with tempfile.NamedTemporaryFile(suffix=".jpg", delete=False) as f:
        # Write minimal JPEG header
        f.write(b"\xff\xd8\xff\xe0\x00\x10JFIF\x00\x01\x01\x00\x00\x01\x00\x01\x00\x00")
        temp_path = f.name

    yield temp_path

    # Cleanup
    try:
        os.remove(temp_path)
    except:
        pass


# ============================================================================
# ENCODE_IMAGE_TO_BASE64 TESTS
# ============================================================================


def test_encode_image_valid_jpeg(sample_image_file):
    """Test encoding valid JPEG image."""
    result = encode_image_to_base64(sample_image_file)

    assert isinstance(result, str)
    assert len(result) > 0


def test_encode_image_file_not_found():
    """Test error when image file not found."""
    with pytest.raises(FileNotFoundError):
        encode_image_to_base64("/nonexistent/image.jpg")


def test_encode_image_invalid_format():
    """Test error with invalid image format."""
    with tempfile.NamedTemporaryFile(suffix=".bmp", delete=False) as f:
        temp_path = f.name

    try:
        with pytest.raises(ValueError, match="Unsupported image format"):
            encode_image_to_base64(temp_path)
    finally:
        os.remove(temp_path)


def test_encode_image_supports_multiple_formats(sample_image_file):
    """Test that multiple image formats are supported."""
    # JPEG
    result_jpg = encode_image_to_base64(sample_image_file)
    assert result_jpg

    # PNG
    with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as f:
        f.write(b"\x89PNG\r\n\x1a\n")
        png_path = f.name

    try:
        result_png = encode_image_to_base64(png_path)
        assert result_png
    finally:
        os.remove(png_path)


# ============================================================================
# EXTRACT_VINYL_METADATA TESTS
# ============================================================================


@patch("backend.agent.vision.Anthropic")
def test_extract_metadata_success(mock_anthropic, mock_image_base64):
    """Test successful metadata extraction."""
    # Mock Claude 3 response
    mock_response = MagicMock()
    mock_response.content = [
        MagicMock(
            text=json.dumps({
                "artist": "The Beatles",
                "title": "Abbey Road",
                "year": 1969,
                "label": "Apple Records",
                "catalog_number": "PCS 7088",
                "genres": ["Rock", "Pop"],
                "confidence": 0.95,
            })
        )
    ]

    mock_client = MagicMock()
    mock_client.messages.create.return_value = mock_response
    mock_anthropic.return_value = mock_client

    result = extract_vinyl_metadata(mock_image_base64, "jpeg")

    assert result["artist"] == "The Beatles"
    assert result["title"] == "Abbey Road"
    assert result["year"] == 1969
    assert result["label"] == "Apple Records"
    assert result["catalog_number"] == "PCS 7088"
    assert result["genres"] == ["Rock", "Pop"]
    assert result["confidence"] == 0.95


@patch("backend.agent.vision.Anthropic")
def test_extract_metadata_missing_optional_fields(mock_anthropic, mock_image_base64):
    """Test extraction with missing optional fields."""
    mock_response = MagicMock()
    mock_response.content = [
        MagicMock(
            text=json.dumps({
                "artist": "Unknown Artist",
                "title": "Unknown Title",
                "year": None,
                "label": "Unknown Label",
                "catalog_number": None,
                "genres": [],
                "confidence": 0.5,
            })
        )
    ]

    mock_client = MagicMock()
    mock_client.messages.create.return_value = mock_response
    mock_anthropic.return_value = mock_client

    result = extract_vinyl_metadata(mock_image_base64, "jpeg")

    assert result["year"] is None
    assert result["catalog_number"] is None
    assert result["genres"] == []
    assert result["confidence"] == 0.5


@patch("backend.agent.vision.Anthropic")
def test_extract_metadata_normalizes_data_types(mock_anthropic, mock_image_base64):
    """Test that response data types are normalized."""
    mock_response = MagicMock()
    mock_response.content = [
        MagicMock(
            text=json.dumps({
                "artist": "The Beatles",
                "title": "Abbey Road",
                "year": "1969",  # String instead of int
                "label": "Apple Records",
                "catalog_number": "PCS 7088",
                "genres": "Rock,Pop",  # String instead of list
                "confidence": "0.95",  # String instead of float
            })
        )
    ]

    mock_client = MagicMock()
    mock_client.messages.create.return_value = mock_response
    mock_anthropic.return_value = mock_client

    result = extract_vinyl_metadata(mock_image_base64, "jpeg")

    # Should be normalized to correct types
    assert isinstance(result["year"], int)
    assert result["year"] == 1969
    assert isinstance(result["confidence"], float)
    assert result["confidence"] == 0.95


@patch("backend.agent.vision.Anthropic")
def test_extract_metadata_invalid_json(mock_anthropic, mock_image_base64):
    """Test error handling for invalid JSON response."""
    mock_response = MagicMock()
    mock_response.content = [MagicMock(text="Not valid JSON")]

    mock_client = MagicMock()
    mock_client.messages.create.return_value = mock_response
    mock_anthropic.return_value = mock_client

    # Should return fallback data
    result = extract_vinyl_metadata(mock_image_base64, "jpeg", fallback_on_error=True)

    assert result["artist"] == "Unknown Artist"
    assert result["confidence"] == 0.0  # 0 confidence for fallback


@patch("backend.agent.vision.Anthropic")
def test_extract_metadata_missing_required_fields(mock_anthropic, mock_image_base64):
    """Test error when required fields are missing."""
    mock_response = MagicMock()
    mock_response.content = [
        MagicMock(
            text=json.dumps({
                "artist": "The Beatles",
                # Missing title, label, genres, confidence
            })
        )
    ]

    mock_client = MagicMock()
    mock_client.messages.create.return_value = mock_response
    mock_anthropic.return_value = mock_client

    result = extract_vinyl_metadata(mock_image_base64, "jpeg", fallback_on_error=True)

    # Should return fallback data
    assert result["artist"] == "Unknown Artist"
    assert result["confidence"] == 0.0


@patch("backend.agent.vision.Anthropic")
def test_extract_metadata_api_error(mock_anthropic, mock_image_base64):
    """Test fallback on API error."""
    mock_client = MagicMock()
    mock_client.messages.create.side_effect = Exception("API Error")
    mock_anthropic.return_value = mock_client

    result = extract_vinyl_metadata(mock_image_base64, "jpeg", fallback_on_error=True)

    # Should return fallback data
    assert result["artist"] == "Unknown Artist"
    assert result["confidence"] == 0.0


@patch("backend.agent.vision.Anthropic")
def test_extract_metadata_api_error_no_fallback(mock_anthropic, mock_image_base64):
    """Test error raised when fallback disabled."""
    mock_client = MagicMock()
    mock_client.messages.create.side_effect = Exception("API Error")
    mock_anthropic.return_value = mock_client

    with pytest.raises(VisionExtractionError):
        extract_vinyl_metadata(mock_image_base64, "jpeg", fallback_on_error=False)


# ============================================================================
# EXTRACT_VINYL_METADATA_FROM_FILE TESTS
# ============================================================================


@patch("backend.agent.vision.extract_vinyl_metadata")
def test_extract_from_file_success(mock_extract, sample_image_file):
    """Test extraction from file."""
    expected_result = {
        "artist": "The Beatles",
        "title": "Abbey Road",
        "year": 1969,
        "label": "Apple Records",
        "catalog_number": "PCS 7088",
        "genres": ["Rock", "Pop"],
        "confidence": 0.95,
    }
    mock_extract.return_value = expected_result

    result = extract_vinyl_metadata_from_file(sample_image_file)

    assert result == expected_result
    mock_extract.assert_called_once()


def test_extract_from_file_not_found():
    """Test error when file not found."""
    with pytest.raises(FileNotFoundError):
        extract_vinyl_metadata_from_file("/nonexistent/image.jpg")


@patch("backend.agent.vision.extract_vinyl_metadata")
def test_extract_from_file_detects_format(mock_extract, sample_image_file):
    """Test that file format is correctly detected."""
    mock_extract.return_value = {"artist": "Test", "title": "Test", "confidence": 0.5}

    extract_vinyl_metadata_from_file(sample_image_file)

    # Check that format was passed correctly
    call_args = mock_extract.call_args
    assert "jpeg" in str(call_args).lower()


# ============================================================================
# INTEGRATION TESTS
# ============================================================================


@patch("backend.agent.vision.Anthropic")
def test_end_to_end_extraction(mock_anthropic, mock_image_base64):
    """Test complete extraction workflow."""
    mock_response = MagicMock()
    mock_response.content = [
        MagicMock(
            text=json.dumps({
                "artist": "Pink Floyd",
                "title": "The Dark Side of the Moon",
                "year": 1973,
                "label": "Harvest",
                "catalog_number": "SHVL 804",
                "genres": ["Progressive Rock", "Psychedelic Rock"],
                "confidence": 0.98,
            })
        )
    ]

    mock_client = MagicMock()
    mock_client.messages.create.return_value = mock_response
    mock_anthropic.return_value = mock_client

    result = extract_vinyl_metadata(mock_image_base64, "png")

    assert result["artist"] == "Pink Floyd"
    assert result["title"] == "The Dark Side of the Moon"
    assert result["year"] == 1973
    assert result["label"] == "Harvest"
    assert 0.9 <= result["confidence"] <= 1.0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
