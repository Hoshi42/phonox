"""
Phonox Agent State Models

Defines the data structures used throughout the LangGraph agent workflow.
Uses TypedDict for type safety and static analysis support.
"""

from typing import TypedDict, Optional, List, Literal
from datetime import datetime
from enum import Enum


class EvidenceType(str, Enum):
    """Types of evidence sources for vinyl record identification."""
    DISCOGS = "discogs"
    MUSICBRAINZ = "musicbrainz"
    IMAGE = "image"
    VISION = "vision"  # Claude 3 multimodal analysis
    WEBSEARCH = "websearch"  # Tavily web search
    USER_INPUT = "user_input"


class Evidence(TypedDict):
    """
    Single piece of evidence about a vinyl record.
    
    Attributes:
        source: Origin of this evidence (EvidenceType enum)
        confidence: Numeric confidence score (0.0 to 1.0)
        data: Raw tool response or extracted features
        timestamp: When this evidence was collected
    """
    source: str  # EvidenceType value: "discogs", "musicbrainz", "image", "vision", "websearch", "user_input"
    confidence: float  # Range: [0.0, 1.0]
    data: dict  # Tool-specific response format
    timestamp: datetime


class VinylMetadata(TypedDict):
    """
    Aggregated metadata about a vinyl record.
    
    Combines evidence from multiple sources (Discogs, MusicBrainz, image analysis)
    into a single record with overall confidence score.
    
    Attributes:
        artist: Primary artist name
        title: Album/release title
        year: Release year (if known)
        label: Record label
        catalog_number: Label catalog number (if available)
        genres: List of genre tags
        evidence: Chain of evidence sources backing this metadata
        overall_confidence: Weighted confidence across all sources
    """
    artist: str
    title: str
    year: Optional[int]
    label: str
    catalog_number: Optional[str]
    genres: List[str]
    evidence: List[Evidence]
    overall_confidence: float  # Weighted average of evidence confidences


class VinylState(TypedDict, total=False):
    """
    Complete state of a vinyl record processing workflow.
    
    This is the main state object passed through the LangGraph agent.
    Each node in the graph reads and writes to this state.
    
    Phase 1.1 node interfaces expect these fields:
    - images: Input images for processing
    - image_features: Extracted features (embeddings, colors, OCR)
    - vision_extraction: Claude 3 multimodal analysis output
    - evidence_chain: Chain of evidence collected
    - websearch_results: Tavily web search results
    - confidence: Overall confidence score (0.0-1.0)
    - auto_commit: Boolean flag for auto-approval
    - needs_review: Boolean flag for manual review
    - validation_passed: Image validation result
    - validation_errors: List of validation errors
    """
    # Input
    images: List[dict]  # List of image dicts: {format, size_bytes}
    
    # Processing
    image_features: dict  # {embeddings, colors, ocr_text}
    vision_extraction: dict  # Claude 3 output: {artist, title, year, label, catalog_number, genres, confidence}
    websearch_results: List[dict]  # Tavily search results
    
    # Evidence & Scoring
    evidence_chain: List[Evidence]  # Append-only history of evidence
    confidence: float  # Overall confidence (0.0-1.0)
    
    # Routing
    auto_commit: bool  # If confidence >= 0.85
    needs_review: bool  # If confidence < 0.85
    
    # Validation
    validation_passed: bool
    validation_errors: List[str]
    
    # Legacy fields (kept for backward compatibility)
    metadata: Optional[VinylMetadata]
    status: str
    error: Optional[str]


# Confidence scoring weights (must sum to 1.0)
# Used to calculate overall_confidence in VinylMetadata
CONFIDENCE_WEIGHTS = {
    "discogs": 0.45,        # Most reliable (official database)
    "musicbrainz": 0.25,    # Reliable (crowdsourced but verified)
    "vision": 0.20,         # Claude 3 multimodal analysis (NEW)
    "websearch": 0.10,      # Web search fallback (NEW)
}

# Confidence thresholds for decision gates
CONFIDENCE_THRESHOLDS = {
    "auto_commit": 0.90,      # High confidence: auto-approve
    "recommended_review": 0.85,  # Good confidence: recommend but review
    "manual_review": 0.70,    # Lower: should be reviewed
    "manual_entry": 0.50,     # Low: user should verify manually
}


def calculate_overall_confidence(evidence_list: List[Evidence]) -> float:
    """
    Calculate weighted confidence score from evidence list.
    
    Args:
        evidence_list: List of Evidence dicts from different sources
        
    Returns:
        Weighted confidence score (0.0 to 1.0)
        
    Example:
        >>> evidence = [
        ...     Evidence(source="discogs", confidence=0.95, data={}, timestamp=now),
        ...     Evidence(source="musicbrainz", confidence=0.80, data={}, timestamp=now),
        ... ]
        >>> score = calculate_overall_confidence(evidence)
        >>> 0.88 < score < 0.92  # Weighted average
        True
    """
    if not evidence_list:
        return 0.0
    
    weighted_sum = 0.0
    total_weight = 0.0
    
    for evidence in evidence_list:
        source = evidence["source"]
        confidence = evidence["confidence"]
        
        # Use weight if source is recognized, otherwise 0.0 weight
        weight = CONFIDENCE_WEIGHTS.get(source, 0.0)
        weighted_sum += confidence * weight
        total_weight += weight
    
    # Return weighted average (or 0.0 if no recognized sources)
    if total_weight == 0.0:
        return 0.0
    
    return weighted_sum / total_weight
