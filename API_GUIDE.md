# Phonox API Documentation

Complete API reference for vinyl record identification and collection management.

## Base URL

```
http://localhost:8000
```

Interactive docs available at:
- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc

## Authentication

Currently no authentication required. Production deployment should add:
- Bearer token via Authorization header
- Rate limiting per user/IP

## Identification Endpoints

### POST /api/v1/identify

Upload vinyl record images for AI-powered identification.

**Request**

```http
POST /api/v1/identify HTTP/1.1
Content-Type: multipart/form-data

images: [File, File, ...]  (1-10 JPEG/PNG/WebP/GIF images)
```

**Response** (202 Accepted)

```json
{
  "record_id": "f47ac10b-58cc-4372-a567-0e02b2c3d479",
  "status": "pending"
}
```

**Status Codes**

- `202 Accepted`: Analysis started, poll for results
- `400 Bad Request`: Invalid images (format, size, count)
- `413 Payload Too Large`: Total size >100MB

**Example**

```bash
curl -X POST http://localhost:8000/api/v1/identify \
  -F "images=@record1.jpg" \
  -F "images=@record2.jpg"

# Response:
{
  "record_id": "f47ac10b-58cc-4372-a567-0e02b2c3d479",
  "status": "pending"
}
```

---

### GET /api/v1/identify/{record_id}

Retrieve identification results.

**Request**

```http
GET /api/v1/identify/f47ac10b-58cc-4372-a567-0e02b2c3d479 HTTP/1.1
```

**Response** (200 OK - Pending)

```json
{
  "record_id": "f47ac10b-58cc-4372-a567-0e02b2c3d479",
  "status": "pending"
}
```

**Response** (200 OK - Complete)

```json
{
  "record_id": "f47ac10b-58cc-4372-a567-0e02b2c3d479",
  "status": "complete",
  "artist": "The Beatles",
  "title": "Abbey Road",
  "year": 1969,
  "label": "Apple Records",
  "catalog_number": "PCS 7088",
  "barcode": "5099923379490",
  "genres": ["Rock", "Pop Rock"],
  "confidence": 0.92,
  "auto_commit": true,
  "needs_review": false,
  "metadata": {
    "artist": "The Beatles",
    "title": "Abbey Road",
    "year": 1969,
    "label": "Apple Records",
    "spotify_url": "https://open.spotify.com/album/...",
    "catalog_number": "PCS 7088",
    "barcode": "5099923379490",
    "genres": ["Rock", "Pop Rock"],
    "estimated_value_eur": 45.50,
    "estimated_value_usd": 49.99,
    "condition": "Near Mint",
    "image_urls": [
      "http://localhost:8000/uploads/image-uuid-1.jpg"
    ]
  },
  "intermediate_results": {
    "search_query": "The Beatles Abbey Road vinyl pressing",
    "search_results_count": 8,
    "claude_analysis": "Identified as original 1969 pressing...",
    "search_sources": [
      {
        "title": "Abbey Road - Discogs",
        "content": "Released 1969, Apple Records PCS 7088..."
      }
    ]
  },
  "created_at": "2026-01-28T10:15:30Z",
  "updated_at": "2026-01-28T10:15:38Z"
}
```

**Status Codes**

- `200 OK`: Record found (check `status` field)
- `404 Not Found`: Record ID doesn't exist
- `500 Internal Server Error`: Analysis failed

**Polling Recommendation**

```javascript
// Poll every 2 seconds, max 300 attempts (10 minutes)
const MAX_POLLS = 300;
let pollCount = 0;
const interval = setInterval(async () => {
  const res = await fetch(`/api/v1/identify/${recordId}`);
  const data = await res.json();
  
  if (data.status === 'complete' || data.status === 'error') {
    clearInterval(interval);
    // Handle result
  } else if (pollCount++ > MAX_POLLS) {
    clearInterval(interval);
    // Handle timeout
  }
}, 2000);
```

---

### POST /api/v1/identify/{record_id}/review

Confirm or modify identification results.

**Request**

```http
POST /api/v1/identify/f47ac10b-58cc-4372-a567-0e02b2c3d479/review HTTP/1.1
Content-Type: application/json

{
  "action": "confirm",
  "modifications": {
    "artist": "The Beatles",
    "title": "Abbey Road (Remaster)",
    "condition": "Very Good Plus",
    "estimated_value_eur": 55.00
  }
}
```

**Response** (200 OK)

```json
{
  "record_id": "f47ac10b-58cc-4372-a567-0e02b2c3d479",
  "status": "complete",
  "message": "Record confirmed and saved"
}
```

**Actions**

- `confirm`: Accept identification as-is
- `modify`: Accept with modifications
- `reject`: Reject and request manual input

---

### POST /api/v1/identify/{record_id}/reanalyze

Re-analyze existing record with new images.

**Request**

```http
POST /api/v1/identify/f47ac10b-58cc-4372-a567-0e02b2c3d479/reanalyze HTTP/1.1
Content-Type: multipart/form-data

images: [File, ...]  (New images to analyze)
```

**Response** (202 Accepted)

```json
{
  "record_id": "f47ac10b-58cc-4372-a567-0e02b2c3d479",
  "status": "pending",
  "message": "Re-analysis started with 1 new image + 1 existing image"
}
```

---

## Chat Endpoints

### POST /api/v1/chat

General vinyl chat without record context.

**Request**

```json
{
  "message": "What are the most valuable vinyl records?"
}
```

**Response** (200 OK)

```json
{
  "message": "The most valuable vinyl records include...",
  "web_enhanced": true,
  "sources_used": 3,
  "search_results": [
    {
      "title": "Top 10 Most Valuable Vinyl Records - Discogs",
      "url": "https://www.discogs.com/...",
      "content": "1. The Beatles - White Album... 2. Pink Floyd - Dark Side..."
    }
  ]
}
```

**Response Headers**

```
Content-Type: application/json
X-Web-Search: triggered  (only if web search was used)
X-Sources: 3
```

---

### POST /api/v1/identify/{record_id}/chat

Chat about specific vinyl record.

**Request**

```json
{
  "message": "What's this record worth?"
}
```

**Response** (200 OK)

```json
{
  "message": "Your Abbey Road (1969 original pressing) in Near Mint condition is worth approximately €45-60 based on current Discogs market prices...",
  "web_enhanced": true,
  "sources_used": 2,
  "search_results": [...]
}
```

**Special Commands**

Prefix message with `/web` to force web search:

```json
{
  "message": "/web Tell me about this pressing"
}
```

---

## Register Endpoints

### POST /api/register/add

Add vinyl record to user's collection.

**Request**

```json
{
  "user_tag": "collector123",
  "vinyl_record": {
    "artist": "The Beatles",
    "title": "Abbey Road",
    "year": 1969,
    "label": "Apple Records",
    "catalog_number": "PCS 7088",
    "barcode": "5099923379490",
    "genres": ["Rock"],
    "condition": "Near Mint",
    "estimated_value_eur": 45.50,
    "user_notes": "Original pressing with insert"
  }
}
```

**Response** (201 Created)

```json
{
  "id": "uuid-record-id",
  "user_tag": "collector123",
  "artist": "The Beatles",
  "title": "Abbey Road",
  "confidence": 0.92,
  "created_at": "2026-01-28T10:15:30Z",
  "updated_at": "2026-01-28T10:15:30Z"
}
```

---

### GET /api/register

Retrieve user's vinyl collection.

**Request**

```http
GET /api/register?user_tag=collector123 HTTP/1.1
```

**Query Parameters**

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| user_tag | string | Yes | User identifier |

**Response** (200 OK)

```json
[
  {
    "id": "uuid-1",
    "user_tag": "collector123",
    "artist": "The Beatles",
    "title": "Abbey Road",
    "year": 1969,
    "label": "Apple Records",
    "genres": ["Rock"],
    "confidence": 0.92,
    "estimated_value_eur": 45.50,
    "condition": "Near Mint",
    "created_at": "2026-01-28T10:15:30Z",
    "image_urls": ["http://..."]
  },
  {...}
]
```

---

### GET /api/register/{record_id}

Get specific record from register.

**Request**

```http
GET /api/register/uuid-record-id?user_tag=collector123 HTTP/1.1
```

**Response** (200 OK)

```json
{
  "id": "uuid-record-id",
  "user_tag": "collector123",
  "artist": "The Beatles",
  ...
}
```

---

### PUT /api/register/{record_id}

Update record in collection.

**Request**

```json
{
  "user_tag": "collector123",
  "condition": "Excellent",
  "estimated_value_eur": 55.00,
  "user_notes": "Updated condition after inspection"
}
```

**Response** (200 OK)

```json
{
  "id": "uuid-record-id",
  "message": "Record updated successfully",
  ...
}
```

---

### DELETE /api/register/{record_id}

Remove record from collection.

**Request**

```http
DELETE /api/register/uuid-record-id?user_tag=collector123 HTTP/1.1
```

**Response** (200 OK)

```json
{
  "message": "Record deleted successfully"
}
```

---

### GET /api/register/users

List all registered users.

**Request**

```http
GET /api/register/users HTTP/1.1
```

**Response** (200 OK)

```json
[
  "collector123",
  "vinylnerd",
  "recordhunter",
  "beatlesmania"
]
```

---

## Health & Metadata

### GET /api/v1/health

Health check endpoint.

**Response** (200 OK)

```json
{
  "status": "healthy",
  "version": "1.3.0",
  "database": "connected"
}
```

---

### GET /

Root endpoint with API info.

**Response** (200 OK)

```json
{
  "name": "Phonox",
  "version": "1.3.0",
  "description": "AI-powered vinyl record identification",
  "docs": "/docs",
  "health": "/api/v1/health"
}
```

---

## Error Handling

### Standard Error Response

```json
{
  "detail": "Error message describing what went wrong",
  "status_code": 400,
  "type": "validation_error"
}
```

### Common Status Codes

| Code | Meaning | Example |
|------|---------|---------|
| 200 | OK | Successfully retrieved data |
| 201 | Created | Record added to register |
| 202 | Accepted | Analysis started, poll for results |
| 400 | Bad Request | Invalid input format |
| 404 | Not Found | Record ID doesn't exist |
| 413 | Payload Too Large | File size exceeds limit |
| 500 | Server Error | Internal processing error |

---

## Rate Limiting

Currently unlimited. Production should implement:

```
- 10 requests/minute per IP for /identify
- 30 requests/minute per IP for /chat
- 50 requests/minute per IP for register operations
```

---

## Request/Response Examples

### Complete Flow Example

```bash
# 1. Upload images
curl -X POST http://localhost:8000/api/v1/identify \
  -F "images=@vinyl.jpg" \
  -o record_response.json

record_id=$(jq -r '.record_id' record_response.json)
echo "Record ID: $record_id"

# 2. Poll for results (every 2 seconds, max 30 attempts)
for i in {1..30}; do
  curl -X GET "http://localhost:8000/api/v1/identify/$record_id" \
    | jq '.status'
  
  if [ "$(curl -s http://localhost:8000/api/v1/identify/$record_id | jq -r '.status')" == "complete" ]; then
    break
  fi
  
  sleep 2
done

# 3. Get full results
curl -X GET "http://localhost:8000/api/v1/identify/$record_id" | jq .

# 4. Chat about the record
curl -X POST "http://localhost:8000/api/v1/identify/$record_id/chat" \
  -H "Content-Type: application/json" \
  -d '{"message": "What is this worth?"}'

# 5. Add to collection
curl -X POST "http://localhost:8000/api/register/add" \
  -H "Content-Type: application/json" \
  -d @- <<EOF
{
  "user_tag": "collector1",
  "vinyl_record": {...}
}
EOF

# 6. View collection
curl -X GET "http://localhost:8000/api/register?user_tag=collector1" | jq .
```

---

## Webhooks

Not currently supported. Future enhancement for async notifications of completed analyses.

---

## Changelog

See [CHANGELOG.md](CHANGELOG.md) for API version history and breaking changes.
