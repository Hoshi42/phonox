# API Endpoints

Complete reference for all Phonox API endpoints.

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
