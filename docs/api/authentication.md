# Authentication

How to authenticate API requests in Phonox.

## Current Status

**Development**: No authentication required  
**Production**: Implement one of the methods below

## Authentication Methods

### Development (None)

All endpoints are open. Add authentication before production deployment.

### Option 1: API Key Authentication (Recommended)

Simple and effective for services and bots.

**Implementation:**
```python
# backend/api/middleware.py
def verify_api_key(request):
    api_key = request.headers.get("X-API-Key")
    if not api_key or api_key != os.getenv("PHONOX_API_KEY"):
        raise HTTPException(status_code=401, detail="Invalid API key")
```

**Usage:**
```bash
curl -H "X-API-Key: your-api-key-here" \
  http://localhost:8000/api/v1/identify
```

### Option 2: Bearer Token (JWT)

Industry standard for web and mobile apps.

**Implementation:**
```python
from fastapi import Depends, HTTPException
from fastapi.security import HTTPBearer

security = HTTPBearer()

async def verify_token(credentials: HTTPAuthCredentials = Depends(security)):
    token = credentials.credentials
    # Verify JWT token
    payload = jwt.decode(token, SECRET_KEY, algorithms=["HS256"])
    return payload
```

**Usage:**
```bash
curl -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  http://localhost:8000/api/v1/identify
```

### Option 3: OAuth 2.0

Best for user-facing applications with GitHub/Google login.

**Providers:**
- GitHub OAuth
- Google OAuth
- Custom OAuth server

**Implementation:**
```python
from fastapi_oauth2 import OAuth2

oauth2_scheme = OAuth2(...)

async def get_current_user(token: str = Depends(oauth2_scheme)):
    user = decode_token(token)
    return user
```

## Rate Limiting

Add rate limiting based on authentication:

```python
from slowapi import Limiter
from slowapi.util import get_remote_address

limiter = Limiter(key_func=get_remote_address)

@router.post("/api/v1/identify")
@limiter.limit("10/minute")
async def identify(request: Request, ...):
    ...
```

## Production Checklist

- ✅ Choose authentication method
- ✅ Generate secure keys/secrets
- ✅ Implement in FastAPI
- ✅ Update frontend to send tokens
- ✅ Add rate limiting
- ✅ Enable HTTPS
- ✅ Use secure cookies
- ✅ Implement refresh tokens
- ✅ Add audit logging

## Next Steps

For now, start with API Key authentication. See [Development Guide](../development/backend.md) for implementation details.
