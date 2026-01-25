"""
Barcode validation and processing utilities for vinyl record identification.

Provides functions to validate, clean, and format UPC/EAN barcodes commonly
found on vinyl records.
"""

import logging
import re
from typing import Optional, Tuple

logger = logging.getLogger(__name__)


def validate_barcode(barcode: str) -> Tuple[bool, Optional[str], Optional[str]]:
    """
    Validate and clean a barcode string.
    
    Args:
        barcode: Raw barcode string from vision extraction
        
    Returns:
        Tuple of (is_valid, cleaned_barcode, error_message)
        
    Examples:
        >>> validate_barcode("123456789012")
        (True, "123456789012", None)
        
        >>> validate_barcode("UPC: 123-456-789012")
        (True, "123456789012", None)
        
        >>> validate_barcode("12345")
        (False, None, "Invalid length: expected 12-13 digits, got 5")
    """
    if not barcode or not isinstance(barcode, str):
        return False, None, "Empty or invalid barcode"
    
    # Remove common prefixes and clean up
    cleaned = barcode.strip().upper()
    
    # Remove common prefixes
    prefixes = ["UPC:", "UPC", "EAN:", "EAN", "BARCODE:", "BARCODE"]
    for prefix in prefixes:
        if cleaned.startswith(prefix):
            cleaned = cleaned[len(prefix):].strip()
            break
    
    # Remove spaces, hyphens, and other separators
    cleaned = re.sub(r'[^\d]', '', cleaned)
    
    # Validate length (UPC-A: 12 digits, EAN-13: 13 digits)
    if len(cleaned) not in [12, 13]:
        return False, None, f"Invalid length: expected 12-13 digits, got {len(cleaned)}"
    
    # Validate all digits
    if not cleaned.isdigit():
        return False, None, "Contains non-digit characters after cleaning"
    
    # Basic UPC/EAN validation (check digit validation could be added here)
    return True, cleaned, None


def format_barcode_for_search(barcode: str) -> Optional[str]:
    """
    Format a barcode for optimal search results.
    
    Args:
        barcode: Raw or cleaned barcode
        
    Returns:
        Formatted barcode string or None if invalid
    """
    is_valid, cleaned, error = validate_barcode(barcode)
    
    if not is_valid:
        logger.warning(f"Invalid barcode for search: {error}")
        return None
    
    # Add leading zero for UPC-A if needed (some systems expect 13-digit EAN format)
    if len(cleaned) == 12:
        # Convert UPC-A to EAN-13 by adding leading zero
        return f"0{cleaned}"
    
    return cleaned


def extract_barcodes_from_text(text: str) -> list[str]:
    """
    Extract potential barcodes from free-form text.
    
    Args:
        text: Text that may contain barcodes
        
    Returns:
        List of valid barcode strings found in the text
    """
    if not text:
        return []
    
    # Pattern to match potential barcodes (12-13 consecutive digits)
    barcode_pattern = r'\b\d{12,13}\b'
    
    potential_barcodes = re.findall(barcode_pattern, text)
    valid_barcodes = []
    
    for candidate in potential_barcodes:
        is_valid, cleaned, _ = validate_barcode(candidate)
        if is_valid and cleaned:
            valid_barcodes.append(cleaned)
    
    return valid_barcodes


def is_likely_barcode(text: str) -> bool:
    """
    Quick check if a text string looks like a barcode.
    
    Args:
        text: Text to check
        
    Returns:
        True if text looks like a barcode
    """
    if not text:
        return False
    
    # Check for barcode-like patterns
    cleaned = re.sub(r'[^\d]', '', text.strip())
    
    # Must be 12-13 digits
    if len(cleaned) not in [12, 13]:
        return False
    
    # Must be all digits
    if not cleaned.isdigit():
        return False
    
    # Additional heuristics
    original = text.strip().upper()
    
    # Contains barcode keywords
    barcode_keywords = ["UPC", "EAN", "BARCODE"]
    has_keyword = any(keyword in original for keyword in barcode_keywords)
    
    # Very long number without spaces (likely barcode)
    is_long_number = len(cleaned) >= 12 and ' ' not in text.strip()
    
    return has_keyword or is_long_number