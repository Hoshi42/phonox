# API Endpoints

Complete reference for all Phonox API endpoints.

## Collection Magazine

All magazine routes require a nonblank `user_tag` query parameter (max 50
characters). It is the existing collection scope, not an authenticated identity.
At most one magazine belongs to each user. See
[the user guide](../user-guide/collection.md#pdf-collection-magazine) for the workflow.

### GET /api/magazine

```bash
curl 'http://localhost:8000/api/magazine?user_tag=collector'
```

Returns `id`, `user_tag`, `status`, `phase`, `error`, `has_pdf`, `edition`,
`page_count`, `record_count`, `published_at`, `changes` (`added`, `changed`,
`removed`), `settings`, `draft_version`, optional `draft`, `warnings`,
`research_step_limit` and `estimated_cost_eur`.
Set `include_draft=false` to omit editorial content. Status values are
`not_created`, `preparing`, `draft`, `rendering`, `complete`, `failed` and
`cancelled`. Opening a completed PDF never starts research.

### POST /api/magazine/prepare

```bash
curl -X POST 'http://localhost:8000/api/magazine/prepare?user_tag=collector' \
  -H 'Content-Type: application/json' \
  -d '{
    "title": "My Vinyl Collection",
    "subtitle": "Records and stories",
    "display_name": "",
    "preface": "",
    "cover_image_id": null,
    "include_notes": false,
    "research": true,
    "refresh_values": true,
    "consent": true
  }'
```

Returns **202** with magazine status. Poll GET until `draft` or an explicit
failure. The same route updates an existing magazine; it never creates a
second magazine for that user. An active job is returned instead of starting
duplicate work. Empty collections and missing research consent return **400**.
Set `research=false` to avoid external calls; stored values remain explicitly
labelled with unknown dates unless an earlier magazine valuation has a real date.
Omitted editorial settings inherit the previous draft/edition's settings.

Each database lookup, web search invocation or AI call uses one of 20 allowed
steps. AI output has a 1,200-token limit and no automatic retries. A web search
step may invoke the existing helper's bounded Tavily/DuckDuckGo fallback.
Allowance estimates are not guaranteed bills. Partial research failures and
budget exhaustion are recorded in the draft/PDF; no default price is invented.

### PUT /api/magazine/draft

```json
{
  "version": 1,
  "preface": "My personal foreword.",
  "records": [
    {
      "id": "record-id-from-draft",
      "group": "Artist chapter",
      "description": "My reviewed record description."
    }
  ],
  "artists": [
    {
      "name": "Artist chapter",
      "portrait": "My reviewed artist portrait."
    }
  ]
}
```

Include every snapshot record exactly once. Editing cannot add another user's
records or alter snapshot images/values. The response contains the refreshed
draft, including newly grouped chapters and incremented `draft_version`.
A stale version or active job returns **409**.

### POST /api/magazine/publish

Body: `{"version": 2}` using the latest reviewed `draft_version`.
Returns **202**; poll until `complete` or `failed`. Stale approval/no draft
returns **409**. The existing PDF is replaced atomically only on success.

### PDF, snapshot images, cancellation and deletion

```text
GET    /api/magazine/pdf?user_tag=collector
GET    /api/magazine/pdf?user_tag=collector&download=true
GET    /api/magazine/images/{image_id}?user_tag=collector
POST   /api/magazine/cancel?user_tag=collector
DELETE /api/magazine?user_tag=collector
```

PDF responses use `application/pdf`, inline or attachment disposition, and
`Cache-Control: private, no-store`. No completed PDF returns **404**; missing
stored PDF files return **410** with an explicit recovery message.
Snapshot images return JPEGs for this user's saved draft/current edition.
Cancel returns status and stops at the next safe job boundary, not by killing
an in-flight provider request. Deletion returns **204**; cancel active work
first or receive **409**. Collection records are never deleted by these routes.

## Identification

### POST /api/v1/identify

Upload vinyl record images for AI identification.

**Request:**
```bash
curl -X POST http://localhost:8000/api/v1/identify \
  -F "images=@record1.jpg" \
  -F "images=@record2.jpg"
```

**Response (202 Accepted):**
```json
{
  "record_id": "f47ac10b-58cc-4372-a567-0e02b2c3d479",
  "status": "pending"
}
```

**Parameters:**
- `images` (multipart) - 1-10 JPEG/PNG/WebP images, max 100MB total

---

### GET /api/v1/identify/{record_id}

Get identification results (poll until complete).

**Request:**
```bash
curl http://localhost:8000/api/v1/identify/f47ac10b-58cc-4372-a567-0e02b2c3d479
```

**Response (Complete):**
```json
{
  "record_id": "uuid",
  "status": "complete",
  "artist": "The Beatles",
  "title": "Abbey Road",
  "year": 1969,
  "label": "Apple Records",
  "catalog_number": "PCS 7088",
  "confidence": 0.92,
  "metadata": {
    "genres": ["Rock"],
    "estimated_value_eur": 45.50,
    "condition": "Near Mint"
  }
}
```

---

### POST /api/v1/identify/{record_id}/review

Confirm or modify identification results.

**Request:**
```json
{
  "action": "confirm",
  "modifications": {
    "condition": "Very Good Plus",
    "estimated_value_eur": 55.00
  }
}
```

**Actions:**
- `confirm` - Accept as-is
- `modify` - Accept with changes
- `reject` - Reject and request manual input

---

## Chat

### POST /api/v1/chat

Ask questions about vinyl records (general chat).

**Request:**
```json
{
  "message": "What are the most valuable Beatles albums?"
}
```

**Response:**
```json
{
  "message": "The most valuable Beatles albums...",
  "web_enhanced": true,
  "sources_used": 3
}
```

---

### POST /api/v1/identify/{record_id}/chat

Chat about a specific identified record.

**Request:**
```json
{
  "message": "What's this record worth?"
}
```

**Response:**
```json
{
  "message": "Based on current market data, Abbey Road in Near Mint condition is worth €45-60...",
  "web_enhanced": true
}
```

---

## Collection (Register)

### POST /api/register/add

Add record to user's collection.

**Request:**
```json
{
  "user_tag": "collector123",
  "vinyl_record": {
    "artist": "The Beatles",
    "title": "Abbey Road",
    "year": 1969,
    "label": "Apple Records",
    "condition": "Near Mint",
    "estimated_value_eur": 45.50
  }
}
```

**Response (201 Created):**
```json
{
  "id": "uuid",
  "user_tag": "collector123",
  "artist": "The Beatles",
  "confidence": 0.92,
  "created_at": "2026-01-29T10:15:30Z"
}
```

---

### GET /api/register

Retrieve user's collection.

**Request:**
```bash
curl "http://localhost:8000/api/register?user_tag=collector123"
```

**Response (200 OK):**
```json
[
  {
    "id": "uuid",
    "artist": "The Beatles",
    "title": "Abbey Road",
    "year": 1969,
    "estimated_value_eur": 45.50,
    "condition": "Near Mint"
  }
]
```

---

### POST /api/register/images/{record_id}

Add images to an existing record in the collection.

**Request:**
```bash
curl -X POST http://localhost:8000/api/register/images/123 \
  -F "images=@label1.jpg" \
  -F "images=@cover2.jpg"
```

**Parameters:**
- `record_id` (path) - Database ID of the record
- `images` (multipart) - 1-5 image files (PNG, JPG, GIF, WebP)
- Maximum 10MB per image

**Response (200 OK):**
```json
{
  "message": "Images uploaded successfully",
  "uploaded": ["label1.jpg", "cover2.jpg"],
  "failed": []
}
```

**Response (400 Bad Request):**
```json
{
  "detail": "No images provided"
}
```

**Response (413 Payload Too Large):**
```json
{
  "detail": "File too large: image.jpg (12.5 MB). Maximum size is 10 MB"
}
```

**Validation:**
- At least 1 image required
- Maximum 5 images per request
- Each file must be ≤ 10MB
- Supported formats: PNG, JPG, JPEG, GIF, WebP
- Files must not be empty

---

### PUT /api/register/{record_id}

Update record in collection.

**Request:**
```json
{
  "user_tag": "collector123",
  "condition": "Excellent",
  "estimated_value_eur": 55.00
}
```

---

### DELETE /api/register/{record_id}

Remove record from collection.

**Request:**
```bash
curl -X DELETE "http://localhost:8000/api/register/uuid?user_tag=collector123"
```

---

## Health

### GET /api/v1/health

Health check endpoint.

**Response:**
```json
{
  "status": "healthy",
  "version": "1.3.2",
  "database": "connected"
}
```

---

## Status Codes

| Code | Meaning |
|------|---------|
| 200 | Success |
| 201 | Created |
| 202 | Accepted (processing) |
| 400 | Bad Request |
| 404 | Not Found |
| 413 | Payload Too Large |
| 500 | Server Error |

---

See [Examples](examples.md) for complete workflows.
