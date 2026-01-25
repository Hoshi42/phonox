"""API routes for vinyl identification."""

import logging
import uuid
from typing import List, Optional, Dict, Any
from datetime import datetime

from fastapi import APIRouter, File, UploadFile, HTTPException, Depends, status
from sqlalchemy.orm import Session
from anthropic import Anthropic

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
from backend.tools import EnhancedChatTools

logger = logging.getLogger(__name__)

# Initialize Anthropic client for chat (using cheapest model: Claude 3.5 Haiku)
anthropic_client = Anthropic()

# Initialize enhanced chat tools
chat_tools = EnhancedChatTools()

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
                vinyl_record.spotify_url = vision_data.get("spotify_url") or vision_data.get("spotify_link")
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
                spotify_url=vinyl_record.spotify_url,
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
        if review.spotify_url:
            vinyl_record.spotify_url = review.spotify_url
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
                spotify_url=vinyl_record.spotify_url,
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


@router.post("/identify/{record_id}/chat", response_model=Dict[str, Any])
async def chat_with_agent(
    record_id: str,
    request: ChatRequest,
    db: Session = Depends(get_db),
) -> Dict[str, Any]:
    """
    Chat with the agent about a specific vinyl record using Claude 3.5 Haiku.
    
    Allows manual input of corrections and metadata refinement.
    Uses Claude 3.5 Haiku (cheapest Claude model) for intelligent chat responses.
    
    Cost: ~$0.00008 per request (Claude 3.5 Haiku pricing)
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
            "spotify_url": vinyl_record.spotify_url,
            "catalog_number": vinyl_record.catalog_number,
            "genres": vinyl_record.get_genres() if hasattr(vinyl_record, 'get_genres') else [],
            "estimated_value_eur": vinyl_record.estimated_value_eur,
        }

        # Build system prompt for Claude to understand vinyl record correction context
        system_prompt = """You are a helpful vinyl record identification assistant with access to web search and scraping tools. Users are providing feedback, corrections, and questions about vinyl record metadata.

Your tasks:
1. Acknowledge the user's input conversationally
2. Use web search to find additional information when needed
3. Validate their corrections against current metadata and web sources
4. Provide enriched information from web searches
5. Extract structured metadata from natural language corrections
6. Keep responses informative but concise

Current vinyl record context:
- Artist: {artist}
- Title: {title}
- Year: {year}
- Label: {label}
- Catalog Number: {catalog_number}
- Genres: {genres}

When users ask questions, search for current information. When they provide corrections, acknowledge and confirm updates.""".format(
            artist=current_metadata.get("artist", "Unknown"),
            title=current_metadata.get("title", "Unknown"),
            year=current_metadata.get("year", "Unknown"),
            label=current_metadata.get("label", "Unknown"),
            catalog_number=current_metadata.get("catalog_number", "Unknown"),
            genres=", ".join(current_metadata.get("genres", [])) or "Unknown",
        )

        # Determine if we need web search based on user message or /web trigger
        search_keywords = ["price", "value", "worth", "cost", "information", "about", "tell me", "details", "history", "when", "where", "who", "what"]
        has_web_trigger = "/web" in request.message.lower()
        needs_web_search = has_web_trigger or any(keyword in request.message.lower() for keyword in search_keywords)
        
        # Remove /web trigger from message if present
        search_message = request.message.replace("/web", "").strip() if has_web_trigger else request.message
        
        web_context = ""
        all_search_results = []  # Track all search results for response
        if needs_web_search and vinyl_record.artist and vinyl_record.title:
            logger.info(f"Performing web search for vinyl question: {request.message[:100]}")
            try:
                # Use web tools to get comprehensive information
                web_info = chat_tools.get_vinyl_comprehensive_info(
                    vinyl_record.artist, 
                    vinyl_record.title
                )
                
                # Collect search results for response
                if web_info.get("general_info"):
                    all_search_results.extend(web_info["general_info"])
                if web_info.get("pricing_info"):
                    all_search_results.extend(web_info["pricing_info"])
                
                # Format web information for Claude
                web_context = "\n\nWeb Search Results:\n"
                
                # Add general info
                if web_info.get("general_info"):
                    web_context += "General Information:\n"
                    for result in web_info["general_info"][:2]:
                        web_context += f"- {result.get('title', '')}: {result.get('content', '')[:200]}...\n"
                
                # Add pricing info
                if web_info.get("pricing_info"):
                    web_context += "\nPricing Information:\n"
                    for result in web_info["pricing_info"][:2]:
                        web_context += f"- {result.get('title', '')}: {result.get('content', '')[:200]}...\n"
                
                # Add detailed scraped content
                if web_info.get("detailed_content"):
                    web_context += "\nDetailed Information:\n"
                    for content in web_info["detailed_content"][:1]:  # Only first detailed result
                        if content.get("success"):
                            web_context += f"- {content.get('title', '')}: {content.get('content', '')[:300]}...\n"
                
            except Exception as e:
                logger.error(f"Error performing web search: {e}")
                web_context = "\nNote: Web search temporarily unavailable."

        # Call Claude Haiku 4.5 (fastest, cheapest model) for intelligent response
        logger.debug(f"Calling Claude Haiku 4.5 for chat message: {request.message[:100]}")
        try:
            response = anthropic_client.messages.create(
                model="claude-haiku-4-5-20251001",  # Fastest Claude model
                max_tokens=800,  # Increased for web-enhanced responses
                system=system_prompt + web_context,
                messages=[
                    {
                        "role": "user",
                        "content": search_message,  # Use cleaned message without /web trigger
                    }
                ],
            )
            agent_response = response.content[0].text
            logger.debug(f"Claude response: {agent_response[:100]}")
        except Exception as e:
            logger.error(f"Error calling Claude 3.5 Haiku: {e}")
            base_response = f"I understood your feedback about the record. I've processed your input for '{vinyl_record.title}'."
            if web_context:
                agent_response = base_response + " I also found some additional information from web sources that might be helpful."
            else:
                agent_response = base_response

        # Update metadata if provided in request
        updated_metadata = current_metadata.copy()
        confidence_increment = 0.05  # Base increment for chat interaction

        if request.metadata:
            if "artist" in request.metadata:
                updated_metadata["artist"] = request.metadata["artist"]
                vinyl_record.artist = request.metadata["artist"]
                confidence_increment = 0.15  # Higher increment for explicit correction
            if "title" in request.metadata:
                updated_metadata["title"] = request.metadata["title"]
                vinyl_record.title = request.metadata["title"]
                confidence_increment = 0.15
            if "year" in request.metadata:
                try:
                    updated_metadata["year"] = int(request.metadata["year"])
                    vinyl_record.year = int(request.metadata["year"])
                except ValueError:
                    pass
            if "label" in request.metadata:
                updated_metadata["label"] = request.metadata["label"]
                vinyl_record.label = request.metadata["label"]
                confidence_increment = 0.1
            if "genres" in request.metadata:
                genres_str = request.metadata["genres"]
                genres = [g.strip() for g in genres_str.split(",")]
                updated_metadata["genres"] = genres
                vinyl_record.set_genres(genres)
                confidence_increment = 0.1
            if "estimated_value_eur" in request.metadata:
                try:
                    value = float(request.metadata["estimated_value_eur"])
                    updated_metadata["estimated_value_eur"] = value
                    vinyl_record.estimated_value_eur = value
                    confidence_increment = 0.05  # Small increment for value updates
                except (ValueError, TypeError):
                    pass
            if "spotify_url" in request.metadata or "spotify_link" in request.metadata:
                spotify_value = request.metadata.get("spotify_url") or request.metadata.get("spotify_link")
                updated_metadata["spotify_url"] = spotify_value
                vinyl_record.spotify_url = spotify_value
                confidence_increment = max(confidence_increment, 0.05)

            # Increment confidence based on quality of user input
            vinyl_record.confidence = min(1.0, vinyl_record.confidence + confidence_increment)
        else:
            # Even for text-only feedback, slightly increase confidence
            vinyl_record.confidence = min(1.0, vinyl_record.confidence + 0.05)

        # Add user note
        vinyl_record.user_notes = (vinyl_record.user_notes or "") + f"\nChat: {search_message[:200]}"

        # Commit changes
        db.commit()
        db.refresh(vinyl_record)

        # Build response
        metadata_dict = VinylMetadataModel(
            artist=updated_metadata.get("artist", "Unknown"),
            title=updated_metadata.get("title", "Unknown"),
            year=updated_metadata.get("year"),
            label=updated_metadata.get("label", "Unknown"),
            spotify_url=updated_metadata.get("spotify_url"),
            catalog_number=updated_metadata.get("catalog_number"),
            genres=updated_metadata.get("genres", []),
            estimated_value_eur=updated_metadata.get("estimated_value_eur"),
            estimated_value_usd=updated_metadata.get("estimated_value_usd"),
        )

        return {
            "record_id": record_id,
            "message": agent_response,
            "updated_metadata": metadata_dict.model_dump() if metadata_dict else None,
            "confidence": vinyl_record.confidence,
            "requires_review": vinyl_record.needs_review,
            "chat_history": [
                {"role": "user", "content": request.message, "timestamp": datetime.now()},
                {"role": "assistant", "content": agent_response, "timestamp": datetime.now()},
            ],
            "web_enhanced": needs_web_search,
            "sources_used": len(all_search_results),
            "search_results": all_search_results[:5],  # Limit to top 5 results
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in chat for record {record_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e),
        )


@router.post("/chat", response_model=Dict[str, Any])
async def general_chat(
    request: ChatRequest,
) -> Dict[str, Any]:
    """
    General chat with web search capabilities for vinyl-related questions.
    
    Automatically performs web search and scraping to answer questions about vinyl records,
    pricing, market information, and general music knowledge when no specific record is selected.
    """
    try:
        logger.info(f"General chat query: {request.message[:100]}")
        
        # Check for explicit /web trigger - always search for general queries, but clean the message
        has_web_trigger = "/web" in request.message.lower()
        search_message = request.message.replace("/web", "").strip() if has_web_trigger else request.message
        
        # Always perform web search for general queries since we have no specific record context
        search_results = chat_tools.search_and_scrape(
            search_message,  # Use cleaned message
            scrape_results=True
        )
        
        # Prepare context for Claude
        web_context = ""
        if search_results.get("search_results"):
            web_context += "Current Web Information:\n"
            for result in search_results["search_results"][:3]:
                web_context += f"• {result.get('title', '')}: {result.get('content', '')[:250]}...\n"
        
        if search_results.get("scraped_content"):
            web_context += "\nDetailed Information:\n"
            for content in search_results["scraped_content"]:
                if content.get("success"):
                    web_context += f"• {content.get('title', '')}: {content.get('content', '')[:400]}...\n"
        
        # Get enhanced response from Claude
        system_prompt = """You are a knowledgeable vinyl record expert with access to current web information. 
        Answer questions about vinyl records, music history, pricing, collecting, and related topics using the provided web search results.
        
        Provide accurate, helpful responses based on the search results. If pricing is mentioned, give context about market conditions.
        Keep responses informative but conversational."""
        
        try:
            response = anthropic_client.messages.create(
                model="claude-haiku-4-5-20251001",
                max_tokens=1000,
                system=system_prompt + "\n\n" + web_context,
                messages=[
                    {
                        "role": "user",
                        "content": request.message,
                    }
                ],
            )
            agent_response = response.content[0].text
        except Exception as e:
            logger.error(f"Error calling Claude: {e}")
            agent_response = f"I found some information about your query, but I'm having trouble processing it right now."
        
        return {
            "message": agent_response,
            "search_results": search_results.get("search_results", []),
            "sources_used": len(search_results.get("search_results", [])),
            "web_enhanced": True
        }
    
    except Exception as e:
        logger.error(f"Error in general chat: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e),
        )


# Include router in app
app.include_router(router)
