"""
Tests for Phonox Agent State Models

Tests TypedDict definitions, state creation, mutation, and
confidence scoring calculations.
"""

import pytest
from datetime import datetime, timedelta
from typing import Any
from backend.agent.state import (
    Evidence,
    VinylMetadata,
    VinylState,
    CONFIDENCE_WEIGHTS,
    CONFIDENCE_THRESHOLDS,
    calculate_overall_confidence,
)


class TestEvidenceType:
    """Test Evidence TypedDict structure and validation."""
    
    def test_evidence_creation_valid(self):
        """Evidence dict can be created with all required fields."""
        now = datetime.now()
        evidence: Evidence = {
            "source": "discogs",
            "confidence": 0.95,
            "data": {"artist": "Pink Floyd", "album": "Dark Side"},
            "timestamp": now,
        }
        
        assert evidence["source"] == "discogs"
        assert evidence["confidence"] == 0.95
        assert evidence["data"]["artist"] == "Pink Floyd"
        assert evidence["timestamp"] == now
    
    def test_evidence_sources_recognized(self):
        """Evidence can be created with all recognized sources."""
        now = datetime.now()
        valid_sources = ["discogs", "musicbrainz", "image", "vision", "websearch", "user_input"]
        
        for source in valid_sources:
            evidence: Evidence = {
                "source": source,
                "confidence": 0.80,
                "data": {},
                "timestamp": now,
            }
            assert evidence["source"] == source
    
    def test_evidence_confidence_range(self):
        """Confidence scores should be in valid range."""
        now = datetime.now()
        
        # Valid boundaries
        for conf in [0.0, 0.5, 0.95, 1.0]:
            evidence: Evidence = {
                "source": "discogs",
                "confidence": conf,
                "data": {},
                "timestamp": now,
            }
            assert 0.0 <= evidence["confidence"] <= 1.0


class TestVinylMetadataType:
    """Test VinylMetadata TypedDict structure."""
    
    def test_vinyl_metadata_creation(self):
        """VinylMetadata dict can be created with all fields."""
        now = datetime.now()
        evidence_list: list[Evidence] = [
            {
                "source": "discogs",
                "confidence": 0.95,
                "data": {"id": "123"},
                "timestamp": now,
            }
        ]
        
        metadata: VinylMetadata = {
            "artist": "The Beatles",
            "title": "Abbey Road",
            "year": 1969,
            "label": "Apple Records",
            "catalog_number": "PCS 7088",
            "genres": ["Rock", "Pop"],
            "evidence": evidence_list,
            "overall_confidence": 0.95,
        }
        
        assert metadata["artist"] == "The Beatles"
        assert metadata["title"] == "Abbey Road"
        assert metadata["year"] == 1969
        assert metadata["label"] == "Apple Records"
        assert metadata["catalog_number"] == "PCS 7088"
        assert metadata["genres"] == ["Rock", "Pop"]
        assert len(metadata["evidence"]) == 1
        assert metadata["overall_confidence"] == 0.95
    
    def test_vinyl_metadata_optional_year(self):
        """year field can be None."""
        now = datetime.now()
        metadata: VinylMetadata = {
            "artist": "Unknown Artist",
            "title": "Unknown Title",
            "year": None,
            "label": "Independent",
            "catalog_number": None,
            "genres": [],
            "evidence": [],
            "overall_confidence": 0.0,
        }
        
        assert metadata["year"] is None
        assert metadata["catalog_number"] is None


class TestVinylStateType:
    """Test VinylState TypedDict and state transitions."""
    
    def test_vinyl_state_pending(self):
        """Initial state is 'pending'."""
        state: VinylState = {
            "images": ["base64_image_1", "base64_image_2"],
            "metadata": None,
            "evidence_chain": [],
            "status": "pending",
            "error": None,
        }
        
        assert state["status"] == "pending"
        assert state["metadata"] is None
        assert state["error"] is None
        assert len(state["images"]) == 2
    
    def test_vinyl_state_processing(self):
        """State can transition to 'processing'."""
        now = datetime.now()
        evidence: Evidence = {
            "source": "image",
            "confidence": 0.75,
            "data": {"features": [0.1, 0.2, 0.3]},
            "timestamp": now,
        }
        
        state: VinylState = {
            "images": ["base64_image"],
            "metadata": None,
            "evidence_chain": [evidence],
            "status": "processing",
            "error": None,
        }
        
        assert state["status"] == "processing"
        assert len(state["evidence_chain"]) == 1
    
    def test_vinyl_state_complete(self):
        """State can transition to 'complete' with metadata."""
        now = datetime.now()
        evidence_list: list[Evidence] = [
            {
                "source": "discogs",
                "confidence": 0.95,
                "data": {"id": "456"},
                "timestamp": now,
            }
        ]
        
        metadata: VinylMetadata = {
            "artist": "Pink Floyd",
            "title": "Dark Side of the Moon",
            "year": 1973,
            "label": "Harvest",
            "catalog_number": "SHVL 804",
            "genres": ["Rock", "Progressive"],
            "evidence": evidence_list,
            "overall_confidence": 0.95,
        }
        
        state: VinylState = {
            "images": ["base64_image"],
            "metadata": metadata,
            "evidence_chain": evidence_list,
            "status": "complete",
            "error": None,
        }
        
        assert state["status"] == "complete"
        assert state["metadata"] is not None
        assert state["metadata"]["artist"] == "Pink Floyd"
        assert state["error"] is None
    
    def test_vinyl_state_failed(self):
        """State can transition to 'failed' with error message."""
        state: VinylState = {
            "images": ["base64_image"],
            "metadata": None,
            "evidence_chain": [],
            "status": "failed",
            "error": "Image quality too low for feature extraction",
        }
        
        assert state["status"] == "failed"
        assert state["error"] is not None
        assert "Image quality" in state["error"]


class TestConfidenceCalculation:
    """Test confidence score calculation logic."""
    
    def test_calculate_confidence_empty_list(self):
        """Empty evidence list returns 0.0 confidence."""
        confidence = calculate_overall_confidence([])
        assert confidence == 0.0
    
    def test_calculate_confidence_single_source(self):
        """Single source returns its confidence score."""
        now = datetime.now()
        evidence: list[Evidence] = [
            {
                "source": "discogs",
                "confidence": 0.85,
                "data": {},
                "timestamp": now,
            }
        ]
        
        confidence = calculate_overall_confidence(evidence)
        # With weight 0.5, contribution is 0.85 * 0.5 = 0.425
        # Total weight is 0.5, so result is 0.425 / 0.5 = 0.85
        assert confidence == pytest.approx(0.85, rel=0.01)
    
    def test_calculate_confidence_multiple_sources(self):
        """Multiple sources are weighted correctly."""
        now = datetime.now()
        evidence: list[Evidence] = [
            {
                "source": "discogs",
                "confidence": 0.95,
                "data": {},
                "timestamp": now,
            },
            {
                "source": "musicbrainz",
                "confidence": 0.80,
                "data": {},
                "timestamp": now,
            },
        ]
        
        confidence = calculate_overall_confidence(evidence)
        # discogs: 0.95 * 0.50 = 0.475
        # musicbrainz: 0.80 * 0.30 = 0.240
        # Total: 0.715 / 0.80 = 0.89375
        expected = (0.95 * 0.50 + 0.80 * 0.30) / 0.80
        assert confidence == pytest.approx(expected, rel=0.01)
    
    def test_calculate_confidence_all_sources(self):
        """All four sources weighted together."""
        now = datetime.now()
        evidence: list[Evidence] = [
            {
                "source": "discogs",
                "confidence": 0.95,
                "data": {},
                "timestamp": now,
            },
            {
                "source": "musicbrainz",
                "confidence": 0.80,
                "data": {},
                "timestamp": now,
            },
            {
                "source": "vision",
                "confidence": 0.70,
                "data": {},
                "timestamp": now,
            },
            {
                "source": "websearch",
                "confidence": 0.65,
                "data": {},
                "timestamp": now,
            },
        ]
        
        confidence = calculate_overall_confidence(evidence)
        # discogs: 0.95 * 0.45 = 0.4275
        # musicbrainz: 0.80 * 0.25 = 0.200
        # vision: 0.70 * 0.20 = 0.140
        # websearch: 0.65 * 0.10 = 0.065
        # Total: 0.8325 / 1.00 = 0.8325
        expected = (0.95 * 0.45 + 0.80 * 0.25 + 0.70 * 0.20 + 0.65 * 0.10) / 1.0
        assert confidence == pytest.approx(expected, rel=0.01)
    
    def test_calculate_confidence_unrecognized_source(self):
        """Unrecognized source contributes 0.0 to confidence."""
        now = datetime.now()
        evidence: list[Evidence] = [
            {
                "source": "user_input",  # Not in CONFIDENCE_WEIGHTS
                "confidence": 0.90,
                "data": {},
                "timestamp": now,
            }
        ]
        
        confidence = calculate_overall_confidence(evidence)
        # user_input has weight 0, so contribution is 0
        assert confidence == 0.0
    
    def test_calculate_confidence_mixed_recognized_unrecognized(self):
        """Mix of recognized and unrecognized sources."""
        now = datetime.now()
        evidence: list[Evidence] = [
            {
                "source": "discogs",
                "confidence": 0.95,
                "data": {},
                "timestamp": now,
            },
            {
                "source": "user_input",  # Not weighted
                "confidence": 0.90,
                "data": {},
                "timestamp": now,
            },
        ]
        
        confidence = calculate_overall_confidence(evidence)
        # Only discogs counts: 0.95 * 0.45 / 0.45 = 0.95
        assert confidence == pytest.approx(0.95, rel=0.01)
    
    def test_calculate_confidence_vision_source(self):
        """Vision (Claude 3) source contributes correctly."""
        now = datetime.now()
        evidence: list[Evidence] = [
            {
                "source": "vision",
                "confidence": 0.80,
                "data": {"artist": "Pink Floyd", "confidence": 0.80},
                "timestamp": now,
            }
        ]
        
        confidence = calculate_overall_confidence(evidence)
        # vision: 0.80 * 0.20 / 0.20 = 0.80
        assert confidence == pytest.approx(0.80, rel=0.01)
    
    def test_calculate_confidence_websearch_source(self):
        """Websearch source contributes with lower weight."""
        now = datetime.now()
        evidence: list[Evidence] = [
            {
                "source": "discogs",
                "confidence": 0.85,
                "data": {},
                "timestamp": now,
            },
            {
                "source": "websearch",
                "confidence": 0.70,
                "data": {"url": "https://example.com"},
                "timestamp": now,
            },
        ]
        
        confidence = calculate_overall_confidence(evidence)
        # discogs: 0.85 * 0.45 = 0.3825
        # websearch: 0.70 * 0.10 = 0.07
        # Total: 0.4525 / 0.55 = 0.8227
        expected = (0.85 * 0.45 + 0.70 * 0.10) / 0.55
        assert confidence == pytest.approx(expected, rel=0.01)


class TestConfidenceThresholds:
    """Test confidence threshold definitions."""
    
    def test_thresholds_values(self):
        """Thresholds are defined and reasonable."""
        assert CONFIDENCE_THRESHOLDS["auto_commit"] == 0.90
        assert CONFIDENCE_THRESHOLDS["recommended_review"] == 0.85
        assert CONFIDENCE_THRESHOLDS["manual_review"] == 0.70
        assert CONFIDENCE_THRESHOLDS["manual_entry"] == 0.50
    
    def test_thresholds_ordered(self):
        """Thresholds are in logical order (decreasing)."""
        vals = list(CONFIDENCE_THRESHOLDS.values())
        assert vals == sorted(vals, reverse=True)
    
    def test_classification_by_threshold(self):
        """Scores classify correctly against thresholds."""
        cases = [
            (0.95, "auto_commit"),
            (0.87, "recommended_review"),
            (0.75, "manual_review"),
            (0.55, "manual_entry"),
            (0.30, None),  # Below all thresholds
        ]
        
        for score, expected_category in cases:
            if score >= CONFIDENCE_THRESHOLDS["auto_commit"]:
                category = "auto_commit"
            elif score >= CONFIDENCE_THRESHOLDS["recommended_review"]:
                category = "recommended_review"
            elif score >= CONFIDENCE_THRESHOLDS["manual_review"]:
                category = "manual_review"
            elif score >= CONFIDENCE_THRESHOLDS["manual_entry"]:
                category = "manual_entry"
            else:
                category = None
            
            assert category == expected_category


class TestConfidenceWeights:
    """Test confidence weight definitions."""
    
    def test_weights_sum_to_one(self):
        """Weights must sum to 1.0 for proper averaging."""
        total = sum(CONFIDENCE_WEIGHTS.values())
        assert total == pytest.approx(1.0, rel=0.01)
    
    def test_weights_values(self):
        """Weight values are reasonable."""
        assert CONFIDENCE_WEIGHTS["discogs"] == 0.45
        assert CONFIDENCE_WEIGHTS["musicbrainz"] == 0.25
        assert CONFIDENCE_WEIGHTS["vision"] == 0.20
        assert CONFIDENCE_WEIGHTS["websearch"] == 0.10
    
    def test_weights_reflect_reliability(self):
        """Weights decrease with less reliable sources."""
        reliability_order = ["discogs", "musicbrainz", "vision", "websearch"]
        weights = [CONFIDENCE_WEIGHTS[s] for s in reliability_order]
        assert weights == sorted(weights, reverse=True)
