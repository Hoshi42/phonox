"""SQLAlchemy ORM models for database persistence."""

import json
import logging
import os
from datetime import datetime
from typing import Optional, List, Dict, Any, Any as ColumnType
from sqlalchemy import Column, String, Float, Boolean, DateTime, Text, Integer, LargeBinary, ForeignKey
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import Session, relationship
from sqlalchemy.dialects.postgresql import UUID
import uuid

Base = declarative_base()  # type: ignore[misc]

logger = logging.getLogger(__name__)


class VinylRecord(Base):  # type: ignore[misc,valid-type]
    """Vinyl record database model."""
    __tablename__ = "vinyl_records"

    # Primary key
    id: ColumnType = Column(String(36), primary_key=True, index=True, default=lambda: str(uuid.uuid4()))

    # Timestamps
    created_at: ColumnType = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at: ColumnType = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # Metadata
    artist: ColumnType = Column(String(255), nullable=True)
    title: ColumnType = Column(String(255), nullable=True)
    year: ColumnType = Column(Integer, nullable=True)
    label: ColumnType = Column(String(255), nullable=True)
    spotify_url: ColumnType = Column(String(500), nullable=True)
    catalog_number: ColumnType = Column(String(50), nullable=True)
    barcode: ColumnType = Column(String(20), nullable=True)  # UPC/EAN barcodes typically 12-13 digits
    genres: ColumnType = Column(Text, nullable=True)  # JSON array stored as string

    # Workflow state
    status: ColumnType = Column(String(50), default="pending", nullable=False, index=True)  # pending, processing, complete, failed
    validation_passed: ColumnType = Column(Boolean, default=False)
    image_features_extracted: ColumnType = Column(Boolean, default=False)

    # Confidence and routing
    confidence: ColumnType = Column(Float, default=0.0, nullable=False)
    auto_commit: ColumnType = Column(Boolean, default=False, nullable=False)
    needs_review: ColumnType = Column(Boolean, default=True, nullable=False)

    # Storage and workflow
    evidence_chain: ColumnType = Column(Text, nullable=True)  # JSON stored as string
    error: ColumnType = Column(Text, nullable=True)
    user_notes: ColumnType = Column(Text, nullable=True)

    # Register specific fields
    in_register: ColumnType = Column(Boolean, default=False, nullable=False)
    estimated_value_eur: ColumnType = Column(Float, nullable=True)
    condition: ColumnType = Column(String(50), nullable=True)  # poor, fair, good, excellent, near_mint
    user_tag: ColumnType = Column(String(50), nullable=True, index=True)  # Simple user identifier
    
    # Relationships
    images = relationship("VinylImage", back_populates="record", cascade="all, delete-orphan")

    def set_genres(self, genres: List[str]) -> None:
        """Set genres from list."""
        self.genres = json.dumps(genres)

    def get_genres(self) -> List[str]:
        """Get genres as list."""
        if not self.genres:
            return []
        try:
            return json.loads(self.genres)
        except (json.JSONDecodeError, TypeError):
            return []

    def set_evidence_chain(self, chain: List[Dict[str, Any]]) -> None:
        """Set evidence chain from list of dicts, handling circular references."""
        try:
            # Try direct serialization first
            self.evidence_chain = json.dumps(chain)
        except (ValueError, TypeError, RecursionError) as e:
            # Handle circular references or non-serializable objects
            logger.warning(f"Evidence chain serialization failed: {e}")
            serializable_chain = []
            for evidence in chain:
                try:
                    # Try to serialize each evidence individually
                    json.dumps(evidence)
                    serializable_chain.append(evidence)
                except (ValueError, TypeError, RecursionError):
                    # If this evidence has issues, create simplified version
                    serializable_chain.append({
                        "source": str(evidence.get("source", "unknown")),
                        "confidence": evidence.get("confidence", 0.0),
                        "timestamp": evidence.get("timestamp", datetime.now().isoformat()),
                        "error": "Serialization failed"
                    })
            try:
                self.evidence_chain = json.dumps(serializable_chain)
            except:
                # Ultimate fallback
                self.evidence_chain = json.dumps([])

    def get_evidence_chain(self) -> List[Dict[str, Any]]:
        """Get evidence chain as list of dicts."""
        if not self.evidence_chain:
            return []
        try:
            return json.loads(self.evidence_chain)
        except (json.JSONDecodeError, TypeError):
            return []

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        # Get image URLs from relationships
        image_urls = [f"/api/register/images/{img.id}" for img in self.images]
        
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
                "spotify_url": self.spotify_url,
                "catalog_number": self.catalog_number,
                "barcode": self.barcode,
                "genres": self.get_genres(),
                "estimated_value_eur": self.estimated_value_eur,
                "estimated_value_usd": getattr(self, 'estimated_value_usd', None),
                "condition": self.condition,
                "image_urls": image_urls,
            },
            "evidence_chain": self.get_evidence_chain(),
            "confidence": self.confidence,
            "auto_commit": self.auto_commit,
            "needs_review": self.needs_review,
            "error": self.error,
            "user_notes": self.user_notes,
        }


class VinylImage(Base):  # type: ignore[misc,valid-type]
    """Vinyl record image storage model."""
    __tablename__ = "vinyl_images"

    # Primary key
    id: ColumnType = Column(String(36), primary_key=True, index=True, default=lambda: str(uuid.uuid4()))
    
    # Foreign key
    record_id: ColumnType = Column(String(36), ForeignKey('vinyl_records.id'), nullable=False)
    
    # Image data
    filename: ColumnType = Column(String(255), nullable=False)
    content_type: ColumnType = Column(String(100), nullable=False)
    file_size: ColumnType = Column(Integer, nullable=False)
    file_path: ColumnType = Column(String(500), nullable=False)  # Path to file on disk
    
    # Metadata
    created_at: ColumnType = Column(DateTime, default=datetime.utcnow, nullable=False)
    is_primary: ColumnType = Column(Boolean, default=False, nullable=False)
    
    # Relationship
    record = relationship("VinylRecord", back_populates="images")
    
    def get_image_data(self) -> Optional[bytes]:
        """Get image data from disk."""
        if self.file_path and os.path.exists(self.file_path):
            try:
                with open(self.file_path, "rb") as f:
                    return f.read()
            except Exception:
                return None
        return None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "id": self.id,
            "record_id": self.record_id,
            "filename": self.filename,
            "content_type": self.content_type,
            "file_size": self.file_size,
            "created_at": self.created_at,
            "is_primary": self.is_primary,
        }

def get_db() -> Session:
    """Dependency for getting database session."""
    if SessionLocal is None:
        raise RuntimeError("Database session not initialized. Application startup failed.")
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# Note: SessionLocal will be set up in main.py
SessionLocal = None  # type: ignore
