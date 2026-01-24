# Architecture Decision: Multimodal LLM + Websearch Integration

**Date**: 2026-01-24  
**Status**: PROPOSED  
**Impact**: Phase 1 (Agent), Phase 2 (Tools)  
**Scope**: LLM selection, vision pipeline, search integration

---

## Decision Summary

The Phonox agent should be enhanced with:

1. **Multimodal Vision Model** – Analyze album artwork, labels, and sleeve art
2. **Websearch Integration** – Look up vinyl records online (Discogs fallback, artist info, label details)
3. **Hybrid LLM Strategy** – Use vision model for images, LLM for reasoning

---

## Problem Statement

Current Phonox workflow:
1. User uploads vinyl album images
2. Agent extracts features (ViT-base embeddings)
3. Calls Discogs & MusicBrainz APIs
4. Returns metadata

**Limitations**:
- ❌ No vision understanding of album text (artist, title, year printed on sleeve)
- ❌ No fallback if APIs fail
- ❌ No context about pressing, catalog number from image alone
- ❌ Can't verify information if primary sources unavailable

**Solution**: Add multimodal vision + websearch

---

## Option 1: Claude 3 + Tavily Websearch (RECOMMENDED)

**Vision Model**: Claude 3 Opus/Sonnet (Anthropic)

```python
# Vision extraction
response = anthropic.messages.create(
    model="claude-3-sonnet-20240229",
    max_tokens=1024,
    messages=[{
        "role": "user",
        "content": [
            {
                "type": "image",
                "source": {
                    "type": "base64",
                    "media_type": "image/jpeg",
                    "data": base64_image
                }
            },
            {
                "type": "text",
                "text": """Analyze this vinyl album cover and extract:
                - Artist name
                - Album title
                - Year (if visible)
                - Label name
                - Catalog number
                - Genre hints
                
                Return as JSON."""
            }
        ]
    }]
)
```

**Websearch Tool**: Tavily API (specialized for AI agents)

```python
# Tavily websearch
response = tavily_client.search(
    query="Pink Floyd Dark Side of the Moon vinyl pressing",
    include_images=True,
    max_results=5
)
# Returns: title, content, raw_content, source_url, image_url
```

**Pros**:
- ✅ Claude 3 Sonnet: $3/$15 per 1M tokens (cost-effective)
- ✅ Native base64 image support (no preprocessing needed)
- ✅ Tavily: AI-optimized search (not general Google scraping)
- ✅ Both have good rate limits for hobby projects
- ✅ Easy JSON extraction from Claude responses
- ✅ Proven in LangGraph + LangChain ecosystem

**Cons**:
- ❌ API dependencies (not local)
- ❌ Requires API keys management

---

## Option 2: GPT-4 Vision + SerpAPI

**Vision Model**: GPT-4V (OpenAI)

```python
response = openai.ChatCompletion.create(
    model="gpt-4-vision-preview",
    messages=[{
        "role": "user",
        "content": [
            {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{base64_image}"}},
            {"type": "text", "text": "Extract vinyl album metadata..."}
        ]
    }],
    max_tokens=1024
)
```

**Websearch Tool**: SerpAPI or Serper

```python
response = google_search_api.search("Pink Floyd Dark Side vinyl")
# Returns: organic_results, images, knowledge_graph, etc.
```

**Pros**:
- ✅ GPT-4V: State-of-the-art vision
- ✅ More established with LangChain

**Cons**:
- ❌ Expensive ($0.01-0.03 per image for GPT-4V)
- ❌ SerpAPI has higher costs than Tavily
- ❌ Rate limits more restrictive

---

## Option 3: Local Vision (Ollama/LLaMA 2 Vision)

**Vision Model**: LLaMA 2 Vision (local, self-hosted)

```python
# Using Ollama locally
ollama.generate(
    model="llava",  # Vision-capable LLaMA
    prompt="Analyze vinyl album cover...",
    images=["base64_image"]
)
```

**Websearch Tool**: None (local only)

**Pros**:
- ✅ No API costs
- ✅ Private (no data sent out)
- ✅ No rate limits

**Cons**:
- ❌ Requires 16-24GB GPU
- ❌ Slower than cloud models
- ❌ No websearch capability (requires external tool)
- ❌ Quality not as good as Claude 3/GPT-4

---

## Recommended Architecture: **Option 1 (Claude 3 + Tavily)**

### Why?

1. **Cost**: Claude 3 Sonnet ($3/$15 per 1M) vs GPT-4V ($10/$30 per 1M images)
2. **Simplicity**: Single provider, good integration with LangGraph
3. **Quality**: Claude 3 Sonnet competitive with GPT-4 for structured extraction
4. **Search**: Tavily specifically designed for AI agents (better than generic Google scraping)
5. **Ecosystem**: Best supported in LangChain/LangGraph

### Cost Breakdown (per album analyzed)

**Vision Analysis**:
- Input: ~500 tokens (prompt + image) = $0.0015
- Output: ~200 tokens (JSON response) = $0.0006
- **Per image**: ~$0.002 (very cheap)

**Websearch** (fallback):
- Tavily basic: Free tier (10 requests/month) or $20/month for 100+ requests
- **Per search**: ~$0.002-0.003 if paid

**Total per album**: ~$0.004-0.006 (less than $0.01)

### New Agent Pipeline

```
┌─────────────────┐
│  Upload Album   │
│   (1+ images)   │
└────────┬────────┘
         │
    ┌────▼─────────────────────┐
    │ Vision Node (Claude 3)   │
    │ Extract from album art:  │
    │ - Artist, title, year    │
    │ - Label, catalog #       │
    │ - Genres, pressing info  │
    └────┬─────────────────────┘
         │
    ┌────▼──────────────────────────┐
    │ Metadata Lookup Node          │
    │ - Try Discogs API (primary)   │
    │ - Try MusicBrainz API         │
    │ - Fallback: Websearch        │
    └────┬───────────────────────────┘
         │
    ┌────▼──────────────────────────┐
    │ Confidence Gate Node           │
    │ Combine vision + API evidence  │
    │ Calculate confidence           │
    └────┬───────────────────────────┘
         │
    ┌────▼──────────────────────────┐
    │ Output Node                    │
    │ Return metadata with           │
    │ evidence chain + confidence    │
    └────────────────────────────────┘
```

---

## State Model Changes Required

### Add to VinylState

```python
class VinylState(TypedDict):
    images: List[str]  # Album cover images (base64)
    # NEW FIELDS:
    vision_extraction: Optional[dict]  # From Claude vision analysis
    websearch_results: Optional[List[dict]]  # From Tavily
    
    metadata: Optional[VinylMetadata]
    evidence_chain: List[Evidence]
    status: str
    error: Optional[str]
```

### Update Evidence with vision source

```python
class Evidence(TypedDict):
    source: str  # "discogs", "musicbrainz", "image", "vision", "websearch"
    confidence: float
    data: dict
    timestamp: datetime
```

### Update CONFIDENCE_WEIGHTS

```python
CONFIDENCE_WEIGHTS = {
    "discogs": 0.45,        # Still most reliable
    "musicbrainz": 0.25,    # Good secondary source
    "vision": 0.20,         # Claude vision analysis
    "websearch": 0.10,      # Fallback/supplementary
}
```

---

## Phase Timeline Impact

### Phase 1: Core Agent (Weeks 2-3)
- Add vision node (calls Claude 3 API)
- Add websearch node (calls Tavily API)
- Update confidence calculation

### Phase 2: Tools (Weeks 3-4)
- Tool 1: Vision extraction (Claude 3)
- Tool 2: Websearch (Tavily)
- Tool 3-4: Keep existing (Discogs, MusicBrainz)
- Tool 5: Fallback chain logic

### Phase 3: Backend (Weeks 4-5)
- FastAPI endpoint accepts base64 images
- Streaming response for long-running vision analysis
- Cache vision results (same album image = same extraction)

---

## API Keys Required

### 1. Anthropic (Claude 3)

```bash
# .env
ANTHROPIC_API_KEY=sk-ant-...
```

**Setup**:
```bash
pip install anthropic
```

**Pricing**: $3 per 1M input tokens, $15 per 1M output tokens

**Free tier**: 5 requests/minute, then $5 free credit

### 2. Tavily Search

```bash
# .env
TAVILY_API_KEY=tvly-...
```

**Setup**:
```bash
pip install tavily-python
```

**Pricing**: Free tier (10/month) or $20/month (unlimited)

### 3. Keep Existing

- Discogs (free, no key needed)
- MusicBrainz (free, no key needed)
- ViT-base embedding (local, no key)

---

## Code Examples

### Vision Node (for Phase 1.2)

```python
# backend/agent/nodes/vision.py
import anthropic
import base64
from backend.agent.state import VinylState, Evidence

def vision_extraction_node(state: VinylState) -> dict:
    """Extract metadata from album images using Claude 3 vision."""
    
    if not state["images"]:
        return {"vision_extraction": None}
    
    client = anthropic.Anthropic()
    
    # Analyze first image (main album cover)
    image_base64 = state["images"][0]
    if image_base64.startswith("data:"):
        # Remove data URI prefix if present
        image_base64 = image_base64.split(",")[1]
    
    message = client.messages.create(
        model="claude-3-sonnet-20240229",
        max_tokens=1024,
        messages=[
            {
                "role": "user",
                "content": [
                    {
                        "type": "image",
                        "source": {
                            "type": "base64",
                            "media_type": "image/jpeg",
                            "data": image_base64,
                        },
                    },
                    {
                        "type": "text",
                        "text": """Analyze this vinyl album cover/artwork and extract metadata.

Return ONLY valid JSON with this structure:
{
    "artist": "Artist name or null",
    "title": "Album title or null",
    "year": 1969 or null,
    "label": "Record label or null",
    "catalog_number": "Catalog # or null",
    "genres": ["genre1", "genre2"] or [],
    "pressing_info": "Pressing info if visible or null",
    "confidence": 0.75
}

Be conservative with confidence (0.5-0.95 range). Only mark high confidence if text is clearly legible."""
                    }
                ],
            }
        ],
    )
    
    try:
        response_text = message.content[0].text
        vision_data = json.loads(response_text)
        
        # Create evidence entry
        evidence: Evidence = {
            "source": "vision",
            "confidence": vision_data.pop("confidence", 0.70),
            "data": vision_data,
            "timestamp": datetime.now(),
        }
        
        return {
            "vision_extraction": vision_data,
            "evidence_chain": state["evidence_chain"] + [evidence],
        }
    
    except (json.JSONDecodeError, IndexError) as e:
        return {
            "vision_extraction": None,
            "error": f"Vision extraction failed: {str(e)}",
        }
```

### Websearch Node (for Phase 1.3)

```python
# backend/agent/nodes/websearch.py
from tavily import TavilyClient
from backend.agent.state import VinylState, Evidence

def websearch_node(state: VinylState) -> dict:
    """Search web for vinyl record metadata if API lookups fail."""
    
    # Only search if confidence is too low
    if state["evidence_chain"]:
        current_confidence = calculate_overall_confidence(state["evidence_chain"])
        if current_confidence >= 0.75:
            return {"websearch_results": None}  # Good enough, skip
    
    client = TavilyClient(api_key=os.getenv("TAVILY_API_KEY"))
    
    # Build search query from available info
    query_parts = []
    if state.get("vision_extraction"):
        vision = state["vision_extraction"]
        if vision.get("artist"):
            query_parts.append(vision["artist"])
        if vision.get("title"):
            query_parts.append(vision["title"])
    
    if not query_parts:
        return {"websearch_results": None}
    
    query = " ".join(query_parts) + " vinyl"
    
    try:
        response = client.search(
            query=query,
            max_results=5,
            include_images=True,
            topic="general"  # or "news" for recent pressings
        )
        
        results = response["results"]
        
        # Create evidence from search results
        evidence: Evidence = {
            "source": "websearch",
            "confidence": 0.60,  # Lower confidence for web results
            "data": {
                "query": query,
                "results": results,
            },
            "timestamp": datetime.now(),
        }
        
        return {
            "websearch_results": results,
            "evidence_chain": state["evidence_chain"] + [evidence],
        }
    
    except Exception as e:
        return {
            "websearch_results": None,
            "error": f"Websearch failed: {str(e)}",
        }
```

---

## Migration Plan

### Phase 1.1 (Current iteration 0.2 replacement)
- ✅ Already done: State models

### Phase 1.2 (NEW iteration)
- Add Claude 3 vision node
- Update Evidence to include "vision" source
- Update CONFIDENCE_WEIGHTS
- Test with sample album images

### Phase 1.3 (NEW iteration)
- Add Tavily websearch node
- Add "websearch" to Evidence sources
- Test fallback chain (Discogs → MusicBrainz → Websearch)

### Phase 1.4 (Updated)
- Integrate all nodes into graph
- End-to-end testing

---

## Testing Strategy

### Unit Tests (Phase 1.2)

```python
def test_vision_extraction_valid_image():
    """Claude vision correctly extracts album metadata."""
    # Mock Claude response
    # Assert JSON parsing works
    # Assert Evidence entry created

def test_vision_extraction_low_quality():
    """Low confidence for unclear images."""
    # Mock blurry image
    # Assert confidence < 0.60

def test_vision_extraction_no_image():
    """Handles missing images gracefully."""
    # Pass empty images list
    # Assert None returned
```

### Integration Tests (Phase 1.3)

```python
def test_websearch_fallback():
    """Websearch used when APIs fail."""
    # Mock Discogs/MB failures
    # Assert websearch node called
    # Assert results combined

def test_confidence_calculation_with_vision():
    """Vision evidence weighted correctly."""
    # Create Evidence list with vision + discogs
    # Assert weighted average calculated
    # Assert discogs (0.45) > vision (0.20)
```

---

## Risk Assessment

| Risk | Probability | Impact | Mitigation |
|------|-------------|--------|-----------|
| Claude API quota exhausted | Low | Medium | Cache results, batch process |
| Tavily search rate limit | Low | Low | Free tier sufficient for hobby |
| Vision hallucination | Medium | Low | Cross-check with Discogs/MB |
| API dependencies | High | Medium | Graceful fallback, error handling |
| Costs exceed budget | Low | Low | Monitor usage, set alerts |

---

## Recommendation

✅ **Proceed with Option 1: Claude 3 Sonnet + Tavily**

**Next Steps**:
1. Add API keys to `.env`
2. Install `anthropic` and `tavily-python` packages
3. Create iteration 1.2 (Vision Node)
4. Create iteration 1.3 (Websearch Node)
5. Update implementation-plan.md with new iterations

**Cost**: ~$0.004 per album (negligible for hobby project)

---
