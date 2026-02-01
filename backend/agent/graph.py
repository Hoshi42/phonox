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
from backend.agent.vision import extract_vinyl_metadata
from backend.agent.metadata import lookup_metadata_from_both
from backend.agent.websearch import search_vinyl_metadata, search_vinyl_by_barcode, search_spotify_album

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

    # Validate format and size
    valid_formats = {"jpeg", "jpg", "png", "webp", "gif"}
    validation_errors = []

    for idx, image in enumerate(images):
        if isinstance(image, dict):
            # Get format from either 'format' key or 'content_type' key
            fmt = image.get("format", "").lower()
            if not fmt and "content_type" in image:
                # Extract format from content_type (e.g., "image/jpeg" -> "jpeg")
                content_type = image.get("content_type", "").lower()
                if content_type.startswith("image/"):
                    fmt = content_type.replace("image/", "").replace("svg+xml", "svg")
            
            size = image.get("size_bytes", 0)
            filename = image.get("path", f"image_{idx}")
            
            logger.info(f"validate_images: Image {idx}: filename={filename}, format={fmt}, content_type={image.get('content_type')}, size={size}")

            if fmt and fmt not in valid_formats:
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

    Processes ALL images and aggregates results for better accuracy.
    Special focus on barcode detection and catalog numbers.

    Extracts:
    - Artist name
    - Album title
    - Release year
    - Label
    - Catalog number
    - Barcodes (UPC/EAN)
    - Genres

    Confidence: 0.20 weight in 4-way system

    Cost: ~$0.002 per image (Claude 3 Sonnet pricing)

    Returns:
        VinylState: Updated state with vision_extraction dict
    """
    if not state.get("validation_passed"):
        logger.warning("vision_extraction: Images not validated")
        return state

    images = state.get("images", [])

    if not images:
        logger.warning("vision_extraction: No images provided")
        return state

    # Process ALL images and aggregate results for better accuracy
    all_results = []
    best_confidence = 0.0
    best_result = None
    extraction_errors = []
    
    try:
        for idx, image in enumerate(images):
            logger.info(f"vision_extraction: Processing image {idx + 1}/{len(images)}: {image.get('path')}")
            
            # Extract image data
            image_content = image.get("content", "")
            image_format = image.get("content_type", "image/jpeg").replace("image/", "")
            
            if not image_content:
                logger.warning(f"vision_extraction: No content for image {idx + 1}")
                continue
                
            # Call Claude 3 Sonnet for metadata extraction
            logger.info(f"vision_extraction: Analyzing image {idx + 1} with Claude 3 Sonnet (format: {image_format})...")
            try:
                result = extract_vinyl_metadata(
                    image_base64=image_content,
                    image_format=image_format,
                    fallback_on_error=False  # No fallback - we want real errors
                )
            except Exception as e:
                error_msg = str(e)
                logger.error(f"vision_extraction: Error on image {idx + 1}: {error_msg}")
                extraction_errors.append({
                    "image": idx + 1,
                    "error": error_msg
                })
                continue
            
            result["image_index"] = idx + 1
            result["image_path"] = image.get("path", f"image_{idx + 1}")
            all_results.append(result)
            
            # Track the result with highest confidence
            confidence = result.get("confidence", 0.0)
            if confidence > best_confidence:
                best_confidence = confidence
                best_result = result
        
        # Multi-image aggregation: Combine results intelligently
        if best_result and all_results:
            vision_results = best_result.copy()
            
            # Aggregate data from all images for better coverage
            all_barcodes = set()
            all_catalog_numbers = set()
            all_visible_text = []
            
            for result in all_results:
                if result.get("barcode"):
                    all_barcodes.add(result["barcode"])
                if result.get("catalog_number"):
                    all_catalog_numbers.add(result["catalog_number"])
                if result.get("all_visible_text"):
                    all_visible_text.append(result["all_visible_text"])
            
            # If artist or title is "Unknown" but other images found something, use it
            if len(all_results) > 1:
                for result in all_results:
                    if vision_results.get("artist") == "Unknown" and result.get("artist") != "Unknown":
                        vision_results["artist"] = result.get("artist")
                    if vision_results.get("title") == "Unknown" and result.get("title") != "Unknown":
                        vision_results["title"] = result.get("title")
                    if not vision_results.get("year") and result.get("year"):
                        vision_results["year"] = result.get("year")
                    if vision_results.get("label") == "Unknown" and result.get("label") != "Unknown":
                        vision_results["label"] = result.get("label")
            
            # Add aggregated data
            vision_results["all_barcodes"] = list(all_barcodes)
            vision_results["all_catalog_numbers"] = list(all_catalog_numbers)
            vision_results["all_visible_text"] = all_visible_text
            vision_results["processed_images"] = len(all_results)
            vision_results["image_results"] = all_results
            
            logger.info(
                f"vision_extraction: FINAL RESULT - {vision_results.get('artist', 'Unknown')} / {vision_results.get('title', 'Unknown')} "
                f"(confidence: {vision_results.get('confidence', 0.0):.2f}, processed {len(all_results)} images)"
            )
            
            if all_barcodes:
                logger.info(f"vision_extraction: Found barcodes: {list(all_barcodes)}")
            if all_catalog_numbers:
                logger.info(f"vision_extraction: Found catalog numbers: {list(all_catalog_numbers)}")
            if all_visible_text:
                logger.info(f"vision_extraction: All visible text from images: {all_visible_text}")
        else:
            # All images failed - raise error with details
            if extraction_errors:
                error_summary = "; ".join([f"Image {e['image']}: {e['error']}" for e in extraction_errors])
                logger.error(f"vision_extraction: All images failed - {error_summary}")
                # Return the first error as the state error
                vision_results = {
                    "error": extraction_errors[0]["error"],
                    "all_errors": extraction_errors,
                    "artist": "ERROR",
                    "title": "ERROR",
                    "year": None,
                    "label": "ERROR",
                    "catalog_number": None,
                    "barcode": None,
                    "genres": [],
                    "confidence": 0.0,
                    "processed_images": len(images)
                }
            else:
                # No results at all
                logger.warning("vision_extraction: No images were processed")
                vision_results = {
                    "error": "No images were successfully analyzed",
                    "artist": "ERROR",
                    "title": "ERROR",
                    "year": None,
                    "label": "ERROR",
                    "catalog_number": None,
                    "barcode": None,
                    "genres": [],
                    "confidence": 0.0,
                    "processed_images": len(images)
                }

    except Exception as e:
        logger.error(f"vision_extraction: Failed to extract metadata: {e}")
        vision_results = {
            "artist": "Unknown",
            "title": "Unknown",
            "year": None,
            "label": "Unknown",
            "catalog_number": None,
            "barcode": None,
            "genres": [],
            "confidence": 0.0,
        }

    state["vision_extraction"] = vision_results

    # Add vision results to evidence chain for confidence calculation
    evidence_chain = state.get("evidence_chain", [])
    evidence_chain.append(
        Evidence(
            source=EvidenceType.VISION,
            data=vision_results,
            confidence=vision_results.get("confidence", 0.0),  # type: ignore
            timestamp=datetime.now(),
        )
    )
    state["evidence_chain"] = evidence_chain
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

    # Get artist + title from vision extraction
    vision_data = state.get("vision_extraction", {})
    artist = vision_data.get("artist", "")
    title = vision_data.get("title", "")

    if not artist or not title:
        logger.warning("lookup_metadata: Insufficient data for metadata lookup")
        return state

    try:
        # Query both Discogs and MusicBrainz
        discogs_result, musicbrainz_result = lookup_metadata_from_both(artist, title)

        # Add Discogs evidence if found
        if discogs_result:
            discogs_evidence: Evidence = {
                "source": EvidenceType.DISCOGS,
                "confidence": discogs_result.get("confidence", 0.85),
                "data": {
                    "artist": discogs_result.get("artist"),
                    "title": discogs_result.get("title"),
                    "year": discogs_result.get("year"),
                    "label": discogs_result.get("label"),
                    "catalog_number": discogs_result.get("catalog_number"),
                    "genres": discogs_result.get("genres", []),
                },
                "timestamp": datetime.now(),
            }
            evidence_chain.append(discogs_evidence)
            logger.info(f"lookup_metadata: Added Discogs evidence for {artist} - {title}")

        # Add MusicBrainz evidence if found
        if musicbrainz_result:
            musicbrainz_evidence: Evidence = {
                "source": EvidenceType.MUSICBRAINZ,
                "confidence": musicbrainz_result.get("confidence", 0.80),
                "data": {
                    "artist": musicbrainz_result.get("artist"),
                    "title": musicbrainz_result.get("title"),
                    "year": musicbrainz_result.get("year"),
                    "label": musicbrainz_result.get("label"),
                    "catalog_number": musicbrainz_result.get("catalog_number"),
                    "genres": musicbrainz_result.get("genres", []),
                },
                "timestamp": datetime.now(),
            }
            evidence_chain.append(musicbrainz_evidence)
            logger.info(f"lookup_metadata: Added MusicBrainz evidence for {artist} - {title}")

    except Exception as e:
        logger.error(f"lookup_metadata: Error querying metadata APIs: {e}")

    # Try to find Spotify album link
    try:
        spotify_result = search_spotify_album(artist, title)
        if spotify_result:
            # Add the Spotify URL to the vision_extraction data
            state["vision_extraction"]["spotify_url"] = spotify_result["spotify_url"]
            logger.info(f"lookup_metadata: Found Spotify album: {spotify_result['spotify_url']}")
    except Exception as e:
        logger.warning(f"lookup_metadata: Spotify search failed: {e}")

    state["evidence_chain"] = evidence_chain

    return state


def websearch_fallback_node(state: VinylState) -> VinylState:
    """
    Use Tavily API for websearch when primary sources don't have sufficient confidence.
    
    Enhanced with barcode-based search capabilities for more accurate results.

    Triggers when: confidence < 0.75

    Returns structured websearch results with:
    - Top match from search results
    - Confidence score
    - Barcode-specific results if available

    Returns:
        VinylState: Updated state with websearch_results (optional)
    """
    current_confidence = state.get("confidence", 0.0)

    # Only trigger if confidence is low
    if current_confidence >= 0.75:
        logger.info(f"websearch_fallback: Skipping (confidence {current_confidence:.2f} >= 0.75)")
        return state

    # Get artist + title from vision or metadata for search query
    vision_data = state.get("vision_extraction", {})
    artist = vision_data.get("artist", "")
    title = vision_data.get("title", "")
    barcode = vision_data.get("barcode", "")
    
    # Skip websearch if vision extraction failed (artist/title are ERROR)
    if artist == "ERROR" or title == "ERROR":
        logger.info("websearch_fallback: Skipping (vision extraction returned ERROR)")
        return state

    # Try barcode search first if available (more accurate)
    websearch_results = []
    search_strategy = "none"
    
    if barcode and len(barcode.strip()) >= 12:
        try:
            logger.info(f"websearch_fallback: Trying barcode search for: {barcode}")
            websearch_results = search_vinyl_by_barcode(
                barcode, 
                artist=artist or None, 
                title=title or None, 
                fallback_on_error=True
            )
            if websearch_results:
                search_strategy = "barcode"
                logger.info(f"websearch_fallback: Barcode search found {len(websearch_results)} results")
            else:
                logger.info("websearch_fallback: Barcode search returned no results, falling back to text search")
        except Exception as e:
            logger.warning(f"websearch_fallback: Barcode search failed: {e}")

    # Fallback to traditional artist/title search if barcode search didn't work
    if not websearch_results and artist and title:
        try:
            logger.info(f"websearch_fallback: Trying text search for: {artist} - {title}")
            websearch_results = search_vinyl_metadata(artist, title, fallback_on_error=True)
            if websearch_results:
                search_strategy = "text"
                logger.info(f"websearch_fallback: Text search found {len(websearch_results)} results")
        except Exception as e:
            logger.warning(f"websearch_fallback: Text search failed: {e}")

    if not websearch_results:
        logger.warning(f"websearch_fallback: No results found (tried barcode: {bool(barcode)}, text: {bool(artist and title)})")
        return state

    state["websearch_results"] = websearch_results

    # Add websearch evidence with enhanced metadata
    evidence_chain = state.get("evidence_chain", [])
    websearch_evidence: Evidence = {
        "source": EvidenceType.WEBSEARCH,
        # Barcode searches are more reliable than text searches
        "confidence": 0.65 if search_strategy == "barcode" else 0.50,
        "data": {
            "search_strategy": search_strategy,
            "query": f"barcode:{barcode}" if search_strategy == "barcode" else f"{artist} {title}",
            "barcode_used": barcode if search_strategy == "barcode" else None,
            "top_result": websearch_results[0] if websearch_results else None,
            "results_count": len(websearch_results),
        },
        "timestamp": datetime.now(),
    }
    evidence_chain.append(websearch_evidence)
    state["evidence_chain"] = evidence_chain

    logger.info(f"websearch_fallback: Found {len(websearch_results)} results using {search_strategy} search")

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
        # Skip websearch if vision extraction failed (artist/title are ERROR)
        vision_data = state.get("vision_extraction", {})
        artist = vision_data.get("artist", "")
        title = vision_data.get("title", "")
        
        if artist == "ERROR" or title == "ERROR":
            logger.info("route_from_lookup: Vision extraction failed (ERROR), skipping websearch")
            return "confidence_gate"
        
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
