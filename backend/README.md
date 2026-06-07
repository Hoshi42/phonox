# Phonox Backend

AI-powered vinyl record identification and collection management system.

## Architecture

The backend uses a **LangGraph-based agent workflow** that orchestrates vinyl record identification through multiple data sources.

### Agent Workflow (6-node graph)

```
validate_images
    ↓
extract_features
    ↓
vision_extraction (Claude 3 multimodal)
    ↓
lookup_metadata (Discogs + MusicBrainz)
    ↓
websearch_fallback (Tavily + DuckDuckGo)
    ↓
confidence_gate → auto_commit or requires_review
```

### Directory Structure

```
backend/
├── main.py                 # FastAPI app entry point
├── database.py             # SQLAlchemy ORM models
├── agent/
│   ├── graph.py           # LangGraph workflow builder
│   ├── state.py           # State models (TypedDict)
│   ├── vision.py          # Claude 3 multimodal analysis
│   ├── metadata.py        # Discogs/MusicBrainz lookup
│   ├── websearch.py       # Tavily web search
│   ├── barcode_utils.py   # Barcode validation/parsing
│   └── __init__.py
├── api/
│   ├── routes.py          # API endpoints (/identify, /chat)
│   ├── register.py        # Register endpoints (/register)
│   ├── models.py          # Pydantic request/response models
│   └── __init__.py
└── tools/
    ├── web_tools.py       # Utility functions for web search
    └── __init__.py
```

## Key Components

### 1. Vision Extraction (`agent/vision.py`)

Uses Claude 3 Sonnet multimodal analysis to extract metadata from vinyl record artwork:
- Artist, title, year
- Label, catalog number
- Genres, visual cues
- Album art characteristics

**Cost**: ~$0.002 per image

### 2. Metadata Lookup (`agent/metadata.py`)

Queries structured databases:
- **Discogs**: Comprehensive vinyl database with pricing
- **MusicBrainz**: Music metadata with acoustic fingerprinting
- Returns normalized metadata with confidence scores

**Cost**: Free (rate-limited)

### 3. Web Search Fallback (`agent/websearch.py`)

When primary sources have low confidence (<0.75):
- Uses Tavily API for targeted web search
- Falls back to DuckDuckGo for free search
- Extracts relevant sources and information
- Returns structured results with citations

**Cost**: ~$0.0005 per search (Tavily)

### 4. Confidence Gate (`agent/graph.py`)

Decision logic:
- High confidence (>0.85) → Auto-commit to register
- Medium confidence (0.65-0.85) → Send for user review
- Low confidence (<0.65) → Require manual input

## API Endpoints

### Identification

```bash
POST /api/v1/identify
Content-Type: multipart/form-data
- images: File[] (jpeg, png, webp, gif)

Response: { record_id, status: 'pending' }
```

```bash
GET /api/v1/identify/{record_id}
Response: { status, artist, title, confidence, ... }
```

### Chat

```bash
POST /api/v1/chat
Body: { message: string, thread_id?: string }
Response: { message, web_enhanced?, collection_queried?, sources_used?, search_results? }
# web_enhanced=true  — web_search or search_vinyl_prices was called
# collection_queried=true — query_collection or quiz_collection was called
```

### Register (Collection Management)

```bash
POST /api/register/add
Body: { user_tag, vinyl_record_data }
Response: { id, created_at }

GET /api/register?user_tag=user1
Response: RegisterRecord[]

DELETE /api/register/{record_id}
Response: { success: true }
```

## Chat Agent (`agent/chat_agent.py`)

A separate **LangGraph ReAct agent** handles the `/api/v1/chat` endpoint. It runs a `START → agent ↔ tools → END` graph with `PostgresSaver` memory (one thread per record or session).

### Chat Tools

| Tool | Purpose |
|------|---------|
| `web_search` | Tavily/DuckDuckGo search for vinyl history, pressings, labels |
| `search_vinyl_prices` | Market pricing lookup for a specific artist + title |
| `query_collection` | Query `vinyl_records` table — full-schema filtering, sorting, count/stats |
| `quiz_collection` | Generate multiple-choice quizzes from the user's collection |

### `query_collection` parameters

| Parameter | Type | Description |
|-----------|------|-------------|
| `artist`, `title`, `genre`, `label`, `catalog_number` | `str` | Partial match (ilike) |
| `barcode` | `str` | Exact match |
| `condition` | `str` | `poor`/`fair`/`good`/`excellent`/`near_mint` |
| `notes` | `str` | Full-text search in `user_notes` |
| `needs_review` | `bool` | Filter pending/reviewed records |
| `user_tag` | `str` | Exact match |
| `year_from`, `year_to` | `int` | Year range |
| `value_min`, `value_max` | `float` | Estimated value range (EUR) |
| `sort_by` | `str` | `value`\|`year`\|`artist`\|`title`\|`label`\|`created_at` |
| `sort_order` | `str` | `asc`\|`desc` |
| `limit` | `int` | 1–50, hard-capped at 50 |
| `count_only` | `bool` | Returns aggregated stats only (count, total/avg/max value) |

### Limits

- **Token budget**: 24K tokens per LLM call (`trim_messages`)
- **Message cap**: 40 messages per thread in Postgres
- **Result cap**: 50 records per `query_collection` call

---

## Database Models

### VinylRecord

```python
- id: UUID (primary key)
- status: pending | processing | complete | failed
- artist, title, year, label, catalog_number, barcode
- genres: JSON array (stored as Text)
- confidence: float
- spotify_url, estimated_value_eur, condition, user_tag, user_notes
- in_register: bool
- needs_review, auto_commit, validation_passed: bool
- created_at, updated_at: DateTime
```

### VinylImage

```python
- id: UUID
- record_id: UUID (FK to VinylRecord)
- filename: str
- file_data: BLOB
- created_at: DateTime
```

## Environment Variables

```env
# Anthropic (required for vision analysis)
ANTHROPIC_API_KEY=sk-...
ANTHROPIC_VISION_MODEL=claude-sonnet-4-6
ANTHROPIC_CHAT_MODEL=claude-haiku-4-5-20251001

# Tavily (optional, falls back to DuckDuckGo)
TAVILY_API_KEY=tvly-...

# Database
DATABASE_URL=postgresql://user:pass@localhost/phonox

# Image storage
UPLOAD_DIR=/app/uploads

# Server
SERVER_PORT=8000
```

## Image Storage

Images are stored on disk at `UPLOAD_DIR` (`/app/uploads` in production):
- One file per image upload
- Database stores: filename, file_path, content_type, file_size
- Backed up with `backup.sh` (tar.gz format)
- Restored with `restore.sh`

**Why disk storage?** 
- Faster file access compared to database blobs
- Standard practice for image-heavy applications
- Separates concerns: metadata in DB, files on disk

## Development

### Install Dependencies

```bash
pip install -r requirements.txt
```

### Run Locally

```bash
python -m backend.main
# API available at http://localhost:8000
# Docs at http://localhost:8000/docs
```

### Run Tests

```bash
pytest tests/
```

## Performance Metrics

- **Image validation**: <100ms
- **Vision extraction**: ~2-3s per image
- **Metadata lookup**: ~500ms per source
- **Web search**: ~1-2s per search
- **End-to-end**: ~5-8s for typical record

## Future Enhancements

- [ ] Acoustic fingerprinting for audio analysis
- [ ] Batch image processing
- [ ] Advanced caching for repeated searches
- [ ] GraphQL API option
- [ ] Real-time WebSocket updates for long-running jobs
- [ ] Rate limiting and authentication
- [ ] Advanced analytics and insights

## Troubleshooting

### Vision extraction fails
- Check ANTHROPIC_API_KEY is set
- Verify image format (JPEG, PNG, WebP, GIF)
- Image must contain visible album artwork

### Low confidence results
- Ensure good image quality
- Try multiple album art photos
- Check if record is in Discogs/MusicBrainz

### Web search not working
- Set TAVILY_API_KEY for premium search
- DuckDuckGo fallback requires internet connection
