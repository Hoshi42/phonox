"""Pydantic request/response models for FastAPI endpoints."""

from typing import Optional, List, Dict, Any
from datetime import datetime
from enum import Enum
from pydantic import BaseModel, Field


class EvidenceSourceEnum(str, Enum):
    """Evidence source types."""
    VISION = "vision"
    DISCOGS = "discogs"
    MUSICBRAINZ = "musicbrainz"
    WEBSEARCH = "websearch"


class EvidenceModel(BaseModel):
    """Evidence item in the chain."""
    source: EvidenceSourceEnum
    confidence: float = Field(..., ge=0.0, le=1.0)
    data: Dict[str, Any]
    timestamp: datetime

    class Config:
        """Pydantic config."""
        json_schema_extra = {
            "example": {
                "source": "discogs",
                "confidence": 0.85,
                "data": {
                    "artist": "The Beatles",
                    "title": "Abbey Road",
                    "label": "Apple Records"
                },
                "timestamp": "2026-01-24T10:30:00"
            }
        }


class VinylMetadataModel(BaseModel):
    """Vinyl record metadata."""
    artist: str
    title: str
    year: Optional[int] = None
    label: str
    spotify_url: Optional[str] = None
    catalog_number: Optional[str] = None
    genres: List[str] = Field(default_factory=list)
    estimated_value_eur: Optional[float] = None
    estimated_value_usd: Optional[float] = None

    class Config:
        """Pydantic config."""
        json_schema_extra = {
            "example": {
                "artist": "The Beatles",
                "title": "Abbey Road",
                "year": 1969,
                "label": "Apple Records",
                "spotify_url": "https://open.spotify.com/album/0ETFjACtuP2ADo6LFhL6HN",
                "catalog_number": "PCS 7088",
                "genres": ["Rock", "Pop"]
            }
        }


class VinylIdentifyRequest(BaseModel):
    """Request body for vinyl identification."""
    image_paths: List[str] = Field(..., min_length=1, max_length=5)
    user_notes: Optional[str] = None

    class Config:
        """Pydantic config."""
        json_schema_extra = {
            "example": {
                "image_paths": ["/path/to/image1.jpg", "/path/to/image2.png"],
                "user_notes": "Black vinyl, original pressing"
            }
        }


class VinylIdentifyResponse(BaseModel):
    """Response for vinyl identification request."""
    record_id: str
    status: str  # "pending", "processing", "complete", "failed"
    message: str
    job_id: Optional[str] = None

    class Config:
        """Pydantic config."""
        json_schema_extra = {
            "example": {
                "record_id": "550e8400-e29b-41d4-a716-446655440000",
                "status": "processing",
                "message": "Vinyl identification started",
                "job_id": "job_12345"
            }
        }


class VinylRecordResponse(BaseModel):
    """Full vinyl record response."""
    record_id: str
    created_at: datetime
    updated_at: datetime
    status: str  # "pending", "processing", "complete", "failed"
    metadata: Optional[VinylMetadataModel] = None
    evidence_chain: List[EvidenceModel] = Field(default_factory=list)
    confidence: float = Field(default=0.0, ge=0.0, le=1.0)
    auto_commit: bool = False
    needs_review: bool = True
    error: Optional[str] = None
    user_notes: Optional[str] = None

    class Config:
        """Pydantic config."""
        json_schema_extra = {
            "example": {
                "record_id": "550e8400-e29b-41d4-a716-446655440000",
                "created_at": "2026-01-24T10:00:00",
                "updated_at": "2026-01-24T10:05:00",
                "status": "complete",
                "metadata": {
                    "artist": "The Beatles",
                    "title": "Abbey Road",
                    "year": 1969,
                    "label": "Apple Records"
                },
                "evidence_chain": [],
                "confidence": 0.92,
                "auto_commit": True,
                "needs_review": False
            }
        }


class ReviewRequest(BaseModel):
    """Manual review correction request."""
    artist: Optional[str] = None
    title: Optional[str] = None
    year: Optional[int] = None
    label: Optional[str] = None
    spotify_url: Optional[str] = None
    catalog_number: Optional[str] = None
    genres: Optional[List[str]] = None
    notes: Optional[str] = None

    class Config:
        """Pydantic config."""
        json_schema_extra = {
            "example": {
                "artist": "The Beatles",
                "title": "Abbey Road (Remaster)",
                "year": 2009,
                "label": "Apple Records",
                "notes": "2009 remaster, Japan edition"
            }
        }


class HealthCheckResponse(BaseModel):
    """Health check response."""
    status: str = "healthy"
    version: str = "1.0.0"
    timestamp: datetime
    dependencies: Dict[str, str]

    class Config:
        """Pydantic config."""
        json_schema_extra = {
            "example": {
                "status": "healthy",
                "version": "1.0.0",
                "timestamp": "2026-01-24T10:30:00",
                "dependencies": {
                    "database": "connected",
                    "claude_api": "available",
                    "tavily_api": "available"
                }
            }
        }


class ErrorResponse(BaseModel):
    """Standard error response."""
    error: str
    detail: Optional[str] = None
    code: Optional[str] = None
    timestamp: datetime = Field(default_factory=datetime.now)

    class Config:
        """Pydantic config."""
        json_schema_extra = {
            "example": {
                "error": "Invalid request",
                "detail": "Missing required field: image_paths",
                "code": "VALIDATION_ERROR",
                "timestamp": "2026-01-24T10:30:00"
            }
        }


class ChatMessage(BaseModel):
    """Chat message model."""
    role: str  # "user" or "assistant"
    content: str
    timestamp: datetime = Field(default_factory=datetime.now)
    metadata: Optional[Dict[str, Any]] = None


class ChatRequest(BaseModel):
    """Chat message request."""
    message: str = Field(..., min_length=1, max_length=2000)
    metadata: Optional[Dict[str, str]] = None  # e.g. {"pressing": "first", "condition": "VG+"}

    class Config:
        """Pydantic config."""
        json_schema_extra = {
            "example": {
                "message": "This is actually a 1987 Japanese remaster, not the original 1969 pressing",
                "metadata": {
                    "pressing_year": "1987",
                    "country": "Japan"
                }
            }
        }


class ChatResponse(BaseModel):
    """Chat response with updated record info."""
    record_id: str
    message: str  # Agent's response
    updated_metadata: Optional[VinylMetadataModel] = None
    confidence: float = Field(default=0.0, ge=0.0, le=1.0)
    requires_review: bool = False
    chat_history: List[ChatMessage] = Field(default_factory=list)
    timestamp: datetime = Field(default_factory=datetime.now)

    class Config:
        """Pydantic config."""
        json_schema_extra = {
            "example": {
                "record_id": "550e8400-e29b-41d4-a716-446655440000",
                "message": "Got it! I've updated the record to 1987 Japanese remaster. Confidence is now 0.95.",
                "updated_metadata": {
                    "artist": "The Beatles",
                    "title": "Abbey Road",
                    "year": 1987,
                    "label": "Apple Records",
                    "genres": ["Rock"]
                },
                "confidence": 0.95,
                "requires_review": False,
                "chat_history": []
            }
        }

