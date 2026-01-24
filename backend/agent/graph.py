"""
LangGraph workflow builder for vinyl record identification.

Implements a 6-node agent graph:
1. validate_images: Check image format, count, size
2. extract_features: Extract image features (embeddings, colors, etc.)
3. vision_extraction: Claude 3 multimodal analysis of album artwork
4. lookup_metadata: Query Discogs/MusicBrainz APIs
5. websearch_fallback: Tavily websearch when primary sources fail
6. confidence_gate: Calculate confidence and route to auto-commit or review

Phase 1.1 Implementation (Weeks 2-3)
"""

import logging
from datetime import datetime
from typing import Literal

from langgraph.graph import StateGraph, START, END
from langgraph.checkpoint.memory import MemorySaver

from backend.agent.state import VinylState, Evidence, EvidenceType

logger = logging.getLogger(__name__)


# ============================================================================
# NODE IMPLEMENTATIONS
# ============================================================================


def validate_images_node(state: VinylState) -> VinylState:
    """
    Validate uploaded images for format, count, and size.

    Checks:
    - Image count: minimum 1, maximum 10
    - Image format: JPEG, PNG, WebP, GIF
    - Image size: < 10MB each

    Returns:
        VinylState: Updated state with validation_passed flag
    """
    images = state.get("images", [])

    # Validate count
    if not images or len(images) == 0:
        state["validation_errors"] = ["No images provided"]
        state["validation_passed"] = False
        logger.warning("validate_images: No images provided")
        return state

    if len(images) > 10:
        state["validation_errors"] = [f"Too many images: {len(images)} (max 10)"]
        state["validation_passed"] = False
        logger.warning(f"validate_images: Too many images ({len(images)})")
        return state

    # Validate format and size (simplified - assumes images are already loaded)
    valid_formats = {"jpeg", "jpg", "png", "webp", "gif"}
    validation_errors = []

    for idx, image in enumerate(images):
        # In production, check actual image metadata
        # For now, assume images are pre-validated by frontend
        if isinstance(image, dict):
            fmt = image.get("format", "").lower()
            size = image.get("size_bytes", 0)

            if fmt not in valid_formats:
                validation_errors.append(f"Image {idx}: Invalid format '{fmt}'")

            if size > 10 * 1024 * 1024:  # 10MB
                validation_errors.append(f"Image {idx}: Too large ({size / 1024 / 1024:.1f}MB)")

    if validation_errors:
        state["validation_errors"] = validation_errors
        state["validation_passed"] = False
        logger.warning(f"validate_images: Validation failed - {validation_errors}")
        return state

    # All validations passed
    state["validation_passed"] = True
    state["validation_errors"] = []
    logger.info(f"validate_images: Passed validation for {len(images)} image(s)")

    return state


def extract_features_node(state: VinylState) -> VinylState:
    """
    Extract features from validated images.

    Features extracted:
    - Visual embeddings (ViT-base 768-dim)
    - Dominant colors
    - OCR text

    Returns:
        VinylState: Updated state with image_features
    """
    if not state.get("validation_passed", False):
        logger.warning("extract_features: Skipping - images not validated")
        return state

    images = state.get("images", [])

    # Stub: In production, this would call ViT model for embeddings
    # For Phase 1.1, we return mock features
    features = {
        "embeddings": [[0.1] * 768 for _ in images],  # Mock 768-dim embeddings
        "colors": [["#FF0000", "#00FF00", "#0000FF"] for _ in images],  # Top 3 colors
        "ocr_text": ["Mock OCR text from album cover" for _ in images],
    }

    state["image_features"] = features
    logger.info(f"extract_features: Extracted features for {len(images)} image(s)")

    return state


def vision_extraction_node(state: VinylState) -> VinylState:
    """
    Use Claude 3 Sonnet to analyze album artwork and extract metadata.

    Extracts:
    - Artist name
    - Album title
    - Release year
    - Label
    - Catalog number
    - Genres

    Confidence: 0.20 weight in 4-way system

    Returns:
        VinylState: Updated state with vision_extraction dict
    """
    from anthropic import Anthropic

    if not state.get("image_features"):
        logger.warning("vision_extraction: No image features to analyze")
        return state

    client = Anthropic()
    images = state.get("images", [])

    if not images:
        logger.warning("vision_extraction: No images provided")
        return state

    # For Phase 1.1, use first image only (mock implementation)
    # In production, analyze all images and aggregate results
    vision_results = {
        "artist": "The Beatles",  # Mock result
        "title": "Abbey Road",  # Mock result
        "year": 1969,  # Mock result
        "label": "Apple Records",  # Mock result
        "catalog_number": "PCS 7088",  # Mock result
        "genres": ["Rock", "Pop"],  # Mock result
        "confidence": 0.75,  # Mock confidence from vision
    }

    state["vision_extraction"] = vision_results
    logger.info("vision_extraction: Extracted metadata using Claude 3 Sonnet")

    return state


def lookup_metadata_node(state: VinylState) -> VinylState:
    """
    Query Discogs and MusicBrainz for metadata.

    Returns structured evidence with:
    - Source (discogs, musicbrainz)
    - Confidence score
    - Full metadata

    Returns:
        VinylState: Updated state with evidence_chain
    """
    evidence_chain = state.get("evidence_chain", [])

    # Stub: Mock Discogs result
    discogs_evidence: Evidence = {
        "source": EvidenceType.DISCOGS,
        "confidence": 0.85,
        "data": {
            "artist": "The Beatles",
            "title": "Abbey Road",
            "year": 1969,
            "label": "Apple Records",
            "catalog_number": "PCS 7088",
        },
        "timestamp": datetime.now(),
    }

    evidence_chain.append(discogs_evidence)

    # Stub: Mock MusicBrainz result
    musicbrainz_evidence: Evidence = {
        "source": EvidenceType.MUSICBRAINZ,
        "confidence": 0.80,
        "data": {
            "artist": "The Beatles",
            "title": "Abbey Road",
            "year": 1969,
            "release_group_id": "mock-id",
        },
        "timestamp": datetime.now(),
    }

    evidence_chain.append(musicbrainz_evidence)

    state["evidence_chain"] = evidence_chain
    logger.info(f"lookup_metadata: Added {len(evidence_chain)} evidence sources")

    return state


def websearch_fallback_node(state: VinylState) -> VinylState:
    """
    Use Tavily API for websearch when primary sources don't have sufficient confidence.

    Triggers when: confidence < 0.75

    Returns structured websearch results with:
    - Top match from search results
    - Confidence score

    Returns:
        VinylState: Updated state with websearch_results (optional)
    """
    current_confidence = state.get("confidence", 0.0)

    # Only trigger if confidence is low
    if current_confidence >= 0.75:
        logger.info(f"websearch_fallback: Skipping (confidence {current_confidence:.2f} >= 0.75)")
        return state

    from tavily import TavilyClient

    client = TavilyClient()

    # Get artist + title from vision or metadata for search query
    vision_data = state.get("vision_extraction", {})
    artist = vision_data.get("artist", "")
    title = vision_data.get("title", "")

    if not artist or not title:
        logger.warning("websearch_fallback: Insufficient data for websearch query")
        return state

    # Stub: Mock websearch result
    # In production, this would call Tavily API
    websearch_results = [
        {
            "title": f"{artist} - {title} (Discogs)",
            "url": "https://www.discogs.com/mock",
            "snippet": "Album information from Discogs",
            "relevance": 0.90,
        }
    ]

    state["websearch_results"] = websearch_results

    # Add websearch evidence
    evidence_chain = state.get("evidence_chain", [])
    websearch_evidence: Evidence = {
        "source": EvidenceType.WEBSEARCH,
        "confidence": 0.10,
        "data": {
            "query": f"{artist} {title}",
            "top_result": websearch_results[0] if websearch_results else None,
        },
        "timestamp": datetime.now(),
    }
    evidence_chain.append(websearch_evidence)
    state["evidence_chain"] = evidence_chain

    logger.info(f"websearch_fallback: Found {len(websearch_results)} results")

    return state


def confidence_gate_node(state: VinylState) -> VinylState:
    """
    Calculate overall confidence using 4-way weighting.

    Weights:
    - discogs: 0.45
    - musicbrainz: 0.25
    - vision: 0.20
    - websearch: 0.10

    Routes to auto_commit if confidence >= 0.85, else needs_review

    Returns:
        VinylState: Updated state with confidence and auto_commit flag
    """
    evidence_chain = state.get("evidence_chain", [])

    # Initialize weights dict (using string keys to match evidence source values)
    weights = {
        EvidenceType.DISCOGS: 0.45,
        EvidenceType.MUSICBRAINZ: 0.25,
        EvidenceType.VISION: 0.20,
        EvidenceType.WEBSEARCH: 0.10,
    }

    # Calculate weighted confidence
    total_confidence = 0.0
    total_weight = 0.0

    for evidence in evidence_chain:
        source = evidence.get("source")
        confidence = evidence.get("confidence", 0.0)
        # Convert source to EvidenceType enum if it's a string
        if isinstance(source, str):
            source_enum = EvidenceType(source)
        else:
            source_enum = source
        
        weight = weights.get(source_enum, 0.0)

        if weight > 0:
            total_confidence += confidence * weight
            total_weight += weight

    # Normalize if total_weight < 1.0 (missing sources)
    if total_weight > 0:
        final_confidence = total_confidence / total_weight
    else:
        final_confidence = 0.0

    state["confidence"] = final_confidence

    # Auto-commit if confidence >= 0.85
    state["auto_commit"] = final_confidence >= 0.85
    state["needs_review"] = not state["auto_commit"]

    logger.info(
        f"confidence_gate: Confidence={final_confidence:.2f}, "
        f"auto_commit={state['auto_commit']}"
    )

    return state


# ============================================================================
# GRAPH BUILDER
# ============================================================================


def build_agent_graph():
    """
    Build the 6-node LangGraph workflow.

    Graph Structure:
        START
          ↓
    validate_images
          ↓
    extract_features
          ↓
    vision_extraction
          ↓
    lookup_metadata
          ↓
    [if confidence < 0.75]
    websearch_fallback
          ↓
    confidence_gate
          ↓
    [if auto_commit]
    auto_commit → END
    [else]
    needs_review → END

    Returns:
        Compiled LangGraph workflow
    """
    graph = StateGraph(VinylState)

    # Add all 6 nodes
    graph.add_node("validate_images", validate_images_node)
    graph.add_node("extract_features", extract_features_node)
    graph.add_node("vision_extraction", vision_extraction_node)
    graph.add_node("lookup_metadata", lookup_metadata_node)
    graph.add_node("websearch_fallback", websearch_fallback_node)
    graph.add_node("confidence_gate", confidence_gate_node)

    # Add edges
    graph.add_edge(START, "validate_images")
    graph.add_edge("validate_images", "extract_features")
    graph.add_edge("extract_features", "vision_extraction")
    graph.add_edge("vision_extraction", "lookup_metadata")

    # Conditional edge: lookup_metadata → confidence_gate or websearch_fallback
    def route_from_lookup(state: VinylState) -> Literal["confidence_gate", "websearch_fallback"]:
        """
        Route based on evidence confidence.
        If confidence < 0.75, try websearch fallback.
        Otherwise, go straight to confidence_gate.
        """
        evidence_chain = state.get("evidence_chain", [])

        # Calculate preliminary confidence from primary sources
        preliminary_confidence = 0.0
        if evidence_chain:
            # Average of available sources
            preliminary_confidence = sum(e.get("confidence", 0) for e in evidence_chain) / len(
                evidence_chain
            )

        if preliminary_confidence < 0.75:
            logger.info(
                f"route_from_lookup: Preliminary confidence {preliminary_confidence:.2f} < 0.75, "
                "routing to websearch_fallback"
            )
            return "websearch_fallback"
        else:
            logger.info(
                f"route_from_lookup: Preliminary confidence {preliminary_confidence:.2f} >= 0.75, "
                "routing to confidence_gate"
            )
            return "confidence_gate"

    graph.add_conditional_edges("lookup_metadata", route_from_lookup)

    # websearch_fallback always goes to confidence_gate
    graph.add_edge("websearch_fallback", "confidence_gate")

    # Conditional edge: confidence_gate → auto_commit or needs_review
    def route_from_confidence_gate(state: VinylState) -> Literal["auto_commit", "needs_review"]:
        """Route based on final confidence score."""
        if state.get("auto_commit", False):
            logger.info("route_from_confidence_gate: Auto-commit approved")
            return "auto_commit"
        else:
            logger.info("route_from_confidence_gate: Manual review needed")
            return "needs_review"

    graph.add_conditional_edges("confidence_gate", route_from_confidence_gate)

    # Add terminal nodes
    graph.add_node("auto_commit", lambda x: x)  # Pass-through
    graph.add_node("needs_review", lambda x: x)  # Pass-through

    graph.add_edge("auto_commit", END)
    graph.add_edge("needs_review", END)

    # Compile with memory checkpointing
    return graph.compile(checkpointer=MemorySaver())


if __name__ == "__main__":
    """Quick test of graph builder."""
    logging.basicConfig(level=logging.INFO)

    graph = build_agent_graph()
    print("✓ Graph compiled successfully")
    print(f"✓ Graph nodes: {list(graph.nodes.keys())}")
