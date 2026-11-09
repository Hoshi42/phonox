"""Stores the latest collection analysis per user so it can be reopened at any time."""

import logging
import math
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, ConfigDict, Field, field_validator
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from backend.database import CollectionAnalysis, get_db

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/analysis", tags=["analysis"])


class AnalysisInput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    summary: str = Field(min_length=1, max_length=100_000)
    record_count: int = Field(ge=0, le=1_000_000)
    total_value_eur: float | None = Field(default=None, ge=0)

    @field_validator("summary")
    @classmethod
    def not_blank(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("The analysis cannot be blank")
        return value

    @field_validator("total_value_eur")
    @classmethod
    def finite(cls, value: float | None) -> float | None:
        if value is not None and not math.isfinite(value):
            raise ValueError("The total value must be a finite number")
        return value


class AnalysisResponse(BaseModel):
    user_tag: str
    summary: str
    record_count: int
    total_value_eur: float | None
    created_at: datetime


def user_scope(user_tag: str = Query(min_length=1, max_length=50)) -> str:
    if not user_tag.strip():
        raise HTTPException(400, "A collection user must be selected.")
    return user_tag


def respond(row: CollectionAnalysis) -> AnalysisResponse:
    return AnalysisResponse(user_tag=row.user_tag, summary=row.summary, record_count=row.record_count,
                            total_value_eur=row.total_value_eur, created_at=row.created_at)


@router.get("", response_model=AnalysisResponse)
def latest(user_tag: str = Depends(user_scope), db: Session = Depends(get_db)):
    row = db.query(CollectionAnalysis).filter_by(user_tag=user_tag).first()
    if row is None:
        raise HTTPException(404, "No analysis has been saved for this user.")
    return respond(row)


@router.put("", response_model=AnalysisResponse)
def save(analysis: AnalysisInput, user_tag: str = Depends(user_scope), db: Session = Depends(get_db)):
    """Replaces the user's previous analysis; only the latest one is kept."""
    for _ in range(2):
        row = db.query(CollectionAnalysis).filter_by(user_tag=user_tag).first()
        if row is None:
            row = CollectionAnalysis(user_tag=user_tag)
            db.add(row)
        row.summary, row.record_count = analysis.summary, analysis.record_count
        row.total_value_eur, row.created_at = analysis.total_value_eur, datetime.utcnow()
        try:
            db.commit()
            db.refresh(row)
            return respond(row)
        except IntegrityError:
            # A concurrent save for the same user created the row first; update it instead.
            db.rollback()
    logger.error("Analysis could not be saved for user %s", user_tag)
    raise HTTPException(409, "The analysis could not be saved. Please try again.")
