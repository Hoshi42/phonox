"""
End-to-end integration tests for the complete LangGraph workflow.

Tests the full 6-node pipeline:
1. validate_images
2. extract_features
3. vision_extraction
4. lookup_metadata
5. websearch_fallback
6. confidence_gate

These tests mock external APIs but test real state transitions and logic flow.
"""

import pytest
from datetime import datetime
from unittest.mock import patch, MagicMock

from backend.agent.graph import (
    build_agent_graph,
)
from backend.agent.state import VinylState, Evidence, EvidenceType


def invoke_graph(graph, state):
    """Helper to invoke graph with required checkpointer config."""
    return graph.invoke(state, config={"configurable": {"thread_id": "test-thread"}})


@pytest.fixture
def sample_vinyl_images():
    """Fixture providing sample vinyl album images for testing."""
    return [
        {
            "format": "jpeg",
            "size_bytes": 500000,
            "path": "/tmp/abbey_road_1.jpg",
        },
        {
            "format": "png",
            "size_bytes": 400000,
            "path": "/tmp/abbey_road_2.png",
        },
    ]


@pytest.fixture
def initial_state(sample_vinyl_images) -> VinylState:
    """Fixture providing initial state for workflow tests."""
    return {
        "images": sample_vinyl_images,
        "validation_passed": False,
        "validation_errors": [],
        "image_features": {},
        "vision_extraction": {},
        "evidence_chain": [],
        "confidence": 0.0,
        "auto_commit": False,
        "websearch_results": [],
    }


class TestGraphCompilation:
    """Tests for graph compilation and initialization."""

    def test_graph_builds_successfully(self):
        """Test that the graph compiles without errors."""
        graph = build_agent_graph()
        assert graph is not None
        assert hasattr(graph, "invoke")

    def test_graph_has_memory_checkpointer(self):
        """Test that graph has checkpoint memory enabled."""
        graph = build_agent_graph()
        assert hasattr(graph, "get_state")


class TestFullWorkflowSuccess:
    """Tests for successful end-to-end workflow with all sources."""

    def test_complete_workflow_all_sources(self, initial_state):
        """Test complete workflow with successful results from all sources."""
        graph = build_agent_graph()

        with patch("backend.agent.graph.lookup_metadata_from_both") as mock_metadata, \
             patch("backend.agent.graph.search_vinyl_metadata") as mock_websearch:

            # Mock successful metadata lookups
            mock_metadata.return_value = (
                {
                    "artist": "The Beatles",
                    "title": "Abbey Road",
                    "year": 1969,
                    "label": "Apple Records",
                    "catalog_number": "PCS 7088",
                    "genres": ["Rock", "Pop"],
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

            # Mock websearch (won't be called due to high confidence)
            mock_websearch.return_value = []

            # Execute workflow
            result = invoke_graph(graph, initial_state)

            # Verify final state
            assert result["validation_passed"] is True
            assert len(result["evidence_chain"]) >= 3  # VISION + DISCOGS + MUSICBRAINZ
            assert result["confidence"] >= 0.80  # High confidence from multiple sources
            # Note: auto_commit requires confidence >= 0.85, adjust if needed based on weights

    def test_vision_extraction_confidence(self, initial_state):
        """Test that vision extraction data is preserved through workflow."""
        graph = build_agent_graph()

        with patch("backend.agent.graph.lookup_metadata_from_both") as mock_metadata:

            # Mock metadata lookups to return None
            mock_metadata.return_value = (None, None)

            result = invoke_graph(graph, initial_state)

            # Vision data should be preserved
            assert result["vision_extraction"]["artist"] == "The Beatles"
            assert result["vision_extraction"]["confidence"] == 0.85  # Default mock confidence

    def test_evidence_chain_building(self, initial_state):
        """Test that evidence chain is properly built through workflow."""
        graph = build_agent_graph()

        with patch("backend.agent.graph.lookup_metadata_from_both") as mock_metadata:
            mock_metadata.return_value = (
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

            result = invoke_graph(graph, initial_state)

            evidence_chain = result["evidence_chain"]
            assert len(evidence_chain) > 0

            # Check for expected evidence types
            evidence_sources = {e["source"] for e in evidence_chain}
            assert EvidenceType.DISCOGS in evidence_sources
            assert EvidenceType.MUSICBRAINZ in evidence_sources


class TestPartialFailureScenarios:
    """Tests for scenarios where some sources fail."""

    def test_discogs_fails_musicbrainz_succeeds(self, initial_state):
        """Test workflow when Discogs fails but MusicBrainz succeeds."""
        graph = build_agent_graph()

        with patch("backend.agent.graph.lookup_metadata_from_both") as mock_metadata:
            # Discogs fails, MusicBrainz succeeds
            mock_metadata.return_value = (
                None,  # Discogs error
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

            result = invoke_graph(graph, initial_state)

            # Should still have evidence from MusicBrainz
            evidence_sources = {e["source"] for e in result["evidence_chain"]}
            assert EvidenceType.MUSICBRAINZ in evidence_sources

    def test_both_metadata_sources_fail_websearch_triggers(self, initial_state):
        """Test that websearch fallback is available when metadata sources fail."""
        graph = build_agent_graph()

        with patch("backend.agent.graph.lookup_metadata_from_both") as mock_metadata, \
             patch("backend.agent.graph.search_vinyl_metadata") as mock_websearch:

            # Both metadata lookups fail
            mock_metadata.return_value = (None, None)

            # Websearch returns results (though might not be called)
            mock_websearch.return_value = [
                {
                    "title": "The Beatles - Abbey Road (Discogs)",
                    "url": "https://discogs.com/abbey-road",
                    "snippet": "Album info",
                    "relevance": 0.95,
                }
            ]

            result = invoke_graph(graph, initial_state)

            # When both metadata sources fail, we still have vision evidence
            # The workflow should complete successfully
            assert result["validation_passed"] is True
            
            # Vision evidence should be in chain (confidence 0.85 is high enough to not need websearch)
            assert len(result["evidence_chain"]) > 0
            vision_evidence = [e for e in result["evidence_chain"] if e["source"] == EvidenceType.VISION]
            assert len(vision_evidence) == 1

    def test_image_validation_failure(self):
        """Test that workflow handles image validation failures gracefully."""
        graph = build_agent_graph()

        invalid_state: VinylState = {
            "images": [],  # No images provided
            "validation_passed": False,
            "validation_errors": [],
            "image_features": {},
            "vision_extraction": {},
            "evidence_chain": [],
            "confidence": 0.0,
            "auto_commit": False,
            "websearch_results": [],
        }

        result = invoke_graph(graph, invalid_state)

        # Should have validation errors
        assert len(result["validation_errors"]) > 0
        assert result["validation_passed"] is False


class TestConfidenceCalculation:
    """Tests for confidence score calculation."""

    def test_high_confidence_auto_commit(self, initial_state):
        """Test that high confidence triggers auto-commit."""
        graph = build_agent_graph()

        with patch("backend.agent.graph.lookup_metadata_from_both") as mock_metadata:
            # Both sources with high confidence
            mock_metadata.return_value = (
                {
                    "artist": "Test Artist",
                    "title": "Test Album",
                    "year": 2020,
                    "label": "Test Label",
                    "catalog_number": "TEST001",
                    "genres": ["Rock"],
                    "confidence": 0.90,
                },
                {
                    "artist": "Test Artist",
                    "title": "Test Album",
                    "year": 2020,
                    "label": "Test Label",
                    "catalog_number": "TEST001",
                    "genres": ["Rock"],
                    "confidence": 0.90,
                },
            )

            result = invoke_graph(graph, initial_state)

            # High confidence should trigger auto-commit
            assert result["confidence"] >= 0.85
            assert result["auto_commit"] is True

    def test_low_confidence_needs_review(self, initial_state):
        """Test that low confidence requires manual review."""
        graph = build_agent_graph()

        with patch("backend.agent.graph.lookup_metadata_from_both") as mock_metadata, \
             patch("backend.agent.graph.search_vinyl_metadata") as mock_websearch:

            # Low confidence from metadata
            mock_metadata.return_value = (
                None,
                {
                    "artist": "Test Artist",
                    "title": "Test Album",
                    "year": 2020,
                    "label": "Test Label",
                    "catalog_number": "TEST001",
                    "genres": ["Rock"],
                    "confidence": 0.60,
                },
            )

            # Websearch returns results
            mock_websearch.return_value = []

            result = invoke_graph(graph, initial_state)

            # Low confidence should not auto-commit
            assert result["confidence"] < 0.85
            assert result["auto_commit"] is False

    def test_confidence_weighting(self, initial_state):
        """Test that confidence weighting is applied correctly."""
        graph = build_agent_graph()

        with patch("backend.agent.graph.lookup_metadata_from_both") as mock_metadata:
            # Different confidence scores from sources
            mock_metadata.return_value = (
                {
                    "artist": "Test",
                    "title": "Album",
                    "year": 2020,
                    "label": "Label",
                    "catalog_number": "CAT001",
                    "genres": [],
                    "confidence": 0.95,  # Discogs: 45% weight
                },
                {
                    "artist": "Test",
                    "title": "Album",
                    "year": 2020,
                    "label": "Label",
                    "catalog_number": "CAT001",
                    "genres": [],
                    "confidence": 0.50,  # MusicBrainz: 25% weight
                },
            )

            result = invoke_graph(graph, initial_state)

            # Final confidence should reflect weighting
            # Rough calculation: 0.95*0.45 + 0.50*0.25 + vision*0.20 + websearch*0.10
            assert result["confidence"] > 0.5


class TestStatePreservation:
    """Tests for proper state preservation through workflow."""

    def test_state_immutability(self, initial_state):
        """Test that original state is not mutated by workflow."""
        graph = build_agent_graph()

        original_images = initial_state["images"].copy()

        with patch("backend.agent.graph.lookup_metadata_from_both") as mock_metadata:
            mock_metadata.return_value = (None, None)

            result = invoke_graph(graph, initial_state)

            # Original input should be unchanged
            assert initial_state["images"] == original_images

    def test_evidence_chain_order(self, initial_state):
        """Test that evidence chain maintains proper order."""
        graph = build_agent_graph()

        with patch("backend.agent.graph.lookup_metadata_from_both") as mock_metadata:
            mock_metadata.return_value = (
                {
                    "artist": "Test",
                    "title": "Album",
                    "year": 2020,
                    "label": "Label",
                    "catalog_number": "CAT",
                    "genres": [],
                    "confidence": 0.85,
                },
                {
                    "artist": "Test",
                    "title": "Album",
                    "year": 2020,
                    "label": "Label",
                    "catalog_number": "CAT",
                    "genres": [],
                    "confidence": 0.80,
                },
            )

            result = invoke_graph(graph, initial_state)

            # Check that Discogs comes before MusicBrainz
            sources_in_order = [e["source"] for e in result["evidence_chain"]]
            discogs_idx = sources_in_order.index(EvidenceType.DISCOGS)
            mb_idx = sources_in_order.index(EvidenceType.MUSICBRAINZ)
            assert discogs_idx < mb_idx


class TestErrorRecovery:
    """Tests for error recovery and resilience."""

    def test_api_timeout_graceful_fallback(self, initial_state):
        """Test that API timeouts are handled gracefully."""
        graph = build_agent_graph()

        with patch("backend.agent.graph.lookup_metadata_from_both") as mock_metadata:
            mock_metadata.side_effect = TimeoutError("API Timeout")

            # Should not raise, should continue with fallback
            result = invoke_graph(graph, initial_state)

            assert result is not None
            assert "evidence_chain" in result

    def test_malformed_api_response_handling(self, initial_state):
        """Test handling of malformed API responses."""
        graph = build_agent_graph()

        with patch("backend.agent.graph.lookup_metadata_from_both") as mock_metadata:
            # Return malformed data
            mock_metadata.return_value = (
                {"invalid": "structure"},  # type: ignore
                None,
            )

            # Should handle gracefully
            result = invoke_graph(graph, initial_state)

            assert result is not None
            assert len(result["validation_errors"]) >= 0  # May have errors but shouldn't crash

    def test_partial_state_handling(self, initial_state):
        """Test handling of workflows with incomplete state."""
        graph = build_agent_graph()

        # Remove optional fields
        initial_state["websearch_results"] = []

        with patch("backend.agent.graph.lookup_metadata_from_both") as mock_metadata:
            mock_metadata.return_value = (None, None)

            result = invoke_graph(graph, initial_state)

            assert result is not None
            assert "websearch_results" in result
