"""SQLAlchemy ORM models for database persistence."""

import json
from datetime import datetime
from typing import Optional, List, Dict, Any, Any as ColumnType
from sqlalchemy import Column, String, Float, Boolean, DateTime, Text, Integer
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import Session

Base = declarative_base()  # type: ignore[misc]


class VinylRecord(Base):  # type: ignore[misc,valid-type]
    """Vinyl record database model."""
    __tablename__ = "vinyl_records"

    # Primary key
    id: ColumnType = Column(String(36), primary_key=True, index=True)

    # Timestamps
    created_at: ColumnType = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at: ColumnType = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # Metadata
    artist: ColumnType = Column(String(255), nullable=True)
    title: ColumnType = Column(String(255), nullable=True)
    year: ColumnType = Column(Integer, nullable=True)
    label: ColumnType = Column(String(255), nullable=True)
    catalog_number: ColumnType = Column(String(50), nullable=True)
    genres: ColumnType = Column(Text, nullable=True)  # JSON array stored as string

    # Workflow state
    status: ColumnType = Column(String(50), default="pending", nullable=False, index=True)  # pending, processing, complete, failed
    validation_passed: ColumnType = Column(Boolean, default=False)
    image_features_extracted: ColumnType = Column(Boolean, default=False)

    # Confidence and routing
    confidence: ColumnType = Column(Float, default=0.0, nullable=False)
    auto_commit: ColumnType = Column(Boolean, default=False, nullable=False)
    needs_review: ColumnType = Column(Boolean, default=True, nullable=False)

    # Evidence chain (JSON)
    evidence_chain: ColumnType = Column(Text, nullable=True)  # JSON array

    # Error tracking
    error: ColumnType = Column(Text, nullable=True)

    # User input
    user_notes: ColumnType = Column(Text, nullable=True)

    def set_genres(self, genres: List[str]) -> None:
        """Set genres from list."""
        self.genres = json.dumps(genres)

    def get_genres(self) -> List[str]:
        """Get genres as list."""
        if not self.genres:
            return []
        return json.loads(self.genres)

    def set_evidence_chain(self, chain: List[Dict[str, Any]]) -> None:
        """Set evidence chain from list of dicts."""
        # Convert datetime objects to ISO format strings
        serializable_chain = []
        for evidence in chain:
            evidence_copy = evidence.copy()
            if isinstance(evidence_copy.get("timestamp"), datetime):
                evidence_copy["timestamp"] = evidence_copy["timestamp"].isoformat()
            serializable_chain.append(evidence_copy)
        self.evidence_chain = json.dumps(serializable_chain)

    def get_evidence_chain(self) -> List[Dict[str, Any]]:
        """Get evidence chain as list of dicts."""
        if not self.evidence_chain:
            return []
        return json.loads(self.evidence_chain)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "record_id": self.id,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "status": self.status,
            "metadata": {
                "artist": self.artist,
                "title": self.title,
                "year": self.year,
                "label": self.label,
                "catalog_number": self.catalog_number,
                "genres": self.get_genres(),
            },
            "evidence_chain": self.get_evidence_chain(),
            "confidence": self.confidence,
            "auto_commit": self.auto_commit,
            "needs_review": self.needs_review,
            "error": self.error,
            "user_notes": self.user_notes,
        }


def get_db() -> Session:
    """Dependency for getting database session."""
    # This will be configured in main.py
    pass


# Note: SessionLocal will be set up in main.py
SessionLocal = None  # type: ignore
