# Phonox Architecture

Comprehensive guide to the system architecture, data flow, and component interactions.

## System Overview

Phonox is a full-stack AI-powered vinyl record identification system with these key features:

1. **Image-based Record Identification**: Upload photos → AI analysis → Metadata extraction
2. **Multi-source Metadata Enrichment**: Discogs + MusicBrainz + Web search
3. **AI Chat Assistant**: Context-aware queries with web search integration
4. **Personal Collection Management**: Register, organize, valuate records

## Architecture Diagram

```
┌─────────────────────────────────────────────────────────────┐
│                    FRONTEND (React/Vite)                    │
├─────────────────────────────────────────────────────────────┤
│  App.tsx → VinylCard + ChatPanel + VinylRegister            │
│           ↓ (Form + Chat inputs)                             │
└─────────────────────────────────────────────────────────────┘
                           ↓ REST API
┌─────────────────────────────────────────────────────────────┐
│                   BACKEND (FastAPI)                          │
├─────────────────────────────────────────────────────────────┤
│  /api/v1/identify  ─→ Upload images                          │
│  /api/v1/chat      ─→ AI chat with web search                │
│  /api/register/*   ─→ Collection management                  │
│                                                              │
│  ┌──────────────────────────────────────────────────────┐   │
│  │     LangGraph Agent Workflow (6-node graph)         │   │
│  ├──────────────────────────────────────────────────────┤   │
│  │ 1. validate_images      │ Check format, size, count  │   │
│  │ 2. extract_features     │ Image analysis (future)     │   │
│  │ 3. vision_extraction    │ Claude 3 multimodal        │   │
│  │ 4. lookup_metadata      │ Discogs + MusicBrainz      │   │
│  │ 5. websearch_fallback   │ Tavily + DuckDuckGo        │   │
│  │ 6. confidence_gate      │ Route to auto/review       │   │
│  └──────────────────────────────────────────────────────┘   │
│                                                              │
│  ┌──────────────────────────────────────────────────────┐   │
│  │        External Data Sources                         │   │
│  ├──────────────────────────────────────────────────────┤   │
│  │ Claude API (vision analysis, chat)                   │   │
│  │ Discogs API (metadata, pricing)                      │   │
│  │ MusicBrainz API (music metadata)                     │   │
│  │ Tavily API (web search)                              │   │
│  │ Spotify API (audio preview links)                    │   │
│  └──────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────┘
                           ↓
┌─────────────────────────────────────────────────────────────┐
│               PostgreSQL Database                            │
├─────────────────────────────────────────────────────────────┤
│  VinylRecord (main records)                                  │
│  VinylImage (uploaded images)                                │
│  User collections (register)                                 │
└─────────────────────────────────────────────────────────────┘
```

## Data Flow

### 1. Record Identification Flow

```
User uploads image
    ↓
Frontend: POST /api/v1/identify
    ↓
Backend: Create temp record, start analysis
    ↓
LangGraph Agent starts 6-node workflow:
    
    ├→ validate_images
    │   ├ Check format (JPEG, PNG, WebP, GIF)
    │   ├ Check size (<10MB each, <100MB total)
    │   └ Check count (1-10 images)
    │
    ├→ vision_extraction
    │   ├ Claude 3 Sonnet multimodal analysis
    │   ├ Extract: artist, title, year, label, genres, barcode
    │   └ Generate confidence scores per field
    │
    ├→ lookup_metadata
    │   ├ Query Discogs API (catalog lookup)
    │   ├ Query MusicBrainz API (fingerprinting)
    │   ├ Merge results, rank by confidence
    │   └ Enrich with: Spotify URL, condition tips
    │
    ├→ websearch_fallback (if confidence < 0.75)
    │   ├ Tavily search: "artist title vinyl record"
    │   ├ Extract: pricing, pressing info, reviews
    │   ├ DuckDuckGo fallback if Tavily unavailable
    │   └ Citation tracking (sources)
    │
    └→ confidence_gate
        ├ If confidence > 0.85: Auto-commit to register
        ├ If 0.65-0.85: Send for user review
        └ If < 0.65: Request manual input

    Save to database with metadata + images
    ↓
Frontend: Poll /api/v1/identify/{record_id}
    ↓
When complete: Display results in VinylCard
```

### 2. Chat Flow

```
User sends message in ChatPanel
    ↓
Frontend: POST /api/v1/chat or /api/v1/identify/{record_id}/chat
    ├ Record context (if record-specific)
    ├ User message
    └ Chat history (current session)
    ↓
Backend:
    ├ If message starts with "/web": Force web search
    ├ Claude analyzes message + context
    ├ If web search needed:
    │   ├ Tavily web search query
    │   ├ Return results + sources
    │   └ Claude synthesizes answer with citations
    └ Return response + source metadata
    ↓
Frontend: Display message + sources + loading indicators
```

### 3. Register Flow

```
User adds record to collection
    ↓
Frontend: POST /api/register/add
    ├ user_tag (user identifier)
    ├ vinyl_record_data
    └ estimated_value_eur
    ↓
Backend: 
    ├ Validate user_tag format
    ├ Save VinylRecord with user_tag
    ├ Persist images to filesystem + database
    └ Return RegisterRecord
    ↓
Frontend: Update register list, show success
    ↓
User can later:
    ├ View register (GET /api/register?user_tag=X)
    ├ Update record (PUT /api/register/{id})
    ├ Delete record (DELETE /api/register/{id})
    └ Switch users (loads different collection)
```

## Component Interaction Diagram

```
┌──────────────────────────────────────────────────────────┐
│                      App.tsx                              │
│  - Global state: record, register, user                   │
│  - API calls orchestration                                │
│  - Polling logic for long-running jobs                    │
└──────────────────────────────────────────────────────────┘
         ↙         ↓              ↘
    ┌─────────┐  ┌──────────┐  ┌──────────────┐
    │ImageUp- │  │VinylCard │  │VinylRegister │
    │load.tsx │  │.tsx      │  │.tsx          │
    └─────────┘  └──────────┘  └──────────────┘
                       ↓              ↓
                  ┌────────────────────────┐
                  │   ChatPanel.tsx        │
                  │ - AI chat interface    │
                  │ - Web search results   │
                  │ - Context awareness    │
                  └────────────────────────┘
                  
                  │
                  ↓
    ┌──────────────────────────────┐
    │   UserManager.tsx            │
    │ - Auth/user switching        │
    │ - localStorage persistence   │
    └──────────────────────────────┘
```

## Database Schema

### VinylRecord Table

```sql
CREATE TABLE vinyl_records (
  id UUID PRIMARY KEY,
  
  -- Identification
  status VARCHAR (pending | analyzed | complete | error),
  confidence FLOAT (0.0-1.0),
  
  -- Metadata
  artist VARCHAR,
  title VARCHAR,
  year INTEGER,
  label VARCHAR,
  catalog_number VARCHAR,
  barcode VARCHAR (UPC/EAN),
  genres JSONB (array of strings),
  
  -- Details
  metadata JSONB (
    - spotify_url
    - estimated_value_eur
    - estimated_value_usd
    - condition (Mint, Near Mint, VG+, VG, G+, G, F, P)
    - image_urls (array)
  ),
  
  -- Collection
  user_tag VARCHAR (nullable, for register),
  user_notes TEXT,
  
  -- Lifecycle
  created_at TIMESTAMP,
  updated_at TIMESTAMP,
  
  -- Evidence
  evidence_chain JSONB (sources + confidence)
);
```

### VinylImage Table

```sql
CREATE TABLE vinyl_images (
  id UUID PRIMARY KEY,
  record_id UUID FK,
  
  filename VARCHAR,
  file_data BLOB (image data),
  
  created_at TIMESTAMP
);
```

## State Management Strategy

### Frontend State Levels

1. **Global (App.tsx)**
   - Current record
   - Vinyl register
   - Current user
   - Loading/error states

2. **Component Local (useState)**
   - Form inputs (editing)
   - Modal visibility
   - View mode toggles
   - Temporary filters

3. **Browser Storage (localStorage)**
   - User preference (username)
   - Last viewed record
   - View mode preference

### No Redux/Context API

Kept simple because:
- Shallow state tree
- Limited cross-component communication
- Props drilling acceptable for 3-4 levels
- Easy to understand data flow

## API Request/Response Patterns

### Typical Identification Request

```
POST /api/v1/identify
Content-Type: multipart/form-data

images: [File, File, ...]

---

Response 202 Accepted:
{
  "record_id": "uuid-1234",
  "status": "pending"
}
```

### Polling for Results

```
GET /api/v1/identify/{record_id}

Response (while pending):
{
  "status": "pending",
  "record_id": "uuid"
}

Response (when complete):
{
  "status": "complete",
  "record_id": "uuid",
  "artist": "The Beatles",
  "title": "Abbey Road",
  "confidence": 0.92,
  "metadata": {...},
  "evidence_chain": [...]
}
```

## Performance Characteristics

### Latency Budget (per operation)

```
Upload → Analysis: 5-8 seconds
  ├ Image validation: <100ms
  ├ Vision extraction: 2-3s
  ├ Metadata lookup: 500-1000ms
  └ Web search: 1-2s (if triggered)

Chat response: 1-3 seconds
  ├ Prompt processing: <200ms
  ├ Claude response: 1-2s
  └ Web search: 0-2s (if triggered)

Register operations: <500ms
  ├ API call: 100-200ms
  └ DB operation: 100-300ms
```

### Throughput

- **Concurrent users**: 100+ (not tested beyond this)
- **Image processing**: 1 image per 2-3 seconds
- **API requests**: Limited by FastAPI default (16 workers)

## Security Considerations

### Current Implementation

- No authentication (open API)
- File size limits (10MB per image, 100MB total)
- Image format validation
- Input sanitization (Pydantic models)

### Production Recommendations

- [ ] Add API authentication (OAuth/JWT)
- [ ] Rate limiting per IP
- [ ] CORS configuration
- [ ] HTTPS only
- [ ] Input validation strictness
- [ ] Sanitize markdown output
- [ ] Implement request timeouts

## Scaling Strategy

### Database
- PostgreSQL with indexes on user_tag, created_at, status
- Archive old records (>1 year)
- Consider partitioning by user_tag

### API
- Horizontally scale FastAPI workers
- Add Redis caching for metadata lookups
- Implement request queuing for long-running jobs

### External Services
- Implement caching layer for Discogs/MusicBrainz
- Use Tavily's batch search for cost optimization
- Cache Claude responses for common queries

## Future Architecture Changes

1. **Microservices**: Separate vision → metadata → websearch services
2. **Message Queue**: Celery/Kafka for asynchronous processing
3. **WebSockets**: Real-time chat and status updates
4. **GraphQL**: Flexible query language for complex data
5. **Analytics**: Tracking user behavior, record popularity
