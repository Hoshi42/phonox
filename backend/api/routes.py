"""
FastAPI routes for vinyl record identification and management.

Endpoints:
- POST /api/v1/identify: Upload images and identify vinyl records
- GET /api/v1/identify/{record_id}: Get identification results
- POST /api/v1/identify/{record_id}/review: Review and confirm results
- POST /api/v1/identify/{record_id}/chat: Chat with AI about specific record
- POST /api/v1/chat: General vinyl chat without specific record context
- GET /api/v1/health: Health check endpoint

Authentication: Not required (open API)
Rate limiting: None (add before production)
"""

import logging
import os
import uuid
from typing import List, Optional, Dict, Any, Union
from datetime import datetime

from fastapi import APIRouter, File, UploadFile, HTTPException, Depends, status
from sqlalchemy.orm import Session
from anthropic import Anthropic

from backend.main import app
from backend.database import VinylRecord, SessionLocal, VinylImage
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
from backend.agent.metadata import estimate_vinyl_value
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


def _estimate_condition_from_confidence(confidence: float) -> str:
    """Estimate vinyl condition based on analysis confidence score.
    
    Maps confidence levels to vinyl grading standards:
    - 0.95+ = Mint (M) - Perfect condition
    - 0.85-0.94 = Near Mint (NM) - Nearly perfect
    - 0.75-0.84 = Very Good+ (VG+) - Shows minimal wear
    - 0.65-0.74 = Very Good (VG) - Shows some wear
    - 0.50-0.64 = Good+ (G+) - Noticeable wear but playable
    - Below 0.50 = Good (G) - Heavy wear but functional
    """
    if confidence >= 0.95:
        return "Mint (M)"
    elif confidence >= 0.85:
        return "Near Mint (NM)"
    elif confidence >= 0.75:
        return "Very Good+ (VG+)"
    elif confidence >= 0.65:
        return "Very Good (VG)"
    elif confidence >= 0.50:
        return "Good+ (G+)"
    else:
        return "Good (G)"


@router.post(
    "/identify",
    status_code=status.HTTP_202_ACCEPTED,
)
async def identify_vinyl(
    files: List[UploadFile] = File(...),
    user_notes: Optional[str] = None,
    db: Session = Depends(get_db),
) -> Union[VinylIdentifyResponse, VinylRecordResponse]:
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

        # Create vinyl record in database with TEMPORARY status
        # Will only be moved to "complete" when user explicitly saves via API
        record_id = str(uuid.uuid4())
        vinyl_record = VinylRecord(
            id=record_id,
            status="temporary",  # Mark as temporary until user saves
            user_notes=user_notes,
        )
        db.add(vinyl_record)
        db.commit()
        db.refresh(vinyl_record)

        logger.info(f"Created temporary vinyl record {record_id} for identification")

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
            # Keep status as "analyzed" (not yet in register)
            vinyl_record.status = "analyzed"
            vinyl_record.validation_passed = result_state.get("validation_passed", False)

            # Extract metadata
            image_analysis_intermediate_results = None  # Track for response
            if result_state.get("vision_extraction"):
                vision_data = result_state["vision_extraction"]
                vinyl_record.artist = vision_data.get("artist")
                vinyl_record.title = vision_data.get("title")
                vinyl_record.year = vision_data.get("year")
                vinyl_record.label = vision_data.get("label")
                vinyl_record.spotify_url = vision_data.get("spotify_url") or vision_data.get("spotify_link")
                vinyl_record.catalog_number = vision_data.get("catalog_number")
                vinyl_record.barcode = vision_data.get("barcode")  # Store barcode from vision extraction
                if vision_data.get("genres"):
                    vinyl_record.set_genres(vision_data["genres"])
                
                # Estimate value based on extracted metadata using web search
                # For image analysis: perform real market research immediately
                try:
                    if vinyl_record.artist and vinyl_record.title:
                        logger.info(f"Performing web search for value estimation during image analysis: {vinyl_record.artist} - {vinyl_record.title}")
                        
                        # Build search query with catalog number if available
                        search_query = f"{vinyl_record.artist} {vinyl_record.title} vinyl record price"
                        if vinyl_record.catalog_number:
                            search_query += f" {vinyl_record.catalog_number}"
                        if vinyl_record.year:
                            search_query += f" {vinyl_record.year}"
                        
                        logger.info(f"Web search query for image analysis: {search_query}")
                        
                        # Perform web search
                        search_results = chat_tools.search_and_scrape(
                            search_query,
                            scrape_results=True
                        )
                        
                        search_results_count = len(search_results.get("search_results", []))
                        logger.info(f"Image analysis web search found {search_results_count} results")
                        
                        # Build market context from search results
                        market_context = "Market Research Results:\n"
                        if search_results.get("search_results"):
                            for result in search_results["search_results"][:12]:
                                market_context += f"- {result.get('title', '')}: {result.get('content', '')}\n"
                        
                        if search_results.get("scraped_content"):
                            market_context += "\nDetailed Pricing Information:\n"
                            for content in search_results["scraped_content"][:3]:
                                if content.get("success"):
                                    market_context += f"- {content.get('title', '')}: {content.get('content', '')}\n"
                        
                        # Build record context
                        record_context = f"""
Vinyl Record Details:
- Artist: {vinyl_record.artist}
- Title: {vinyl_record.title}
- Year: {vinyl_record.year or 'Unknown'}
- Label: {vinyl_record.label or 'Unknown'}
- Catalog Number: {vinyl_record.catalog_number or 'Unknown'}
- Genres: {', '.join(vinyl_record.get_genres()) if hasattr(vinyl_record, 'get_genres') else 'Unknown'}
- Image Analysis Confidence: {vinyl_record.confidence * 100:.0f}%
- Format: Vinyl LP
"""
                        
                        # Use Claude Haiku to analyze market data
                        valuation_prompt = f"""Based on the web search results and record details provided, estimate the fair market value of this vinyl record in EUR.

{market_context}

{record_context}

Please provide:
1. Estimated fair market value in EUR (single number)
2. Price range (minimum and maximum in EUR)
3. Key factors affecting the price
4. Market condition assessment (strong/stable/weak)
5. Brief explanation of your valuation

Format your response as follows:
ESTIMATED_VALUE: €XX.XX
PRICE_RANGE: €XX.XX - €XX.XX
MARKET_CONDITION: [strong/stable/weak]
FACTORS: [list key factors]
EXPLANATION: [brief explanation]"""
                        
                        try:
                            # Get chat model from environment, with fallback
                            chat_model = os.getenv("ANTHROPIC_CHAT_MODEL", "claude-haiku-4-5-20251001")
                            response = anthropic_client.messages.create(
                                model=chat_model,
                                max_tokens=500,
                                messages=[
                                    {
                                        "role": "user",
                                        "content": valuation_prompt,
                                    }
                                ],
                            )
                            
                            valuation_text = response.content[0].text
                            logger.info(f"Claude valuation during image analysis: {valuation_text[:200]}")
                            
                            # Parse Claude's response
                            import re
                            estimated_value = None
                            price_range_min = None
                            price_range_max = None
                            market_condition = "stable"
                            factors = []
                            explanation = ""
                            
                            for line in valuation_text.split('\n'):
                                # Strip and check for key markers
                                line_stripped = line.strip()
                                if line_stripped.startswith('ESTIMATED_VALUE:') or 'ESTIMATED_VALUE:' in line_stripped:
                                    match = re.search(r'€?([\d.]+)', line)
                                    if match:
                                        estimated_value = float(match.group(1))
                                elif line_stripped.startswith('PRICE_RANGE:') or 'PRICE_RANGE:' in line_stripped:
                                    # Extract all numbers from the line
                                    matches = re.findall(r'€?([\d.]+)', line)
                                    if len(matches) >= 2:
                                        price_range_min = float(matches[0])
                                        price_range_max = float(matches[1])
                                        logger.info(f"Extracted price range from: {line} => min: {price_range_min}, max: {price_range_max}")
                                elif line.startswith('MARKET_CONDITION:'):
                                    condition = line.replace('MARKET_CONDITION:', '').strip().lower()
                                    if condition in ['strong', 'stable', 'weak']:
                                        market_condition = condition
                                elif line.startswith('FACTORS:'):
                                    factors_text = line.replace('FACTORS:', '').strip()
                                    factors = [f.strip() for f in factors_text.split(',')]
                                elif line.startswith('EXPLANATION:'):
                                    explanation = line.replace('EXPLANATION:', '').strip()
                            
                            # Fallback if parsing fails
                            if estimated_value is None:
                                prices = re.findall(r'€([\d.]+)', valuation_text)
                                if prices:
                                    estimated_value = float(prices[0])
                                else:
                                    estimated_value = None
                            
                            # Store estimated values if found
                            if estimated_value is not None:
                                vision_data["estimated_value_eur"] = estimated_value
                                vision_data["estimated_value_usd"] = estimated_value / 0.92
                                vision_data["market_condition"] = market_condition
                                vision_data["price_range_min"] = price_range_min
                                vision_data["price_range_max"] = price_range_max
                                vision_data["valuation_factors"] = factors
                                vision_data["valuation_explanation"] = explanation
                                
                                # ALSO store in vinyl_record so it's in the metadata (not just evidence)
                                vinyl_record.estimated_value_eur = estimated_value
                                logger.info(f"Image analysis: Web-based value estimate for {vinyl_record.artist} - {vinyl_record.title}: €{estimated_value}")
                                
                                # Create intermediate results for response
                                image_analysis_intermediate_results = {
                                    "search_query": search_query,
                                    "search_results_count": search_results_count,
                                    "claude_analysis": valuation_text,
                                    "search_sources": [
                                        {
                                            "title": result.get("title", ""),
                                            "content": result.get("content", "")[:200]  # First 200 chars
                                        }
                                        for result in search_results.get("search_results", [])[:12]
                                    ]
                                }
                            else:
                                logger.warning(f"Could not parse estimated value from Claude response for image analysis")
                        
                        except Exception as e:
                            logger.error(f"Error calling Claude for image analysis valuation: {e}")
                            # Continue without valuation
                    
                except Exception as e:
                    logger.error(f"Error during web search valuation in image analysis: {e}")
                    # Continue without valuation

            # Store evidence chain
            evidence_chain = result_state.get("evidence_chain", [])
            if evidence_chain:
                vinyl_record.set_evidence_chain(_serialize_evidence_chain(evidence_chain))

            # Store confidence and routing flags
            vinyl_record.confidence = result_state.get("confidence", 0.0)
            vinyl_record.auto_commit = result_state.get("auto_commit", False)
            vinyl_record.needs_review = result_state.get("needs_review", True)
            
            # Estimate condition from confidence if not already set
            if not vinyl_record.condition:
                vinyl_record.condition = _estimate_condition_from_confidence(vinyl_record.confidence)

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

        # Return analyzed record response (whether successful analysis or not)
        # Status is "analyzed" (not yet saved to register) or "failed"
        if vinyl_record.status in ["analyzed", "failed"]:
            logger.info(f"Identification complete, returning record response for {record_id}")
            logger.info(f"Image analysis intermediate_results: {image_analysis_intermediate_results}")
            record_dict = vinyl_record.to_dict()
            metadata_dict = record_dict.get("metadata", {})
            # Filter out None values from metadata for Pydantic validation
            metadata_dict_clean = {k: v for k, v in metadata_dict.items() if v is not None}
            response = VinylRecordResponse(
                record_id=record_id,
                created_at=vinyl_record.created_at,
                updated_at=vinyl_record.updated_at,
                status=vinyl_record.status,
                metadata=VinylMetadataModel(**metadata_dict_clean),
                evidence_chain=record_dict.get("evidence_chain", []),
                confidence=vinyl_record.confidence or 0.0,
                auto_commit=vinyl_record.auto_commit or False,
                needs_review=vinyl_record.needs_review or True,
                error=vinyl_record.error,
                user_notes=vinyl_record.user_notes,
                intermediate_results=image_analysis_intermediate_results,
            )
            logger.info(f"Returning response with intermediate_results: {response.intermediate_results is not None}")
            return response
        
        # Otherwise return initial response
        return VinylIdentifyResponse(
            record_id=record_id,
            status=vinyl_record.status,
            message="Vinyl identification started" if vinyl_record.status == "processing" else f"Identification {vinyl_record.status}",
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
                barcode=vinyl_record.barcode,
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
                barcode=vinyl_record.barcode,
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
            barcode=updated_metadata.get("barcode"),
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
            "search_results": all_search_results[:12],  # Limit to top 12 results
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


@router.patch(
    "/identify/{record_id}/metadata",
    response_model=VinylRecordResponse,
)
async def update_vinyl_metadata(
    record_id: str,
    metadata: Dict[str, Any] = None,
    db: Session = Depends(get_db),
) -> VinylRecordResponse:
    """Update vinyl record metadata fields."""
    try:
        # Query record from database
        vinyl_record = db.query(VinylRecord).filter(VinylRecord.id == record_id).first()

        if not vinyl_record:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Vinyl record {record_id} not found",
            )

        # Update allowed metadata fields
        if metadata:
            if "condition" in metadata:
                vinyl_record.condition = metadata["condition"]
            if "estimated_value_eur" in metadata:
                vinyl_record.estimated_value_eur = metadata["estimated_value_eur"]
            if "artist" in metadata:
                vinyl_record.artist = metadata["artist"]
            if "title" in metadata:
                vinyl_record.title = metadata["title"]
            if "year" in metadata:
                vinyl_record.year = metadata["year"]
            if "label" in metadata:
                vinyl_record.label = metadata["label"]
            if "genres" in metadata:
                if metadata["genres"]:
                    vinyl_record.set_genres(metadata["genres"] if isinstance(metadata["genres"], list) else [])
            if "catalog_number" in metadata:
                vinyl_record.catalog_number = metadata["catalog_number"]
            if "barcode" in metadata:
                vinyl_record.barcode = metadata["barcode"]
            if "spotify_url" in metadata:
                vinyl_record.spotify_url = metadata["spotify_url"]

        db.commit()
        db.refresh(vinyl_record)

        # Build response
        record_dict = vinyl_record.to_dict()
        metadata_dict = record_dict.get("metadata", {})
        metadata_dict_clean = {k: v for k, v in metadata_dict.items() if v is not None}

        return VinylRecordResponse(
            record_id=record_id,
            created_at=vinyl_record.created_at,
            updated_at=vinyl_record.updated_at,
            status=vinyl_record.status,
            metadata=VinylMetadataModel(**metadata_dict_clean),
            evidence_chain=record_dict.get("evidence_chain", []),
            confidence=vinyl_record.confidence or 0.0,
            auto_commit=vinyl_record.auto_commit or False,
            needs_review=vinyl_record.needs_review or True,
            error=vinyl_record.error,
            user_notes=vinyl_record.user_notes,
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating vinyl metadata: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e),
        )


@router.post(
    "/reanalyze/{record_id}",
    response_model=VinylRecordResponse,
    status_code=status.HTTP_202_ACCEPTED,
)
async def reanalyze_vinyl(
    record_id: str,
    files: List[UploadFile] = File(...),
    db: Session = Depends(get_db),
) -> VinylIdentifyResponse:
    """
    Re-analyze a vinyl record with additional images.
    
    This endpoint combines existing database images with new uploaded images
    for a more comprehensive analysis.
    """
    try:
        # Get existing record
        existing_record = db.query(VinylRecord).filter(VinylRecord.id == record_id).first()
        if not existing_record:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Record not found"
            )
            
        # Validate new files
        if not files or len(files) == 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="At least one image file is required for re-analysis",
            )
            
        logger.info(f"Re-analyzing record {record_id} with {len(files)} new images")
        
        # Update record status
        existing_record.status = "processing"
        db.commit()
        
        try:
            # Initialize agent graph
            graph = build_agent_graph()
            
            # Convert new uploaded files to image dicts
            import base64
            
            new_image_dicts = []
            for file in files:
                content = await file.read()
                file_content = base64.b64encode(content).decode('utf-8')
                new_image_dicts.append({
                    "path": file.filename or f"new_image_{len(new_image_dicts)}",
                    "content": file_content,
                    "content_type": file.content_type or "image/jpeg"
                })
            
            # Fetch and include existing images from database
            # Images are stored in VinylImage table with file_path pointing to the file system
            existing_image_dicts = []
            try:
                existing_images = db.query(VinylImage).filter(VinylImage.record_id == record_id).all()
                logger.info(f"Found {len(existing_images)} existing image records in database for re-analysis")
                
                for idx, vinyl_image in enumerate(existing_images):
                    try:
                        # Check if file exists and read it
                        if os.path.exists(vinyl_image.file_path):
                            with open(vinyl_image.file_path, "rb") as f:
                                image_data = f.read()
                                file_content = base64.b64encode(image_data).decode('utf-8')
                                existing_image_dicts.append({
                                    "path": vinyl_image.filename or f"existing_image_{idx}",
                                    "content": file_content,
                                    "content_type": vinyl_image.content_type or "image/jpeg"
                                })
                                logger.info(f"Loaded existing image {idx + 1}/{len(existing_images)}: {vinyl_image.filename}")
                        else:
                            logger.warning(f"Image file not found on disk: {vinyl_image.file_path}")
                    except Exception as e:
                        logger.warning(f"Could not read image file {vinyl_image.file_path}: {e}")
            except Exception as e:
                logger.warning(f"Error fetching existing images from database: {e}")
            
            # Combine all images: existing + new
            all_images = existing_image_dicts + new_image_dicts
            
            logger.info(f"Re-analysis will process {len(all_images)} total images ({len(existing_image_dicts)} existing from disk + {len(new_image_dicts)} new uploads)")
            
            initial_state: VinylState = {  # type: ignore
                "images": all_images,
                "validation_passed": False,
                "image_features": {},
                "vision_extraction": {},
                "evidence_chain": [],
                "confidence": 0.0,
                "auto_commit": False,
                "needs_review": True,
            }
            
            # Invoke graph with config for checkpointer
            config = {"configurable": {"thread_id": record_id + "_reanalysis"}}
            result_state = graph.invoke(initial_state, config=config)
            
            # Update record with new results
            existing_record.status = "analyzed"
            existing_record.validation_passed = result_state.get("validation_passed", False)
            
            # Extract metadata
            if result_state.get("vision_extraction"):
                vision_data = result_state["vision_extraction"]
                existing_record.artist = vision_data.get("artist")
                existing_record.title = vision_data.get("title")
                existing_record.year = vision_data.get("year")
                existing_record.label = vision_data.get("label")
                existing_record.spotify_url = vision_data.get("spotify_url") or vision_data.get("spotify_link")
                existing_record.catalog_number = vision_data.get("catalog_number")
                existing_record.barcode = vision_data.get("barcode")
                if vision_data.get("genres"):
                    existing_record.set_genres(vision_data["genres"])
                
                # Also store estimated value if available
                if vision_data.get("estimated_value_eur"):
                    existing_record.estimated_value_eur = vision_data.get("estimated_value_eur")
            
            # Store evidence chain
            evidence_chain = result_state.get("evidence_chain", [])
            if evidence_chain:
                existing_record.set_evidence_chain(_serialize_evidence_chain(evidence_chain))
            
            # Store confidence and routing flags
            existing_record.confidence = result_state.get("confidence", 0.0)
            existing_record.auto_commit = result_state.get("auto_commit", False)
            existing_record.needs_review = result_state.get("needs_review", True)
            
            # Handle errors
            if result_state.get("error"):
                existing_record.status = "failed"
                existing_record.error = result_state["error"]
            
            # Save newly uploaded images to the database
            # This makes them persistent and part of the record
            if len(files) > 0:
                logger.info(f"Saving {len(files)} newly uploaded images to database for record {record_id}")
                from backend.api.register import UPLOAD_DIR
                for file in files:
                    try:
                        # Read file content
                        file_content = await file.read()
                        
                        # Generate unique filename
                        file_extension = os.path.splitext(file.filename or '')[1] or '.jpg'
                        unique_filename = f"{uuid.uuid4()}{file_extension}"
                        file_path = os.path.join(UPLOAD_DIR, unique_filename)
                        
                        # Save file to disk
                        with open(file_path, "wb") as buffer:
                            buffer.write(file_content)
                        
                        # Create database record for the image
                        vinyl_image = VinylImage(
                            record_id=record_id,
                            filename=file.filename or unique_filename,
                            content_type=file.content_type or "image/jpeg",
                            file_size=len(file_content),
                            file_path=file_path,
                            is_primary=len(existing_record.images) == 0  # First image is primary
                        )
                        
                        db.add(vinyl_image)
                        logger.info(f"Saved image {file.filename} for record {record_id}")
                    except Exception as e:
                        logger.error(f"Error saving image {file.filename}: {e}")
            
            db.commit()
            db.refresh(existing_record)
            
            logger.info(f"Completed re-analysis for {record_id}: confidence={existing_record.confidence:.2f}, status={existing_record.status}")
            
            # Return the actual updated record status
            record_dict = existing_record.to_dict()
            metadata_dict = record_dict.get("metadata", {})
            metadata_dict_clean = {k: v for k, v in metadata_dict.items() if v is not None}
            
            return VinylRecordResponse(
                record_id=record_id,
                created_at=existing_record.created_at,
                updated_at=existing_record.updated_at,
                status=existing_record.status,
                metadata=VinylMetadataModel(**metadata_dict_clean),
                evidence_chain=record_dict.get("evidence_chain", []),
                confidence=existing_record.confidence or 0.0,
                auto_commit=existing_record.auto_commit or False,
                needs_review=existing_record.needs_review or True,
                error=existing_record.error,
                user_notes=existing_record.user_notes,
            )
        
        except Exception as e:
            logger.error(f"Error during re-analysis: {e}")
            existing_record.status = "failed"
            existing_record.error = str(e)
            db.commit()
            
            # Return error status
            return VinylRecordResponse(
                record_id=record_id,
                created_at=existing_record.created_at,
                updated_at=existing_record.updated_at,
                status="failed",
                error=str(e),
            )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Unexpected error in reanalyze_vinyl: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e),
        )


@router.post("/estimate-value/{record_id}", response_model=Dict[str, Any])
async def estimate_value_with_websearch(
    record_id: str,
    db: Session = Depends(get_db),
) -> Dict[str, Any]:
    """
    Estimate vinyl record value using web search for market pricing.
    
    Uses web search to find current market prices from Discogs, eBay, Vinted,
    and other sources, then uses Claude Haiku to provide intelligent valuation
    based on condition, rarity, and current market data.
    
    Returns estimated value in EUR with market context.
    """
    try:
        # Fetch the vinyl record
        vinyl_record = db.query(VinylRecord).filter(VinylRecord.id == record_id).first()
        if not vinyl_record:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Record {record_id} not found",
            )
        
        if not vinyl_record.artist or not vinyl_record.title:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Record must have artist and title for value estimation",
            )
        
        logger.info(f"Estimating value with web search for {vinyl_record.artist} - {vinyl_record.title}")
        
        # Perform web search for pricing information
        # Include catalog_number for more specific results (exact pressing identification)
        search_query = f"{vinyl_record.artist} {vinyl_record.title} vinyl record price"
        if vinyl_record.catalog_number:
            search_query += f" {vinyl_record.catalog_number}"
        if vinyl_record.year:
            search_query += f" {vinyl_record.year}"
        
        logger.info(f"Web search query: {search_query}")
        
        search_results = chat_tools.search_and_scrape(
            search_query,
            scrape_results=True
        )
        
        # Store search results for intermediate display
        search_results_count = len(search_results.get("search_results", []))
        logger.info(f"Web search found {search_results_count} results")
        
        # Build market context from search results
        market_context = "Market Research Results:\n"
        if search_results.get("search_results"):
            for result in search_results["search_results"][:5]:
                market_context += f"- {result.get('title', '')}: {result.get('content', '')}\n"
        
        if search_results.get("scraped_content"):
            market_context += "\nDetailed Pricing Information:\n"
            for content in search_results["scraped_content"][:3]:
                if content.get("success"):
                    market_context += f"- {content.get('title', '')}: {content.get('content', '')}\n"
        
        # Build record context
        record_context = f"""
Vinyl Record Details:
- Artist: {vinyl_record.artist}
- Title: {vinyl_record.title}
- Year: {vinyl_record.year or 'Unknown'}
- Label: {vinyl_record.label or 'Unknown'}
- Catalog Number: {vinyl_record.catalog_number or 'Unknown'}
- Genres: {', '.join(vinyl_record.get_genres()) if hasattr(vinyl_record, 'get_genres') else 'Unknown'}
- Current Condition Assessment: Based on image analysis (confidence: {vinyl_record.confidence * 100:.0f}%)
- Format: Vinyl LP
"""
        
        # Use Claude to analyze market data and provide valuation
        valuation_prompt = f"""Based on the web search results and record details provided, estimate the fair market value of this vinyl record in EUR.

{market_context}

{record_context}

Please provide:
1. Estimated fair market value in EUR (single number)
2. Price range (minimum and maximum in EUR)
3. Key factors affecting the price
4. Market condition assessment (strong/stable/weak)
5. Brief explanation of your valuation

Format your response as follows:
ESTIMATED_VALUE: €XX.XX
PRICE_RANGE: €XX.XX - €XX.XX
MARKET_CONDITION: [strong/stable/weak]
FACTORS: [list key factors]
EXPLANATION: [brief explanation]"""
        
        try:
            response = anthropic_client.messages.create(
                model="claude-haiku-4-5-20251001",
                max_tokens=500,
                messages=[
                    {
                        "role": "user",
                        "content": valuation_prompt,
                    }
                ],
            )
            
            valuation_text = response.content[0].text
            logger.info(f"Claude valuation response: {valuation_text[:200]}")
            
            # Parse Claude's response
            estimated_value = None
            price_range_min = None
            price_range_max = None
            market_condition = "stable"
            factors = []
            explanation = ""
            
            for line in valuation_text.split('\n'):
                # Strip and check for key markers
                line_stripped = line.strip()
                if line_stripped.startswith('ESTIMATED_VALUE:') or 'ESTIMATED_VALUE:' in line_stripped:
                    # Extract number from "€XX.XX"
                    import re
                    match = re.search(r'€?([\d.]+)', line)
                    if match:
                        estimated_value = float(match.group(1))
                elif line_stripped.startswith('PRICE_RANGE:') or 'PRICE_RANGE:' in line_stripped:
                    # Extract "€XX.XX - €XX.XX"
                    import re
                    matches = re.findall(r'€?([\d.]+)', line)
                    if len(matches) >= 2:
                        price_range_min = float(matches[0])
                        price_range_max = float(matches[1])
                        logger.info(f"Extracted price range from: {line} => min: {price_range_min}, max: {price_range_max}")
                elif line.startswith('MARKET_CONDITION:'):
                    condition = line.replace('MARKET_CONDITION:', '').strip().lower()
                    if condition in ['strong', 'stable', 'weak']:
                        market_condition = condition
                elif line.startswith('FACTORS:'):
                    factors_text = line.replace('FACTORS:', '').strip()
                    factors = [f.strip() for f in factors_text.split(',')]
                elif line.startswith('EXPLANATION:'):
                    explanation = line.replace('EXPLANATION:', '').strip()
            
            # Fallback if parsing fails
            if estimated_value is None:
                # Try to extract any price mentioned
                import re
                prices = re.findall(r'€([\d.]+)', valuation_text)
                if prices:
                    estimated_value = float(prices[0])
                else:
                    estimated_value = 25.0  # Safe default
            
            # Note: We do NOT update the database here
            # The value is only stored when the user clicks "Update in Register"
            # This allows the user to review and decide whether to apply it
            
            logger.info(f"Value estimation completed: €{estimated_value} for {vinyl_record.artist} - {vinyl_record.title}")
            logger.info(f"Estimated value is NOT yet saved to database - user must click 'Update in Register'")
            
            # Prepare intermediate results for display
            intermediate_results = {
                "search_query": search_query,
                "search_results_count": search_results_count,
                "claude_analysis": valuation_text,
                "search_sources": [
                    {
                        "title": result.get("title", ""),
                        "content": result.get("content", "")[:200]  # First 200 chars
                    }
                    for result in search_results.get("search_results", [])[:5]
                ]
            }
            
            return {
                "record_id": record_id,
                "estimated_value_eur": estimated_value,
                "price_range_min": price_range_min,
                "price_range_max": price_range_max,
                "market_condition": market_condition,
                "factors": factors,
                "explanation": explanation,
                "web_enhanced": True,
                "sources_used": search_results_count,
                "intermediate_results": intermediate_results,
            }
            
        except Exception as e:
            logger.error(f"Error calling Claude for valuation: {e}")
            # Return current value with note that web search wasn't fully processed
            return {
                "record_id": record_id,
                "estimated_value_eur": vinyl_record.estimated_value_eur or 25.0,
                "error": "Web-based valuation unavailable, using cached estimate",
                "web_enhanced": False,
            }
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error estimating value for {record_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e),
        )


# Include router in app
app.include_router(router)
