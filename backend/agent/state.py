"""
Phonox Agent State Models

Defines the data structures used throughout the LangGraph agent workflow.
Uses TypedDict for type safety and static analysis support.
"""

from typing import TypedDict, Optional, List
from datetime import datetime


class Evidence(TypedDict):
    """
    Single piece of evidence about a vinyl record.
    
    Attributes:
        source: Origin of this evidence ("discogs", "musicbrainz", "image", "vision", "websearch")
        confidence: Numeric confidence score (0.0 to 1.0)
        data: Raw tool response or extracted features
        timestamp: When this evidence was collected
    """
    source: str  # "discogs", "musicbrainz", "image", "vision", "websearch", "user_input"
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


class VinylState(TypedDict):
    """
    Complete state of a vinyl record processing workflow.
    
    This is the main state object passed through the LangGraph agent.
    Each node in the graph reads and writes to this state.
    
    Attributes:
        images: List of base64-encoded images or file paths
        metadata: Extracted/looked-up metadata (None if processing)
        evidence_chain: Complete history of all evidence collected
        status: Processing status ("pending", "processing", "complete", "failed")
        error: Error message if status is "failed"
        vision_extraction: Claude 3 multimodal analysis output (NEW)
        websearch_results: Tavily web search results (NEW)
    """
    images: List[str]  # Base64 strings or file paths
    metadata: Optional[VinylMetadata]  # None until processing completes
    evidence_chain: List[Evidence]  # Append-only list
    status: str  # "pending" | "processing" | "complete" | "failed"
    error: Optional[str]  # Only set if status == "failed"
    vision_extraction: Optional[dict]  # Claude 3 vision output (NEW)
    websearch_results: Optional[List[dict]]  # Tavily results (NEW)


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
