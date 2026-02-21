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
import json
import os
from datetime import datetime
from typing import Literal, List, Dict, Any, Tuple, Optional

from langgraph.graph import StateGraph, START, END
from anthropic import Anthropic

from backend.agent.state import VinylState, Evidence, EvidenceType
from backend.agent.vision import extract_vinyl_metadata, extract_vinyl_metadata_with_retry
from backend.agent.metadata import lookup_metadata_from_both
from backend.agent.websearch import search_vinyl_metadata, search_vinyl_by_barcode, search_spotify_album

logger = logging.getLogger(__name__)

# Initialize Anthropic client for LLM-based aggregation
anthropic_client = Anthropic()


# ============================================================================
# LLM-BASED AGGREGATION (Simpler & More Intelligent)
# ============================================================================


def aggregate_with_llm(all_results: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Use Claude to intelligently aggregate metadata from multiple images.
    
    This is simpler than rule-based logic and leverages Claude's intelligence
    for conflict resolution and metadata merging.
    
    Args:
        all_results: List of metadata dicts from each image
    
    Returns:
        Aggregated metadata dict with all fields merged
    """
    if not all_results:
        return {}
    
    if len(all_results) == 1:
        # Only one image, no aggregation needed
        return all_results[0]
    
    logger.info(f"Using Claude to aggregate {len(all_results)} image results...")
    
    # Build prompt for Claude
    aggregation_prompt = f"""You are a vinyl record metadata expert. Multiple images of the same record have been analyzed separately, and you need to merge the results intelligently.

IMAGE ANALYSIS RESULTS:
{json.dumps(all_results, indent=2, default=str)}

TASK: Merge these results into a single, accurate metadata object.

RULES:
1. **Artist/Title**: Choose the result with highest confidence. If similar (e.g., "Pink Floyd" vs "PINK FLOYD"), normalize to standard capitalization.
2. **Year**: If all agree, use that. If conflict, choose highest confidence.
3. **Label**: Choose highest confidence value.
4. **Catalog Number**: If multiple found, include all (they might be different editions).
5. **Barcode**: Include all valid barcodes found (12-13 digits).
6. **Genres**: Merge all genres, remove duplicates, keep lowercase normalized.
7. **Condition**: Choose WORST condition seen across all images (most conservative assessment). Use Goldmine scale: M, NM, VG+, VG, G+, G, F, P.
8. **Confidence**: Calculate as weighted average of all image confidences.

If images conflict on key fields (artist/title), explain the conflict but choose the most confident value.

Return ONLY valid JSON:
{{{{
    "artist": "normalized artist name",
    "title": "normalized title",
    "year": 1973,
    "label": "label name",
    "catalog_number": "CAT123",
    "barcode": "724384260729",
    "genres": ["rock", "progressive rock"],
    "condition": "Near Mint (NM)",
    "condition_notes": "Minor sleeve wear visible",
    "all_barcodes": ["724384260729"],
    "all_catalog_numbers": ["CAT123", "CAT456"],
    "confidence": 0.88,
    "reasoning": "Brief explanation of key decisions made",
    "conflicts_resolved": ["Brief description of any conflicts and how resolved"]
}}}}"""
    
    try:
        aggregation_model = os.getenv("ANTHROPIC_AGGREGATION_MODEL", "claude-sonnet-4-6")
        response = anthropic_client.messages.create(
            model=aggregation_model,
            max_tokens=1500,
            temperature=0.3,  # Deterministic for consistent merging
            messages=[{"role": "user", "content": aggregation_prompt}]
        )
        
        response_text = response.content[0].text if response.content else ""
        
        # Parse JSON from response
        json_start = response_text.find("{")
        json_end = response_text.rfind("}") + 1
        
        if json_start == -1 or json_end == 0:
            logger.error("No JSON found in Claude aggregation response")
            # Fallback to simple merge
            return simple_merge_fallback(all_results)
        
        aggregated = json.loads(response_text[json_start:json_end])
        
        logger.info(f"Claude aggregation: {aggregated.get('artist')} / {aggregated.get('title')}")
        logger.info(f"  Confidence: {aggregated.get('confidence', 0.0):.2f}")
        logger.info(f"  Reasoning: {aggregated.get('reasoning', 'N/A')}")
        
        if aggregated.get('conflicts_resolved'):
            for conflict in aggregated['conflicts_resolved']:
                logger.info(f"  Resolved conflict: {conflict}")
        
        return aggregated
        
    except Exception as e:
        logger.error(f"LLM aggregation failed: {e}, falling back to simple merge")
        return simple_merge_fallback(all_results)


def simple_merge_fallback(all_results: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Simple fallback merge when LLM aggregation fails.
    Just picks the result with highest confidence.
    """
    if not all_results:
        return {}
    
    # Sort by confidence, pick highest
    sorted_results = sorted(all_results, key=lambda x: x.get('confidence', 0.0), reverse=True)
    best = sorted_results[0].copy()
    
    # Collect all barcodes and catalogs
    all_barcodes = set()
    all_catalogs = set()
    for r in all_results:
        if r.get('barcode'):
            all_barcodes.add(r['barcode'])
        if r.get('catalog_number'):
            all_catalogs.add(r['catalog_number'])
    
    best['all_barcodes'] = list(all_barcodes)
    best['all_catalog_numbers'] = list(all_catalogs)
    
    logger.info("Using simple fallback merge (highest confidence)")
    return best


def validate_metadata_quality(
    metadata: Dict[str, Any], 
    confidence_threshold: float = 0.5
) -> Tuple[bool, List[str]]:
    """
    Validate that extracted metadata meets quality standards.
    
    Args:
        metadata: Extracted metadata dict
        confidence_threshold: Minimum acceptable confidence (0.0-1.0)
    
    Returns:
        Tuple of (is_valid, list_of_issues)
    """
    issues = []
    
    # Check confidence threshold
    confidence = metadata.get('confidence', 0.0)
    if confidence < confidence_threshold:
        issues.append(
            f"Low confidence: {confidence:.2f} (threshold: {confidence_threshold:.2f})"
        )
    
    # Check for placeholder/unknown values
    placeholders = {'Unknown', 'N/A', 'UNKNOWN', 'TBD', '???', '', 'ERROR'}
    
    for field in ['artist', 'title', 'label']:
        value = metadata.get(field)
        if value in placeholders:
            issues.append(f"Field '{field}' is placeholder: '{value}'")
    
    # Validate year if present
    year = metadata.get('year')
    if year:
        try:
            year_int = int(year)
            if not (1900 <= year_int <= 2026):
                issues.append(f"Year out of valid range: {year_int}")
        except (ValueError, TypeError):
            issues.append(f"Year is not a valid integer: {year}")
    
    # Warn if no genres
    genres = metadata.get('genres', [])
    if not genres or len(genres) == 0:
        issues.append("No genres detected - analysis might be incomplete")
    
    # Check barcode format if present
    barcode = metadata.get('barcode')
    if barcode:
        barcode_digits = ''.join(c for c in str(barcode) if c.isdigit())
        if not (12 <= len(barcode_digits) <= 14):
            issues.append(
                f"Barcode format suspicious: {barcode} ({len(barcode_digits)} digits)"
            )
    
    is_valid = len(issues) == 0
    return is_valid, issues


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

    Cost: ~$0.027–$0.030 per image (Sonnet 4.5 pricing, incl. prompt + CoT output)

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
                
            # Call Claude 3 Sonnet for metadata extraction with retry logic
            logger.info(f"vision_extraction: Analyzing image {idx + 1} with Claude 3 Sonnet (format: {image_format})...")
            try:
                # Prepare image context for optimized prompts
                image_context = {
                    'image_index': idx + 1,
                    'total_images': len(images),
                    'previous_results': best_result  # Pass best result so far for context
                }
                
                result = extract_vinyl_metadata_with_retry(
                    image_base64=image_content,
                    image_format=image_format,
                    fallback_on_error=False,  # No fallback - we want real errors
                    max_retries=3,  # Retry up to 3 times
                    base_delay=1.0,  # Start with 1 second, then 2, then 4
                    image_context=image_context  # Pass context for optimized prompts
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
        
        # Multi-image aggregation: Let Claude intelligently merge all results
        if best_result and all_results:
            logger.info(f"vision_extraction: Aggregating {len(all_results)} image results using Claude...")
            
            # Use LLM-based aggregation for intelligent merging
            vision_results = aggregate_with_llm(all_results)
            
            # Preserve per-image results for reference
            vision_results["processed_images"] = len(all_results)
            vision_results["image_results"] = all_results
            
            # Collect all visible text from all images
            all_visible_text = []
            for result in all_results:
                if result.get("all_visible_text"):
                    all_visible_text.append(result["all_visible_text"])
            vision_results["all_visible_text"] = all_visible_text
            
            # Validate quality of aggregated metadata
            is_valid, quality_issues = validate_metadata_quality(vision_results, confidence_threshold=0.4)
            if not is_valid:
                logger.warning(f"vision_extraction: Quality issues detected: {quality_issues}")
                vision_results["_quality_issues"] = quality_issues
            
            logger.info(
                f"vision_extraction: FINAL RESULT - "
                f"{vision_results.get('artist', 'Unknown')} / {vision_results.get('title', 'Unknown')} "
                f"(confidence: {vision_results.get('confidence', 0.0):.2f})"
            )
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

    # Initialize weights dict from state module (using enum keys)
    weights = {
        EvidenceType.DISCOGS: 0.40,
        EvidenceType.MUSICBRAINZ: 0.20,
        EvidenceType.VISION: 0.18,
        EvidenceType.WEBSEARCH: 0.12,
        EvidenceType.IMAGE: 0.05,
        EvidenceType.USER_INPUT: 0.05,
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

    # Compile without checkpointer to avoid recursion limit issues
    # Checkpointer not needed for single-shot analysis
    return graph.compile()


if __name__ == "__main__":
    """Quick test of graph builder."""
    logging.basicConfig(level=logging.INFO)

    graph = build_agent_graph()
    print("✓ Graph compiled successfully")
    print(f"✓ Graph nodes: {list(graph.nodes.keys())}")
