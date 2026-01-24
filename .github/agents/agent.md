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
    source: str                    # Tool name: "discogs", "musicbrainz", "manual"
    confidence: float              # 0.0 - 1.0
    url: str                       # Source URL
    timestamp: datetime
    raw_data: dict                 # Complete response

class VinylMetadata(TypedDict):
    title: Optional[str]
    artist: Optional[str]
    year: Optional[int]
    format: Optional[str]          # LP, 7", 12", etc.
    pressing: Optional[str]        # Pressing info (catalog, barcode)
    condition: Optional[str]       # Near Mint, Very Good, etc.

class VinylState(TypedDict):
    # Identifiers
    session_id: str                # Unique session
    vinyl_id: Optional[str]        # DB ID after commit
    
    # Input
    images: List[str]              # File paths or URLs
    image_features: dict           # Extracted embeddings
    
    # Processing
    metadata: VinylMetadata        # Collected metadata
    evidence_chain: List[Evidence] # Tool responses
    confidence: float              # Final confidence [0.0, 1.0]
    
    # Decision
    auto_commit: bool              # Should commit without review?
    review_reason: Optional[str]   # Why manual review needed
    final_approval: bool           # Manual reviewer approved?
    
    # Metadata
    created_at: datetime
    updated_at: datetime
    error: Optional[str]
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

### Confidence Calculation

```python
def calculate_confidence(evidence_chain: List[Evidence]) -> float:
    if not evidence_chain:
        return 0.0
    
    weights = {
        "discogs": 0.5,        # Primary source
        "musicbrainz": 0.3,    # Supplementary
        "image_match": 0.2,    # Visual confirmation
    }
    
    total_weight = 0.0
    weighted_sum = 0.0
    
    for evidence in evidence_chain:
        weight = weights.get(evidence["source"], 0.1)
        weighted_sum += evidence["confidence"] * weight
        total_weight += weight
    
    return min(1.0, weighted_sum / total_weight) if total_weight > 0 else 0.0
```

### Per-Tool Confidence

- **Discogs Direct Match**: 0.95 (barcode) → 0.85 (fuzzy)
- **MusicBrainz**: 0.80 (exact) → 0.65 (partial)
- **Image Feature Match**: 0.70 (high) → 0.40 (low)
- **Manual Input**: 1.0 (after review)

---

## Agent Flow State Transitions

START → validate_images → extract_features → lookup_metadata → calculate_confidence → confidence_gate

Decision branches:
- **Auto-commit** (≥0.85): Save → generate_pdf → END
- **Needs review** (0.70–0.84): Manual approval required
- **Manual entry** (<0.50): Force user to input data

---

## Node Specifications

### Node: validate_images
**Input**: VinylState  
**Output**: VinylState (with error if failed)

- Check minimum 2 images (front + spine/back)
- Validate format: jpg, png, webp only
- Check file size: <10MB each
- Ensure images are readable

### Node: extract_features
**Input**: VinylState  
**Output**: VinylState (with image_features, metadata extracted)

- Run ViT-base embeddings
- OCR extraction: title, artist, label
- Color analysis, condition detection

### Node: lookup_metadata
**Input**: VinylState  
**Output**: VinylState (with evidence_chain, metadata)

**Priority order with fallback**:
1. Discogs barcode lookup
2. Discogs fuzzy (title + artist)
3. MusicBrainz release lookup
4. Image similarity matching
5. No metadata found → needs_manual_entry

**Rate limiting**: Enforce per-tool limits (Discogs: 60/min, MB: 1/sec)

### Node: confidence_gate
**Input**: VinylState  
**Output**: VinylState (with confidence, auto_commit, review_reason)

- Calculate weighted confidence from evidence_chain
- Set auto_commit flag if ≥0.85
- Set review_reason if <0.85
- Set needs_manual_entry if <0.50

---

## Error Handling & Retry Logic

### Tool Retries
- Max 3 attempts per tool
- Exponential backoff: 2s, 5s, 10s
- Log failures in evidence_chain with confidence: 0.0
- Fall through to next tool on failure

### Fallback Chain
Discogs Barcode → Discogs Fuzzy → MusicBrainz → Image Match → Manual

---

## Testing Requirements

See testing.md for complete test strategy.

**Critical test cases**:
- ✅ High confidence auto-commit (≥0.85)
- ✅ Manual review required (0.70–0.84)
- ✅ Tool failure + fallback
- ✅ Image validation failure
- ✅ Rate limit handling
- ✅ State transitions across nodes

---

## Monitoring & Alerts

- Track confidence distribution (histogram)
- Alert if manual reviews exceed 10% of volume
- Log evidence_chain at each node (JSON)
- Monitor tool latencies and error rates
