"""API routes for vinyl identification."""

import logging
import uuid
from typing import List, Optional
from datetime import datetime

from fastapi import APIRouter, File, UploadFile, HTTPException, Depends, status
from sqlalchemy.orm import Session

from backend.main import app
from backend.database import VinylRecord, SessionLocal
from backend.api.models import (
    VinylIdentifyRequest,
    VinylIdentifyResponse,
    VinylRecordResponse,
    ReviewRequest,
    ErrorResponse,
    EvidenceModel,
    VinylMetadataModel,
    ChatRequest,
    ChatResponse,
    ChatMessage,
)
from backend.agent.graph import build_agent_graph
from backend.agent.state import VinylState

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1", tags=["vinyl"])


def get_db():
    """Get database session."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def _serialize_evidence_chain(evidence_chain: List[dict]) -> List[dict]:
    """Serialize evidence chain for JSON storage."""
    serialized = []
    for evidence in evidence_chain:
        evidence_copy = evidence.copy()
        # Convert datetime to ISO format string
        if isinstance(evidence_copy.get("timestamp"), datetime):
            evidence_copy["timestamp"] = evidence_copy["timestamp"].isoformat()
        # Convert enum to string if needed
        if hasattr(evidence_copy.get("source"), "value"):
            evidence_copy["source"] = evidence_copy["source"].value
        serialized.append(evidence_copy)
    return serialized


@router.post(
    "/identify",
    response_model=VinylIdentifyResponse,
    status_code=status.HTTP_202_ACCEPTED,
)
async def identify_vinyl(
    files: List[UploadFile] = File(...),
    user_notes: Optional[str] = None,
    db: Session = Depends(get_db),
) -> VinylIdentifyResponse:
    """
    Identify a vinyl record from images.

    Creates a new identification job and returns a job ID for polling.
    Accepts multipart form data with image files.
    """
    try:
        # Validate files
        if not files or len(files) == 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="At least one image file is required",
            )

        if len(files) > 5:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Maximum 5 images allowed",
            )

        # Create vinyl record in database
        record_id = str(uuid.uuid4())
        vinyl_record = VinylRecord(
            id=record_id,
            status="processing",
            user_notes=user_notes,
        )
        db.add(vinyl_record)
        db.commit()
        db.refresh(vinyl_record)

        logger.info(f"Created vinyl record {record_id} for identification")

        # For now, return immediately (in production, would queue async job)
        # In a real implementation, this would trigger an async Celery task
        try:
            # Initialize agent graph
            graph = build_agent_graph()

            # Create initial state
            # Convert uploaded files to image dicts with file content
            import base64
            image_dicts = []
            for file in files:
                content = await file.read()
                # Encode binary content as base64 string for processing
                file_content = base64.b64encode(content).decode('utf-8')
                image_dicts.append({
                    "path": file.filename or f"image_{len(image_dicts)}",
                    "content": file_content,
                    "content_type": file.content_type or "image/jpeg"
                })
            
            initial_state: VinylState = {  # type: ignore
                "images": image_dicts,
                "validation_passed": False,
                "image_features": {},
                "vision_extraction": {},
                "evidence_chain": [],
                "confidence": 0.0,
                "auto_commit": False,
                "needs_review": True,
            }

            # Invoke graph with config for checkpointer
            config = {"configurable": {"thread_id": record_id}}
            result_state = graph.invoke(initial_state, config=config)

            # Update record with results
            vinyl_record.status = "complete"
            vinyl_record.validation_passed = result_state.get("validation_passed", False)

            # Extract metadata
            if result_state.get("vision_extraction"):
                vision_data = result_state["vision_extraction"]
                vinyl_record.artist = vision_data.get("artist")
                vinyl_record.title = vision_data.get("title")
                vinyl_record.year = vision_data.get("year")
                vinyl_record.label = vision_data.get("label")
                vinyl_record.catalog_number = vision_data.get("catalog_number")
                if vision_data.get("genres"):
                    vinyl_record.set_genres(vision_data["genres"])

            # Store evidence chain
            evidence_chain = result_state.get("evidence_chain", [])
            if evidence_chain:
                vinyl_record.set_evidence_chain(_serialize_evidence_chain(evidence_chain))

            # Store confidence and routing flags
            vinyl_record.confidence = result_state.get("confidence", 0.0)
            vinyl_record.auto_commit = result_state.get("auto_commit", False)
            vinyl_record.needs_review = result_state.get("needs_review", True)

            # Handle errors
            if result_state.get("error"):
                vinyl_record.status = "failed"
                vinyl_record.error = result_state["error"]

            db.commit()
            db.refresh(vinyl_record)

            logger.info(
                f"Completed identification for {record_id}: "
                f"confidence={vinyl_record.confidence:.2f}, "
                f"auto_commit={vinyl_record.auto_commit}"
            )

        except Exception as e:
            logger.error(f"Error during identification: {e}")
            vinyl_record.status = "failed"
            vinyl_record.error = str(e)
            db.commit()

        return VinylIdentifyResponse(
            record_id=record_id,
            status="processing",
            message="Vinyl identification started",
            job_id=record_id,
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Unexpected error in identify_vinyl: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e),
        )


@router.get("/identify/{record_id}", response_model=VinylRecordResponse)
async def get_vinyl_record(
    record_id: str,
    db: Session = Depends(get_db),
) -> VinylRecordResponse:
    """Retrieve vinyl identification results."""
    try:
        # Query record from database
        vinyl_record = db.query(VinylRecord).filter(VinylRecord.id == record_id).first()

        if not vinyl_record:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Vinyl record {record_id} not found",
            )

        # Build response
        evidence_chain_dicts = vinyl_record.get_evidence_chain()
        evidence_chain = []
        for ev in evidence_chain_dicts:
            # Reconstruct EvidenceModel from stored dict
            try:
                evidence_chain.append(
                    EvidenceModel(
                        source=ev["source"],
                        confidence=ev["confidence"],
                        data=ev["data"],
                        timestamp=datetime.fromisoformat(ev["timestamp"]),
                    )
                )
            except Exception as e:
                logger.warning(f"Failed to parse evidence: {e}")

        metadata = None
        if vinyl_record.artist or vinyl_record.title:
            metadata = VinylMetadataModel(
                artist=vinyl_record.artist or "Unknown",
                title=vinyl_record.title or "Unknown",
                year=vinyl_record.year,
                label=vinyl_record.label or "Unknown",
                catalog_number=vinyl_record.catalog_number,
                genres=vinyl_record.get_genres(),
            )

        return VinylRecordResponse(
            record_id=vinyl_record.id,
            created_at=vinyl_record.created_at,
            updated_at=vinyl_record.updated_at,
            status=vinyl_record.status,
            metadata=metadata,
            evidence_chain=evidence_chain,
            confidence=vinyl_record.confidence,
            auto_commit=vinyl_record.auto_commit,
            needs_review=vinyl_record.needs_review,
            error=vinyl_record.error,
            user_notes=vinyl_record.user_notes,
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error retrieving record {record_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e),
        )


@router.post("/identify/{record_id}/review", response_model=VinylRecordResponse)
async def review_vinyl(
    record_id: str,
    review: ReviewRequest,
    db: Session = Depends(get_db),
) -> VinylRecordResponse:
    """
    Submit manual review corrections for a vinyl record.

    Updates the record with user-corrected metadata.
    """
    try:
        vinyl_record = db.query(VinylRecord).filter(VinylRecord.id == record_id).first()

        if not vinyl_record:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Vinyl record {record_id} not found",
            )

        # Update with reviewed metadata
        if review.artist:
            vinyl_record.artist = review.artist
        if review.title:
            vinyl_record.title = review.title
        if review.year:
            vinyl_record.year = review.year
        if review.label:
            vinyl_record.label = review.label
        if review.catalog_number:
            vinyl_record.catalog_number = review.catalog_number
        if review.genres:
            vinyl_record.set_genres(review.genres)
        if review.notes:
            vinyl_record.user_notes = review.notes

        # Mark as reviewed
        vinyl_record.needs_review = False
        vinyl_record.status = "complete"
        vinyl_record.updated_at = datetime.utcnow()

        db.commit()
        db.refresh(vinyl_record)

        logger.info(f"Updated vinyl record {record_id} with manual review")

        # Return updated record
        evidence_chain_dicts = vinyl_record.get_evidence_chain()
        evidence_chain = []
        for ev in evidence_chain_dicts:
            try:
                evidence_chain.append(
                    EvidenceModel(
                        source=ev["source"],
                        confidence=ev["confidence"],
                        data=ev["data"],
                        timestamp=datetime.fromisoformat(ev["timestamp"]),
                    )
                )
            except Exception as e:
                logger.warning(f"Failed to parse evidence: {e}")

        metadata = None
        if vinyl_record.artist or vinyl_record.title:
            metadata = VinylMetadataModel(
                artist=vinyl_record.artist or "Unknown",
                title=vinyl_record.title or "Unknown",
                year=vinyl_record.year,
                label=vinyl_record.label or "Unknown",
                catalog_number=vinyl_record.catalog_number,
                genres=vinyl_record.get_genres(),
            )

        return VinylRecordResponse(
            record_id=vinyl_record.id,
            created_at=vinyl_record.created_at,
            updated_at=vinyl_record.updated_at,
            status=vinyl_record.status,
            metadata=metadata,
            evidence_chain=evidence_chain,
            confidence=vinyl_record.confidence,
            auto_commit=vinyl_record.auto_commit,
            needs_review=vinyl_record.needs_review,
            error=vinyl_record.error,
            user_notes=vinyl_record.user_notes,
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error reviewing record {record_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e),
        )


@router.post("/identify/{record_id}/chat", response_model=ChatResponse)
async def chat_with_agent(
    record_id: str,
    request: ChatRequest,
    db: Session = Depends(get_db),
) -> ChatResponse:
    """
    Chat with the agent about a specific vinyl record.
    
    Allows manual input of corrections and metadata refinement.
    """
    try:
        # Fetch the vinyl record
        vinyl_record = db.query(VinylRecord).filter(VinylRecord.id == record_id).first()
        if not vinyl_record:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Record {record_id} not found",
            )

        logger.info(f"Chat message for record {record_id}: {request.message[:100]}")

        # Create chat context from current record state
        current_metadata = {
            "artist": vinyl_record.artist,
            "title": vinyl_record.title,
            "year": vinyl_record.year,
            "label": vinyl_record.label,
            "catalog_number": vinyl_record.catalog_number,
            "genres": vinyl_record.get_genres() if hasattr(vinyl_record, 'get_genres') else [],
        }

        # Build chat input for agent
        chat_input = f"""
User feedback on vinyl record:
{request.message}

Current metadata:
Artist: {current_metadata.get('artist', 'Unknown')}
Title: {current_metadata.get('title', 'Unknown')}
Year: {current_metadata.get('year', 'Unknown')}
Label: {current_metadata.get('label', 'Unknown')}
Catalog: {current_metadata.get('catalog_number', 'Unknown')}
Genres: {', '.join(current_metadata.get('genres', []))}

Additional metadata hints: {request.metadata if request.metadata else 'None'}

Based on user feedback, please:
1. Validate and update the metadata if user provided corrections
2. Respond conversationally to the user
3. Update confidence score based on the clarity of user input
4. Indicate if review is still needed
"""

        # For now, we'll do a simple update without running the full agent
        # In a full implementation, this would invoke the agent graph
        updated_metadata = current_metadata.copy()
        agent_response = f"Thank you for the feedback on '{vinyl_record.title}'. I've noted your input and updated the record accordingly."
        
        # If metadata was provided in request, use it
        if request.metadata:
            if "artist" in request.metadata:
                updated_metadata["artist"] = request.metadata["artist"]
                vinyl_record.artist = request.metadata["artist"]
            if "title" in request.metadata:
                updated_metadata["title"] = request.metadata["title"]
                vinyl_record.title = request.metadata["title"]
            if "year" in request.metadata:
                try:
                    updated_metadata["year"] = int(request.metadata["year"])
                    vinyl_record.year = int(request.metadata["year"])
                except ValueError:
                    pass
            if "label" in request.metadata:
                updated_metadata["label"] = request.metadata["label"]
                vinyl_record.label = request.metadata["label"]
            if "genres" in request.metadata:
                genres_str = request.metadata["genres"]
                genres = [g.strip() for g in genres_str.split(",")]
                updated_metadata["genres"] = genres
                vinyl_record.set_genres(genres)
            
            # Increment confidence based on user input
            vinyl_record.confidence = min(1.0, vinyl_record.confidence + 0.1)
            agent_response = f"Updated record with your input. Confidence increased to {vinyl_record.confidence:.2f}"

        # Add user note
        vinyl_record.user_notes = (vinyl_record.user_notes or "") + f"\nChat: {request.message[:200]}"

        # Commit changes
        db.commit()
        db.refresh(vinyl_record)

        # Build response
        metadata_dict = VinylMetadataModel(
            artist=updated_metadata.get("artist", "Unknown"),
            title=updated_metadata.get("title", "Unknown"),
            year=updated_metadata.get("year"),
            label=updated_metadata.get("label", "Unknown"),
            catalog_number=updated_metadata.get("catalog_number"),
            genres=updated_metadata.get("genres", []),
        )

        return ChatResponse(
            record_id=record_id,
            message=agent_response,
            updated_metadata=metadata_dict,
            confidence=vinyl_record.confidence,
            requires_review=vinyl_record.needs_review,
            chat_history=[
                ChatMessage(role="user", content=request.message),
                ChatMessage(role="assistant", content=agent_response),
            ],
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in chat for record {record_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e),
        )


# Include router in app
app.include_router(router)
