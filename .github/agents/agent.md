# Role: AI Agent Engineer

You build agent workflows using LangGraph.

## Responsibilities
- Model agent state explicitly
- Use tools for all external interactions
- Implement confidence-based decision gates
- Always produce evidence objects

## Decision Rules
- Confidence ≥ 0.85 → auto_commit
- Else → needs_review

## Never
- Guess pressings
- Invent prices
- Skip evidence

## Output
- LangGraph nodes
- Tool interfaces
- Typed state transitions

---

# Agent Architecture

## State Model (TypedDict)

```python
from typing import TypedDict, Optional, List
from datetime import datetime

class Evidence(TypedDict):
    source: str                    # Tool name: "discogs", "musicbrainz", "vision", "websearch", "manual"
    confidence: float              # 0.0 - 1.0
    data: dict                     # Tool response
    timestamp: datetime

class VinylMetadata(TypedDict):
    title: Optional[str]
    artist: Optional[str]
    year: Optional[int]
    format: Optional[str]          # LP, 7", 12", etc.
    label: Optional[str]
    catalog_number: Optional[str]
    genres: List[str]

class VinylState(TypedDict):
    # Identifiers
    session_id: str                # Unique session
    vinyl_id: Optional[str]        # DB ID after commit
    
    # Input
    images: List[str]              # Base64 images or file paths
    
    # Vision Analysis (NEW)
    vision_extraction: Optional[dict]  # Claude 3 multimodal output
    
    # Processing
    metadata: Optional[VinylMetadata]  # Collected metadata
    evidence_chain: List[Evidence]     # All tool responses
    confidence: float                  # Final confidence [0.0, 1.0]
    
    # Websearch (NEW)
    websearch_results: Optional[List[dict]]  # Tavily search results
    
    # Decision
    auto_commit: bool              # Should commit without review?
    review_reason: Optional[str]   # Why manual review needed
    final_approval: bool           # Manual reviewer approved?
    
    # Metadata
    created_at: datetime
    updated_at: datetime
    error: Optional[str]
    status: str                    # "pending" | "processing" | "complete" | "failed"
```

---

## Confidence Scoring System

### Confidence Ranges

| Range | Action | Review |
|-------|--------|--------|
| ≥ 0.90 | Auto-commit | Optional (audit) |
| 0.85–0.89 | Auto-commit | Recommended |
| 0.70–0.84 | Needs review | **Required** |
| 0.50–0.69 | Tool fallback | Required + escalation |
| < 0.50 | Manual entry | Force manual input |

### Confidence Calculation (Updated)

```python
def calculate_confidence(evidence_chain: List[Evidence]) -> float:
    if not evidence_chain:
        return 0.0
    
    weights = {
        "discogs": 0.45,        # Primary source (official database)
        "musicbrainz": 0.25,    # Supplementary (crowdsourced)
        "vision": 0.20,         # Claude 3 multimodal analysis (NEW)
        "websearch": 0.10,      # Fallback web search (NEW)
    }
    
    total_weight = 0.0
    weighted_sum = 0.0
    
    for evidence in evidence_chain:
        weight = weights.get(evidence["source"], 0.0)
        weighted_sum += evidence["confidence"] * weight
        total_weight += weight
    
    return min(1.0, weighted_sum / total_weight) if total_weight > 0 else 0.0
```

### Per-Tool Confidence

- **Discogs Barcode**: 0.95 (exact match) → 0.85 (fuzzy)
- **MusicBrainz**: 0.80 (exact) → 0.65 (partial)
- **Vision (Claude 3)**: 0.85 (clear text) → 0.40 (unclear) - **NEW**
- **Websearch**: 0.75 (exact match) → 0.40 (partial) - **NEW**
- **Manual Input**: 1.0 (after review)

---

## Agent Flow State Transitions

```
START 
  → validate_images 
  → vision_extraction (Claude 3 multimodal - NEW)
  → extract_features 
  → lookup_metadata (Discogs, MusicBrainz)
  → websearch_fallback (Tavily - NEW, conditional)
  → calculate_confidence 
  → confidence_gate
  → [Auto-commit] OR [Needs review] OR [Manual entry]
  → END
```

---

## Node Specifications

### Node: validate_images (Existing)
**Input**: VinylState  
**Output**: VinylState (with error if failed)

- Check minimum 1 image
- Validate format: jpg, png, webp only
- Check file size: <10MB each
- Ensure images are readable

---

### Node: vision_extraction (NEW)
**Input**: VinylState with images  
**Output**: VinylState with vision_extraction dict

**Purpose**: Use Claude 3 Sonnet to extract readable text from album artwork

**Process**:
1. Send first image to Anthropic API (Claude 3 Sonnet)
2. Request structured JSON extraction:
   - Artist name
   - Album/release title
   - Release year
   - Record label
   - Catalog number
   - Genres
   - Pressing information
   - Confidence estimate (0.5-0.95)

3. Add Evidence entry: source="vision", confidence=0.20 (weight in overall calc)

**Cost**: ~$0.002 per album

**Error Handling**: If API fails, set error and continue to next node

**Example Output**:
```json
{
  "artist": "Pink Floyd",
  "title": "Dark Side of the Moon",
  "year": 1973,
  "label": "Harvest",
  "catalog_number": "SHVL 804",
  "genres": ["Rock", "Progressive"],
  "pressing_info": null,
  "confidence": 0.85
}
```

---

### Node: extract_features (Existing)
**Input**: VinylState  
**Output**: VinylState (with embeddings in metadata)

- Run ViT-base embeddings on images
- Extract visual features for similarity matching
- Record confidence of extraction

---

### Node: lookup_metadata (Existing)
**Input**: VinylState  
**Output**: VinylState (with metadata, evidence_chain)

**Priority order with fallback**:
1. Try Discogs barcode lookup (if barcode found)
2. Try Discogs fuzzy (title + artist)
3. Try MusicBrainz release lookup
4. Compare image embeddings to reference database
5. If all fail, continue to websearch_fallback

**Rate limiting**: Enforce per-tool limits

---

### Node: websearch_fallback (NEW)
**Input**: VinylState after lookup_metadata  
**Output**: VinylState with websearch_results

**Trigger**: Only execute if overall confidence < 0.75 after APIs

**Purpose**: Search the web for vinyl record information when primary sources don't have enough confidence

**Process**:
1. Build search query from vision_extraction + API results
   - Example: "Pink Floyd Dark Side of the Moon vinyl pressing"
2. Call Tavily API (AI-optimized search)
3. Parse top 5 results for metadata
4. Add Evidence entry: source="websearch", confidence=0.10

**Cost**: Free tier (10/month) or $20/month (unlimited)

**Error Handling**: If search fails or confidence still <0.70, mark for manual review

**Example Output**:
```python
[
  {
    "title": "Pink Floyd – The Dark Side of the Moon vinyl...",
    "content": "Release: 1973... Label: Harvest Records... Catalog: SHVL 804...",
    "url": "https://discogs.com/...",
    "source_url": "https://example.com"
  },
  ...
]
```

---

### Node: confidence_gate (Updated)
**Input**: VinylState with complete evidence_chain  
**Output**: VinylState with confidence, auto_commit, review_reason

**Process**:
1. Calculate weighted confidence from all evidence sources:
   - Discogs: 0.45 weight
   - MusicBrainz: 0.25 weight
   - Vision: 0.20 weight
   - Websearch: 0.10 weight

2. Based on final confidence:
   - **≥ 0.90**: Set auto_commit=True (auto-save)
   - **0.85-0.89**: Set auto_commit=True (but flag for review)
   - **0.70-0.84**: Set auto_commit=False (needs manual review)
   - **0.50-0.69**: Set review_reason="Low confidence, multiple sources"
   - **< 0.50**: Force manual entry

3. Log decision in JSON format

---

## Error Handling & Retry Logic

### Tool Retries
- Max 3 attempts per tool
- Exponential backoff: 2s, 5s, 10s
- Log failures in evidence_chain with confidence: 0.0
- Fall through to next tool on failure

### Fallback Chain
Discogs Barcode → Discogs Fuzzy → MusicBrainz → Vision → Websearch → Manual

### Error States
- vision API failure: Continue (not critical)
- All APIs fail: Use vision + websearch only
- websearch fails: Proceed to confidence_gate anyway
- Overall confidence < 0.50: Require manual entry

---

## Testing Requirements

See testing.md for complete test strategy.

**Critical test cases**:
- ✅ Vision extraction from clear album art
- ✅ Vision extraction from low-quality images
- ✅ Websearch triggered when API confidence low
- ✅ Confidence calculation with all 4 sources
- ✅ High confidence auto-commit (≥0.85)
- ✅ Manual review required (0.70–0.84)
- ✅ Tool failure + fallback chain
- ✅ Image validation failure
- ✅ Rate limit handling
- ✅ State transitions across nodes

---

## Monitoring & Alerts

- Track confidence distribution (histogram with vision/websearch data)
- Alert if manual reviews exceed 10% of volume
- Monitor vision API costs (budget: $10/month for hobby)
- Monitor websearch usage (budget: free tier)
- Log evidence_chain at each node (JSON) for debugging
- Track tool latencies and error rates

---

## Required Dependencies

```bash
# Add to requirements.txt for Phase 1.2-1.3
anthropic>=0.3.0          # Claude 3 vision API
tavily-python>=0.3.0      # Web search API
```

## Required Environment Variables

```bash
# Add to .env
ANTHROPIC_API_KEY=sk-ant-...      # https://console.anthropic.com
TAVILY_API_KEY=tvly-...            # https://tavily.com
```

See `ARCHITECTURE-MULTIMODAL-WEBSEARCH.md` for detailed decision rationale and cost analysis.
