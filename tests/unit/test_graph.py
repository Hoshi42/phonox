"""
Unit tests for LangGraph agent (Phase 1.1).

Tests for:
- validate_images_node
- extract_features_node
- vision_extraction_node
- lookup_metadata_node
- websearch_fallback_node
- confidence_gate_node
- Graph compilation and routing
"""

import pytest
from datetime import datetime
from typing import List
from unittest.mock import patch, MagicMock

from backend.agent.graph import (
    build_agent_graph,
    validate_images_node,
    extract_features_node,
    vision_extraction_node,
    lookup_metadata_node,
    websearch_fallback_node,
    confidence_gate_node,
)
from backend.agent.state import VinylState, Evidence, EvidenceType


# ============================================================================
# FIXTURES
# ============================================================================


@pytest.fixture
def empty_state() -> VinylState:
    """Empty initial state."""
    return {
        "images": [],
        "image_features": {},
        "vision_extraction": {},
        "evidence_chain": [],
        "confidence": 0.0,
        "auto_commit": False,
        "needs_review": False,
        "validation_passed": False,
        "validation_errors": [],
        "websearch_results": [],
    }


@pytest.fixture
def valid_images_state() -> VinylState:
    """State with 2 valid images."""
    return {
        "images": [
            {"format": "jpeg", "size_bytes": 1024 * 1024},  # 1MB
            {"format": "png", "size_bytes": 2 * 1024 * 1024},  # 2MB
        ],
        "image_features": {},
        "vision_extraction": {},
        "evidence_chain": [],
        "confidence": 0.0,
        "auto_commit": False,
        "needs_review": False,
        "validation_passed": False,
        "validation_errors": [],
        "websearch_results": [],
    }


# ============================================================================
# VALIDATE_IMAGES_NODE TESTS
# ============================================================================


def test_validate_images_no_images(empty_state):
    """Test validation fails with no images."""
    result = validate_images_node(empty_state)

    assert result["validation_passed"] is False
    assert len(result["validation_errors"]) > 0
    assert "No images" in result["validation_errors"][0]


def test_validate_images_too_many_images(empty_state):
    """Test validation fails with too many images."""
    empty_state["images"] = [{"format": "jpeg", "size_bytes": 1000} for _ in range(11)]
    result = validate_images_node(empty_state)

    assert result["validation_passed"] is False
    assert "Too many images" in result["validation_errors"][0]


def test_validate_images_valid_count(valid_images_state):
    """Test validation passes with valid image count."""
    result = validate_images_node(valid_images_state)

    assert result["validation_passed"] is True
    assert result["validation_errors"] == []


def test_validate_images_invalid_format(empty_state):
    """Test validation fails with invalid image format."""
    empty_state["images"] = [{"format": "bmp", "size_bytes": 1000}]  # BMP not supported
    result = validate_images_node(empty_state)

    assert result["validation_passed"] is False
    assert "Invalid format" in result["validation_errors"][0]


def test_validate_images_oversized(empty_state):
    """Test validation fails with oversized image."""
    empty_state["images"] = [{"format": "jpeg", "size_bytes": 11 * 1024 * 1024}]  # 11MB
    result = validate_images_node(empty_state)

    assert result["validation_passed"] is False
    assert "Too large" in result["validation_errors"][0]


# ============================================================================
# EXTRACT_FEATURES_NODE TESTS
# ============================================================================


def test_extract_features_skips_unvalidated(empty_state):
    """Test extract_features skips if images not validated."""
    empty_state["validation_passed"] = False
    result = extract_features_node(empty_state)

    assert result["image_features"] == {}


def test_extract_features_success(valid_images_state):
    """Test extract_features returns mock features."""
    valid_images_state["validation_passed"] = True
    result = extract_features_node(valid_images_state)

    assert "embeddings" in result["image_features"]
    assert "colors" in result["image_features"]
    assert "ocr_text" in result["image_features"]
    assert len(result["image_features"]["embeddings"]) == 2  # 2 images


def test_extract_features_embedding_dim(valid_images_state):
    """Test embeddings have correct dimension."""
    valid_images_state["validation_passed"] = True
    result = extract_features_node(valid_images_state)

    embeddings = result["image_features"]["embeddings"]
    assert all(len(emb) == 768 for emb in embeddings)  # ViT-base is 768-dim


# ============================================================================
# VISION_EXTRACTION_NODE TESTS
# ============================================================================


def test_vision_extraction_no_features(empty_state):
    """Test vision_extraction skips without image features."""
    result = vision_extraction_node(empty_state)

    assert result["vision_extraction"] == {}


def test_vision_extraction_success(valid_images_state):
    """Test vision_extraction returns structured metadata."""
    valid_images_state["validation_passed"] = True
    valid_images_state["image_features"] = {"embeddings": [[0.1] * 768] * 2}

    result = vision_extraction_node(valid_images_state)

    assert "artist" in result["vision_extraction"]
    assert "title" in result["vision_extraction"]
    assert "year" in result["vision_extraction"]
    assert "label" in result["vision_extraction"]
    assert "catalog_number" in result["vision_extraction"]
    assert "genres" in result["vision_extraction"]
    assert "confidence" in result["vision_extraction"]


# ============================================================================
# LOOKUP_METADATA_NODE TESTS
# ============================================================================


def test_lookup_metadata_adds_evidence(empty_state):
    """Test lookup_metadata adds Discogs and MusicBrainz evidence."""
    from unittest.mock import patch
    
    # Add vision extraction data
    empty_state["vision_extraction"] = {
        "artist": "The Beatles",
        "title": "Abbey Road",
        "year": 1969,
        "label": "Apple Records",
        "catalog_number": "PCS 7088",
        "genres": ["Rock"],
        "confidence": 0.75,
    }
    empty_state["evidence_chain"] = []  # Start with empty chain
    
    with patch("backend.agent.graph.lookup_metadata_from_both") as mock_lookup:
        mock_lookup.return_value = (
            {
                "artist": "The Beatles",
                "title": "Abbey Road",
                "year": 1969,
                "label": "Apple Records",
                "catalog_number": "PCS 7088",
                "genres": ["Rock"],
                "confidence": 0.85,
            },
            {
                "artist": "The Beatles",
                "title": "Abbey Road",
                "year": 1969,
                "label": "Apple Records",
                "catalog_number": "PCS 7088",
                "genres": ["Rock"],
                "confidence": 0.80,
            },
        )
        
        result = lookup_metadata_node(empty_state)

        assert len(result["evidence_chain"]) == 2
        assert result["evidence_chain"][0]["source"] == EvidenceType.DISCOGS
        assert result["evidence_chain"][1]["source"] == EvidenceType.MUSICBRAINZ


def test_lookup_metadata_evidence_structure(empty_state):
    """Test evidence has correct structure."""
    from unittest.mock import patch
    
    empty_state["vision_extraction"] = {
        "artist": "Test Artist",
        "title": "Test Album",
        "year": 2020,
        "label": "Test Label",
        "catalog_number": "TEST001",
        "genres": ["Rock"],
        "confidence": 0.75,
    }
    empty_state["evidence_chain"] = []
    
    with patch("backend.agent.graph.lookup_metadata_from_both") as mock_lookup:
        mock_lookup.return_value = (
            {
                "artist": "Test Artist",
                "title": "Test Album",
                "year": 2020,
                "label": "Test Label",
                "catalog_number": "TEST001",
                "genres": ["Rock"],
                "confidence": 0.85,
            },
            None,
        )
        
        result = lookup_metadata_node(empty_state)

        for evidence in result["evidence_chain"]:
            assert "source" in evidence
            assert "confidence" in evidence
            assert "data" in evidence
            assert evidence["confidence"] > 0


def test_lookup_metadata_preserves_existing_chain(empty_state):
    """Test lookup_metadata appends to existing chain."""
    from unittest.mock import patch
    
    existing_evidence: Evidence = {
        "source": EvidenceType.IMAGE,
        "confidence": 0.5,
        "data": {"type": "image"},
        "timestamp": datetime.now(),
    }
    empty_state["evidence_chain"] = [existing_evidence]
    empty_state["vision_extraction"] = {
        "artist": "Test Artist",
        "title": "Test Album",
        "year": 2020,
        "label": "Test Label",
        "catalog_number": "TEST001",
        "genres": ["Rock"],
        "confidence": 0.75,
    }

    with patch("backend.agent.graph.lookup_metadata_from_both") as mock_lookup:
        mock_lookup.return_value = (
            {
                "artist": "Test Artist",
                "title": "Test Album",
                "year": 2020,
                "label": "Test Label",
                "catalog_number": "TEST001",
                "genres": ["Rock"],
                "confidence": 0.85,
            },
            {
                "artist": "Test Artist",
                "title": "Test Album",
                "year": 2020,
                "label": "Test Label",
                "catalog_number": "TEST001",
                "genres": ["Rock"],
                "confidence": 0.80,
            },
        )
        
        result = lookup_metadata_node(empty_state)

        assert len(result["evidence_chain"]) == 3  # 1 existing + 2 new


# ============================================================================
# WEBSEARCH_FALLBACK_NODE TESTS
# ============================================================================


def test_websearch_fallback_skips_high_confidence(empty_state):
    """Test websearch_fallback skips when confidence >= 0.75."""
    empty_state["confidence"] = 0.80
    result = websearch_fallback_node(empty_state)

    assert result["websearch_results"] == []


def test_websearch_fallback_triggers_low_confidence(empty_state):
    """Test websearch_fallback triggers when confidence < 0.75."""
    empty_state["confidence"] = 0.60
    empty_state["vision_extraction"] = {"artist": "The Beatles", "title": "Abbey Road"}

    result = websearch_fallback_node(empty_state)

    assert len(result["websearch_results"]) > 0


def test_websearch_fallback_insufficient_data(empty_state):
    """Test websearch_fallback needs artist and title."""
    empty_state["confidence"] = 0.60
    empty_state["vision_extraction"] = {}  # No artist/title

    result = websearch_fallback_node(empty_state)

    assert result["websearch_results"] == []


def test_websearch_fallback_adds_evidence(empty_state):
    """Test websearch_fallback adds evidence to chain."""
    empty_state["confidence"] = 0.60
    empty_state["vision_extraction"] = {"artist": "The Beatles", "title": "Abbey Road"}

    result = websearch_fallback_node(empty_state)

    # Should have added websearch evidence
    websearch_evidence = [e for e in result["evidence_chain"] if e["source"] == EvidenceType.WEBSEARCH]
    assert len(websearch_evidence) > 0


# ============================================================================
# CONFIDENCE_GATE_NODE TESTS
# ============================================================================


def test_confidence_gate_empty_chain(empty_state):
    """Test confidence_gate with empty evidence chain."""
    result = confidence_gate_node(empty_state)

    assert result["confidence"] == 0.0
    assert result["auto_commit"] is False
    assert result["needs_review"] is True


def test_confidence_gate_single_source_high(empty_state):
    """Test confidence with single high-confidence source."""
    evidence: Evidence = {
        "source": EvidenceType.DISCOGS,
        "confidence": 0.90,
        "data": {},
        "timestamp": datetime.now(),
    }
    empty_state["evidence_chain"] = [evidence]

    result = confidence_gate_node(empty_state)

    assert result["confidence"] > 0
    assert result["auto_commit"] is True


def test_confidence_gate_multiple_sources(empty_state):
    """Test 4-way confidence weighting with multiple sources."""
    evidence_list: List[Evidence] = [
        {
            "source": EvidenceType.DISCOGS,
            "confidence": 0.90,
            "data": {},
            "timestamp": datetime.now(),
        },  # weight 0.45
        {
            "source": EvidenceType.MUSICBRAINZ,
            "confidence": 0.80,
            "data": {},
            "timestamp": datetime.now(),
        },  # weight 0.25
        {
            "source": EvidenceType.VISION,
            "confidence": 0.75,
            "data": {},
            "timestamp": datetime.now(),
        },  # weight 0.20
        {
            "source": EvidenceType.WEBSEARCH,
            "confidence": 0.60,
            "data": {},
            "timestamp": datetime.now(),
        },  # weight 0.10
    ]
    empty_state["evidence_chain"] = evidence_list

    result = confidence_gate_node(empty_state)

    # Expected: 0.90*0.45 + 0.80*0.25 + 0.75*0.20 + 0.60*0.10 = 0.405 + 0.200 + 0.150 + 0.060 = 0.815
    assert 0.80 <= result["confidence"] <= 0.85
    # At 0.815, this is < 0.85 threshold, so auto_commit should be False
    assert result["auto_commit"] is False


def test_confidence_gate_threshold_85(empty_state):
    """Test auto_commit threshold at 0.85."""
    # Confidence exactly at threshold
    evidence: Evidence = {
        "source": EvidenceType.DISCOGS,
        "confidence": 0.85,
        "data": {},
        "timestamp": datetime.now(),
    }
    empty_state["evidence_chain"] = [evidence]

    result = confidence_gate_node(empty_state)

    assert result["confidence"] >= 0.85
    assert result["auto_commit"] is True


def test_confidence_gate_below_threshold(empty_state):
    """Test needs_review when below threshold."""
    evidence: Evidence = {
        "source": EvidenceType.VISION,
        "confidence": 0.50,
        "data": {},
        "timestamp": datetime.now(),
    }  # weight 0.20, so 0.10 total
    empty_state["evidence_chain"] = [evidence]

    result = confidence_gate_node(empty_state)

    assert result["confidence"] < 0.85
    assert result["auto_commit"] is False
    assert result["needs_review"] is True


# ============================================================================
# GRAPH COMPILATION TESTS
# ============================================================================


def test_graph_compiles():
    """Test that graph compiles without errors."""
    graph = build_agent_graph()

    assert graph is not None
    print(f"Graph nodes: {list(graph.nodes.keys())}")


def test_graph_has_all_nodes():
    """Test graph includes all 6 core nodes."""
    graph = build_agent_graph()

    required_nodes = [
        "validate_images",
        "extract_features",
        "vision_extraction",
        "lookup_metadata",
        "websearch_fallback",
        "confidence_gate",
    ]

    graph_nodes = set(graph.nodes.keys())
    for node in required_nodes:
        assert node in graph_nodes, f"Missing node: {node}"


def test_graph_node_signatures():
    """Test all nodes are callable with VinylState."""
    graph = build_agent_graph()
    empty_state = {
        "images": [],
        "image_features": {},
        "vision_extraction": {},
        "evidence_chain": [],
        "confidence": 0.0,
        "auto_commit": False,
        "needs_review": False,
        "validation_passed": False,
        "validation_errors": [],
        "websearch_results": [],
    }

    # Test each node can be called (stubbed nodes only)
    stubbed_nodes = ["auto_commit", "needs_review"]
    for node_name in stubbed_nodes:
        if node_name in graph.nodes:
            node = graph.nodes[node_name]
            # Stub nodes should be passthrough
            result = node.invoke(empty_state)
            assert result is not None


# ============================================================================
# END-TO-END FLOW TESTS
# ============================================================================


def test_full_flow_high_confidence():
    """Test complete flow with high confidence outcome."""
    graph = build_agent_graph()

    # Start with valid images
    initial_state: VinylState = {
        "images": [
            {"format": "jpeg", "size_bytes": 1024 * 1024},
        ],
        "image_features": {},
        "vision_extraction": {},
        "evidence_chain": [],
        "confidence": 0.0,
        "auto_commit": False,
        "needs_review": False,
        "validation_passed": False,
        "validation_errors": [],
        "websearch_results": [],
    }

    # Run through graph with required checkpoint config
    result = graph.invoke(initial_state, config={"thread_id": "test-thread-1"})

    # Should reach auto_commit or needs_review
    assert "validation_passed" in result
    assert "confidence" in result
    assert isinstance(result["confidence"], float)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
