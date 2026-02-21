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

import json
import logging
import os
import uuid
from typing import List, Optional, Dict, Any, Union
from datetime import datetime

from fastapi import APIRouter, File, UploadFile, HTTPException, Depends, status, Form
from sqlalchemy.orm import Session
from anthropic import Anthropic

from backend.main import app
from backend.database import VinylRecord, get_db, VinylImage
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


def _serialize_evidence_chain(evidence_chain: List[dict]) -> List[dict]:
    """Serialize evidence chain for JSON storage, handling circular references."""
    import json
    
    def safe_serialize_value(obj, depth=0, max_depth=10):
        """Safely serialize a value, handling circular references with depth limit."""
        # Prevent infinite recursion
        if depth > max_depth:
            return f"<truncated at depth {max_depth}>"
        
        if isinstance(obj, datetime):
            return obj.isoformat()
        elif hasattr(obj, "value"):
            return obj.value
        elif isinstance(obj, (str, int, float, bool, type(None))):
            return obj
        elif isinstance(obj, dict):
            result = {}
            for k, v in obj.items():
                try:
                    result[k] = safe_serialize_value(v, depth + 1, max_depth)
                except (ValueError, TypeError, RecursionError):
                    result[k] = str(v)[:200] if v is not None else None
            return result
        elif isinstance(obj, (list, tuple)):
            try:
                return [safe_serialize_value(item, depth + 1, max_depth) for item in obj[:100]]  # Limit list size
            except (ValueError, TypeError, RecursionError):
                return [str(item)[:200] for item in obj[:10]]
        else:
            # For any other type, convert to string
            try:
                return str(obj)[:200]
            except:
                return "<non-serializable>"
    
    serialized = []
    for evidence in evidence_chain:
        try:
            evidence_copy = safe_serialize_value(evidence)
            # Double-check it's JSON serializable
            json.dumps(evidence_copy)
            serialized.append(evidence_copy)
        except (ValueError, TypeError, RecursionError) as e:
            logger.warning(f"Skipping non-serializable evidence: {e}")
            # Add simplified version
            serialized.append({
                "source": str(evidence.get("source", "unknown")),
                "confidence": evidence.get("confidence", 0.0),
                "timestamp": datetime.now().isoformat(),
                "error": "Circular reference or non-serializable data"
            })
    return serialized





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
        # Initialize variable outside try block to ensure it's always defined
        image_analysis_intermediate_results = None
        
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

            # Invoke graph (config thread_id not used but kept for future expansion)
            config = {"configurable": {"thread_id": record_id}}
            result_state = graph.invoke(initial_state, config=config)

            # Update record with results
            # Keep status as "analyzed" (not yet in register)
            vinyl_record.status = "analyzed"
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
            
            # Use condition estimated by vision agent if available
            # (The agent analyzes physical condition from the images)
            if not vinyl_record.condition and vision_data:
                vinyl_record.condition = vision_data.get("condition")

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
                condition=vinyl_record.condition,
                estimated_value_eur=vinyl_record.estimated_value_eur,
                estimated_value_usd=vinyl_record.estimated_value_usd,
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
                condition=vinyl_record.condition,
                estimated_value_eur=vinyl_record.estimated_value_eur,
                estimated_value_usd=vinyl_record.estimated_value_usd,
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
        system_prompt = """You are a helpful vinyl record identification assistant. Users are providing feedback, corrections, and questions about vinyl record metadata.

CHAT HISTORY & CONTEXT:
- You have been provided with recent chat history to understand the conversation context
- Use this history to understand the user's intent and avoid asking repetitive questions
- If the user mentions something multiple times or references a previous point, they want to discuss or clarify that specific topic
- Infer what the user needs based on context rather than asking generic clarifying questions
- Build on previous answers rather than restarting the conversation

YOUR TASKS:
1. Use chat history to understand ongoing discussion about this record
2. Answer the current question based on both the history and current message
3. Provide focused, relevant information without asking what they already told you
4. Validate corrections against current metadata and web sources (when provided)
5. Extract structured metadata from natural language corrections
6. Keep responses informative but concise

IMPORTANT: Do NOT include detailed web search results or source lists in your response - these are provided separately to the user interface.

Current vinyl record context:
- Artist: {artist}
- Title: {title}
- Year: {year}
- Label: {label}
- Catalog Number: {catalog_number}
- Genres: {genres}

When web search information is provided below, use it to enhance your answer but keep your response focused on answering the user's question directly.""".format(
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
                
                # Format MINIMAL web information for Claude (summary only, not full formatted results)
                web_context = "\n\nNote: Web search results are available with 5+ sources on pricing, condition, and market information for this record."
                
            except Exception as e:
                logger.error(f"Error performing web search: {e}")

                web_context = "\nNote: Web search temporarily unavailable."
        # Call Claude Haiku 4.5 (fastest, cheapest model) for intelligent response
        logger.debug(f"Calling Claude Haiku 4.5 for chat message: {request.message[:100]}")
        try:
            # Build messages list with chat history for context
            messages_for_claude = []
            
            # Add chat history if provided
            if request.chat_history:
                logger.debug(f"Including {len(request.chat_history)} messages from chat history")
                for history_msg in request.chat_history:
                    messages_for_claude.append({
                        "role": history_msg.get("role", "user"),
                        "content": history_msg.get("content", "")
                    })
            
            # Add current message
            messages_for_claude.append({
                "role": "user",
                "content": search_message,  # Use cleaned message without /web trigger
            })
            
            chat_model = os.getenv("ANTHROPIC_CHAT_MODEL", "claude-haiku-4-5-20251001")
            response = anthropic_client.messages.create(
                model=chat_model,
                max_tokens=800,  # Increased for web-enhanced responses
                system=system_prompt + web_context,
                messages=messages_for_claude,
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
        
CHAT HISTORY & CONTEXT:
- You have been provided with recent chat history to understand the conversation context
- Use this history to understand the user's intent and avoid asking repetitive questions
- If the user mentions something multiple times or references a previous point, they want to discuss or clarify that specific topic
- Infer what the user needs based on context rather than asking generic clarifying questions
- Build on previous answers rather than restarting the conversation
        
Provide accurate, helpful responses based on the search results and chat history. If pricing is mentioned, give context about market conditions.
Keep responses informative but conversational."""
        
        try:
            # Build messages list with chat history for context
            messages_for_claude = []
            
            # Add chat history if provided
            if request.chat_history:
                logger.debug(f"General chat: Including {len(request.chat_history)} messages from chat history")
                for history_msg in request.chat_history:
                    messages_for_claude.append({
                        "role": history_msg.get("role", "user"),
                        "content": history_msg.get("content", "")
                    })
            
            # Add current message
            messages_for_claude.append({
                "role": "user",
                "content": request.message,
            })
            
            chat_model = os.getenv("ANTHROPIC_CHAT_MODEL", "claude-haiku-4-5-20251001")
            response = anthropic_client.messages.create(
                model=chat_model,
                max_tokens=4000,
                system=system_prompt + "\n\n" + web_context,
                messages=messages_for_claude,
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
    files: List[UploadFile] = File(default=[]),  # Optional files - can reanalyze without new images
    current_record: Optional[str] = Form(None),
    reanalyze_all: Optional[str] = Form(None),  # "true" to reanalyze existing images too
    db: Session = Depends(get_db),
) -> VinylRecordResponse:
    """
    Smart re-analysis: Analyze images from browser memory OR database (for registered records).
    
    **Two scenarios:**
    1. **Analyzing new images (not yet registered)**: 
       - All images in browser memory
       - Sent via files parameter
       - No database access needed
    
    2. **Re-analyzing registered records**:
       - Existing images in database
       - Load from database + any new uploads
       - Set reanalyze_all="true" to trigger database loading
    
    Parameters:
        record_id: Vinyl record ID
        files: New images to add (can be empty for registered records)
        current_record: JSON string of current record data (optional)
        reanalyze_all: "true" = load existing images from database (for registered records)
        db: Database session
    
    Returns:
        Updated vinyl record with analyzed/enhanced metadata (in-memory only)
    """
    try:
        # Check if this is a registered record that needs existing images loaded
        do_load_from_database = reanalyze_all and reanalyze_all.lower() == "true"
        
        # Validate that we have at least something to analyze
        if not do_load_from_database and (not files or len(files) == 0):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="At least one image file is required for re-analysis",
            )
        
        if do_load_from_database:
            logger.info(f"Re-analyzing REGISTERED record {record_id} - loading existing images from database + {len(files) if files else 0} new")
        else:
            logger.info(f"Re-analyzing record {record_id} with {len(files)} images from browser memory")
        
        # Parse current record data for preserving existing fields (e.g. Spotify URL)
        existing_spotify_url = None
        if current_record:
            try:
                current_record_data = json.loads(current_record)
                existing_spotify_url = (
                    current_record_data.get("metadata", {}).get("spotify_url")
                    or current_record_data.get("spotify_url")
                )
                if existing_spotify_url:
                    logger.info(f"Found existing Spotify URL in current_record: {existing_spotify_url}")
            except Exception as e:
                logger.warning(f"Failed to parse current_record for Spotify URL preservation: {e}")
        
        try:
            # STEP 1: Analyze images from the request (all images are in memory/uploaded)
            graph = build_agent_graph()
            
            import base64
            image_dicts = []
            
            # Process all uploaded images (they're in browser memory, not database yet)
            if files:
                for file in files:
                    try:
                        content = await file.read()
                        file_content = base64.b64encode(content).decode('utf-8')
                        image_dicts.append({
                            "path": file.filename or f"image_{len(image_dicts)}",
                            "content": file_content,
                            "content_type": file.content_type or "image/jpeg"
                        })
                    except Exception as e:
                        logger.error(f"Error processing file {file.filename}: {e}")
                        raise HTTPException(
                            status_code=status.HTTP_400_BAD_REQUEST,
                            detail=f"Failed to process image {file.filename}: {str(e)}"
                        )
            
            logger.info(f"Processing {len(image_dicts)} images from browser memory")
            
            # If no files were provided but this is a registered-record re-analysis,
            # fall back to loading images directly from the database.
            # This handles the case where the frontend failed to pre-fetch images
            # (e.g. backend was transiently unavailable while images were loading).
            if len(image_dicts) == 0 and do_load_from_database:
                logger.info(f"No client files received for registered record {record_id} – loading images from database")
                db_images = db.query(VinylImage).filter(VinylImage.record_id == record_id).all()
                for db_img in db_images:
                    try:
                        image_data = db_img.get_image_data()
                        if image_data:
                            file_content = base64.b64encode(image_data).decode('utf-8')
                            image_dicts.append({
                                "path": db_img.filename or f"db_image_{db_img.id}",
                                "content": file_content,
                                "content_type": db_img.content_type or "image/jpeg",
                            })
                    except Exception as e:
                        logger.error(f"Error loading DB image {db_img.id}: {e}")
                logger.info(f"Loaded {len(image_dicts)} image(s) from database for record {record_id}")
            
            # Ensure we have at least one image to analyze
            if len(image_dicts) == 0:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="No images available for re-analysis. Please upload at least one image or ensure the record has existing images.",
                )
            
            # Create state with images for analysis
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
            
            # Invoke graph (config thread_id not used but kept for future expansion)
            config = {"configurable": {"thread_id": record_id}}
            result_state = graph.invoke(initial_state, config=config)
            
            # STEP 2: Extract metadata from images
            new_metadata = result_state.get("vision_extraction", {})
            logger.info(f"Extracted metadata from images: {new_metadata}")
            
            # ✅ CRITICAL: Validate that image detection/analysis actually succeeded
            # If vision extraction failed or returned empty, the entire chain should fail
            
            # Check if vision extraction produced no results
            if not new_metadata or len(new_metadata) == 0:
                error_msg = result_state.get("error", "Vision extraction failed: no metadata detected from images")
                logger.error(f"❌ Vision extraction returned empty for {record_id}: {error_msg}")
                # Return failure - complete chain must fail if image detection fails
                return VinylRecordResponse(
                    record_id=record_id,
                    created_at=datetime.utcnow(),
                    updated_at=datetime.utcnow(),
                    status="failed",
                    error=f"Image analysis failed: {error_msg}. Could not detect vinyl record details.",
                )
            
            # Check if graph invocation reported an error
            if result_state.get("error"):
                error_msg = result_state.get("error")
                logger.error(f"❌ Graph invocation had error for {record_id}: {error_msg}")
                # Return failure - chain fails if analysis had errors
                return VinylRecordResponse(
                    record_id=record_id,
                    created_at=datetime.utcnow(),
                    updated_at=datetime.utcnow(),
                    status="failed",
                    error=f"Image analysis failed: {error_msg}",
                )
            
            # Check confidence score is not zero (indicates analysis failed)
            analysis_confidence = result_state.get("confidence", 0)
            if analysis_confidence == 0:
                logger.error(f"❌ Analysis produced zero confidence for {record_id}")
                return VinylRecordResponse(
                    record_id=record_id,
                    created_at=datetime.utcnow(),
                    updated_at=datetime.utcnow(),
                    status="failed",
                    error="Image analysis could not produce confidence score. Check that valid vinyl record images were provided.",
                )
            
            # STEP 3: Use the analyzed metadata directly
            # Since we analyze ALL uploaded images together, the LLM aggregation already merged them
            # No need for further enhancement - this IS the enhanced result
            enhanced_metadata = new_metadata
            new_confidence = analysis_confidence
            logger.info(f"✅ Analysis complete with {len(files)} images (confidence: {new_confidence:.2f})")
            
            # Preserve existing Spotify URL if the graph didn't find a new one
            # search_spotify_album relies on web search which is non-deterministic;
            # fall back to the URL already stored in the current record.
            if not enhanced_metadata.get("spotify_url") and existing_spotify_url:
                enhanced_metadata["spotify_url"] = existing_spotify_url
                logger.info(f"Preserved existing Spotify URL (not found by graph): {existing_spotify_url}")
            
            # STEP 3B: Estimate value based on extracted metadata using web search
            estimated_value_eur = None
            valuation_factors = []
            search_query = None
            search_results_count = 0
            valuation_text = None
            search_sources = []
            try:
                if enhanced_metadata.get("artist") and enhanced_metadata.get("title"):
                    logger.info(f"Performing web search for value estimation during reanalysis: {enhanced_metadata.get('artist')} - {enhanced_metadata.get('title')}")
                    
                    # Build search query with catalog number if available
                    search_query = f"{enhanced_metadata.get('artist')} {enhanced_metadata.get('title')} vinyl record price"
                    if enhanced_metadata.get("catalog_number"):
                        search_query += f" {enhanced_metadata.get('catalog_number')}"
                    if enhanced_metadata.get("year"):
                        search_query += f" {enhanced_metadata.get('year')}"
                    
                    logger.info(f"Web search query for reanalysis: {search_query}")
                    
                    # Perform web search
                    search_results = chat_tools.search_and_scrape(
                        search_query,
                        scrape_results=True
                    )
                    
                    search_results_count = len(search_results.get("search_results", []))
                    logger.info(f"Reanalysis web search found {search_results_count} results")
                    
                    # Build market context from search results
                    market_context = "Market Research Results:\n"
                    if search_results.get("search_results"):
                        for result in search_results["search_results"][:12]:
                            market_context += f"- {result.get('title', '')}: {result.get('content', '')}\n"
                            # Capture for intermediate results
                            search_sources.append({
                                "title": result.get("title", ""),
                                "content": result.get("content", "")[:200]
                            })
                    
                    if search_results.get("scraped_content"):
                        market_context += "\nDetailed Pricing Information:\n"
                        for content in search_results["scraped_content"][:3]:
                            if content.get("success"):
                                market_context += f"- {content.get('title', '')}: {content.get('content', '')}\n"
                    
                    # Build record context
                    record_context = f"""
Vinyl Record Details:
- Artist: {enhanced_metadata.get('artist')}
- Title: {enhanced_metadata.get('title')}
- Year: {enhanced_metadata.get('year') or 'Unknown'}
- Label: {enhanced_metadata.get('label') or 'Unknown'}
- Catalog Number: {enhanced_metadata.get('catalog_number') or 'Unknown'}
- Genres: {', '.join(enhanced_metadata.get('genres', [])) if enhanced_metadata.get('genres') else 'Unknown'}
- Image Analysis Confidence: {new_confidence * 100:.0f}%
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
                        logger.info(f"Claude valuation during reanalysis: {valuation_text[:200]}")
                        
                        # Parse Claude's response
                        import re
                        price_range_min = None
                        price_range_max = None
                        market_condition = "stable"
                        explanation = ""
                        
                        for line in valuation_text.split('\n'):
                            # Strip and check for key markers
                            line_stripped = line.strip()
                            if line_stripped.startswith('ESTIMATED_VALUE:') or 'ESTIMATED_VALUE:' in line_stripped:
                                match = re.search(r'€?([\d.]+)', line)
                                if match:
                                    estimated_value_eur = float(match.group(1))
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
                                valuation_factors = [f.strip() for f in factors_text.split(',')]
                            elif line.startswith('EXPLANATION:'):
                                explanation = line.replace('EXPLANATION:', '').strip()
                        
                        # Fallback if parsing fails
                        if estimated_value_eur is None:
                            prices = re.findall(r'€([\d.]+)', valuation_text)
                            if prices:
                                estimated_value_eur = float(prices[0])
                        
                        if estimated_value_eur is not None:
                            logger.info(f"Reanalysis: Web-based value estimate: €{estimated_value_eur}")
                    
                    except Exception as e:
                        logger.error(f"Error calling Claude for reanalysis valuation: {e}")
                        # Continue without valuation
                
            except Exception as e:
                logger.error(f"Error during web search valuation in reanalysis: {e}")
                # Continue without valuation
            
            # STEP 4: Build response with analyzed metadata
            # Create intermediate results for display in chat panel
            reanalysis_intermediate_results = None
            if search_query:
                reanalysis_intermediate_results = {
                    "search_query": search_query,
                    "search_results_count": search_results_count,
                    "claude_analysis": valuation_text,
                    "search_sources": search_sources
                }
            
            response_data = VinylRecordResponse(
                record_id=record_id,
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow(),
                status="analyzed",
                metadata=VinylMetadataModel(
                    artist=enhanced_metadata.get("artist"),
                    title=enhanced_metadata.get("title"),
                    year=enhanced_metadata.get("year"),
                    label=enhanced_metadata.get("label"),
                    catalog_number=enhanced_metadata.get("catalog_number"),
                    barcode=enhanced_metadata.get("barcode"),
                    genres=enhanced_metadata.get("genres"),
                    spotify_url=enhanced_metadata.get("spotify_url"),
                    condition=enhanced_metadata.get("condition"),
                    confidence=new_confidence,
                    estimated_value_eur=estimated_value_eur,  # Include the newly estimated value
                    estimated_value_usd=None,  # USD not calculated in reanalysis, set to None
                ),
                evidence_chain=_serialize_evidence_chain(result_state.get("evidence_chain", [])),
                confidence=new_confidence,
                auto_commit=result_state.get("auto_commit", False),
                needs_review=result_state.get("needs_review", True),
                error=result_state.get("error"),
                user_notes=None,
                intermediate_results=reanalysis_intermediate_results,
            )
            
            logger.info(f"Completed re-analysis for {record_id}: confidence={new_confidence:.2f}, estimated_value_eur={estimated_value_eur}")
            return response_data
        
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error during smart re-analysis: {e}")
            # Return error response without database updates
            return VinylRecordResponse(
                record_id=record_id,
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow(),
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
