# API Reference

Complete API documentation for Phonox backend.

## Base URL

```
http://localhost:8000
```

## Interactive Documentation

The API includes interactive documentation:

- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc

Try out endpoints directly in your browser!

## API Overview

Phonox provides RESTful APIs for:

| Endpoint | Purpose |
|----------|---------|
| `/api/v1/identify` | Upload and identify vinyl records |
| `/api/v1/identify/{id}` | Get identification results |
| `/api/v1/identify/{id}/chat` | Chat about a specific record |
| `/api/v1/chat` | General vinyl chat |
| `/api/register` | Manage personal collection |

## Response Format

All endpoints return JSON responses.

**Success Response (200-202):**
```json
{
  "status": "success",
  "data": { ... },
  "message": "Operation completed"
}
```

**Error Response (4xx-5xx):**
```json
{
  "detail": "Error description",
  "status_code": 400,
  "type": "validation_error"
}
```

## Authentication

Currently no authentication required for development.

For production, implement:
- API key authentication
- Rate limiting per user
- OAuth 2.0 for user-specific data

## Rate Limiting

Development: Unlimited  
Production (recommended):
- 10 req/min for `/identify`
- 30 req/min for `/chat`
- 50 req/min for `/register`

## Next Steps

- [Endpoints Reference](endpoints.md) - All endpoints with examples
- [Authentication](authentication.md) - Auth implementation
- [Code Examples](examples.md) - Real-world usage examples
