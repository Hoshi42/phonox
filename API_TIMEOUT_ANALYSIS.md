# API Timeout Configuration Analysis

## Summary
✅ **Most critical timeouts are configured**, but **frontend fetch calls are missing timeouts**. This could cause infinite hanging on slow networks.

---

## Backend Timeouts ✅

### 1. Web Scraping (Configurable)
- **File**: `backend/tools/web_tools.py`
- **Timeout**: `WEB_SCRAPING_TIMEOUT` (default: 10 seconds)
- **Status**: ✅ **CONFIGURABLE VIA ENV**
- **Location**: Line 15, Line 168
```python
WEB_SCRAPING_TIMEOUT = int(os.getenv("WEB_SCRAPING_TIMEOUT", "10"))
response = self.session.get(url, timeout=WEB_SCRAPING_TIMEOUT)
```
- **Coverage**: All URL requests from `WebScrapingTool.scrape_url()`

### 2. DuckDuckGo Search Fallback
- **File**: `backend/tools/web_tools.py`
- **Timeout**: 10 seconds (hardcoded)
- **Status**: ✅ **FIXED BUT NOT CONFIGURABLE**
- **Location**: Line 117
```python
resp = requests.get('https://duckduckgo.com/html/', params=params, headers=headers, timeout=10)
```
- **Issue**: Should use `WEB_SCRAPING_TIMEOUT` for consistency

### 3. Metadata API Calls (MusicBrainz, Discogs, Wikipedia)
- **File**: `backend/agent/metadata.py`
- **Timeout**: `API_TIMEOUT = 5` seconds (hardcoded)
- **Status**: ✅ **FIXED BUT NOT CONFIGURABLE**
- **Locations**: Lines 77, 103, 172
```python
API_TIMEOUT = 5  # seconds
response = requests.get(url, ..., timeout=API_TIMEOUT)
```
- **Issue**: Should be configurable via environment for different deployment scenarios

### 4. Claude API (Anthropic)
- **File**: `backend/api/routes.py`, `backend/agent/metadata_enhancer.py`
- **Timeout**: Default client timeout (not specified)
- **Status**: ❌ **NO EXPLICIT TIMEOUT CONFIGURED**
- **Anthropic Python SDK**: Uses default HTTP timeout (usually 30-60 seconds)
- **Recommendation**: Should add explicit timeout configuration

---

## Frontend Timeouts ❌ MISSING

### 1. File Upload (`identify()`)
- **File**: `frontend/src/api/client.ts`
- **Timeout**: ❌ **NONE**
- **Location**: Line 76
```typescript
const response = await fetch(url, {
  method: 'POST',
  body: formData,
  headers: getCacheHeaders()
  // NO TIMEOUT!
})
```
- **Impact**: Can hang indefinitely on slow networks
- **Risk**: User feels frozen, no feedback after 5+ minutes

### 2. Poll Results (`getResult()`)
- **File**: `frontend/src/api/client.ts`
- **Timeout**: ❌ **NONE**
- **Location**: Line 122
```typescript
const response = await fetch(url, {
  headers: getCacheHeaders()
  // NO TIMEOUT!
})
```
- **Impact**: Polling loop could hang
- **Risk**: Analysis appears stuck

### 3. Record Review (`review()`)
- **File**: `frontend/src/api/client.ts`
- **Timeout**: ❌ **NONE**
- **Location**: Line 144

### 4. Chat (`chat()`)
- **File**: `frontend/src/api/client.ts`
- **Timeout**: ❌ **NONE**
- **Location**: Line 172
```typescript
const response = await fetch(`${this.baseUrl}/api/v1/identify/${recordId}/chat`, {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({ message, metadata: stringMetadata })
  // NO TIMEOUT!
})
```
- **Impact**: Chat can hang indefinitely
- **Risk**: User loses feedback

### 5. Re-analyze (`reanalyze()`)
- **File**: `frontend/src/api/client.ts`
- **Timeout**: ❌ **NONE**
- **Location**: Line 225

### 6. General Chat (`POST /api/v1/chat`)
- **File**: `frontend/src/components/ChatPanel.tsx`
- **Timeout**: ❌ **NONE**
- **Location**: Line 156
```typescript
response = await fetch('/api/v1/chat', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({ message: userMessage.content })
  // NO TIMEOUT!
})
```

---

## Database Connection Timeouts ✅

### PostgreSQL Connection
- **File**: `backend/db_connection.py`
- **Configuration**: Connection pooling with timeouts
- **Status**: ✅ **PROPERLY CONFIGURED**
- **Details**:
  - Retry mechanism with exponential backoff
  - Configurable `DB_MAX_RETRIES`, `DB_RETRY_DELAY`, `DB_MAX_RETRY_DELAY`
  - Connection pool: `pool_pre_ping=True`, `pool_recycle=3600`

---

## FastAPI Server Timeouts

### HTTP Request/Response
- **Status**: ⚠️ **UVICORN DEFAULT** (usually 300 seconds)
- **Issue**: Long-running operations may timeout
- **Recommendation**: Add request timeout configuration

---

## Recommendations

### 🔴 CRITICAL (Frontend)
1. **Add fetch timeout to all frontend API calls** (5-30 seconds depending on operation)
2. **Implement timeout wrapper** to standardize timeout handling
3. **Add error UI** for timeout scenarios with retry option

### 🟡 IMPORTANT (Backend)
1. **Make DuckDuckGo timeout configurable** - use `WEB_SCRAPING_TIMEOUT`
2. **Make metadata API timeout configurable** - use environment variable `API_TIMEOUT`
3. **Add Anthropic Claude timeout configuration** - currently using default
4. **Add Uvicorn request timeout** - configure in FastAPI startup

### 🟢 GOOD (Already Done)
- ✅ Web scraping timeout: configurable
- ✅ Database connection retry logic
- ✅ Health check monitoring

---

## Timeout Recommendations by Operation

| Operation | Frontend | Backend | Recommendation |
|-----------|----------|---------|-----------------|
| File Upload | ❌ None | ✅ 5s (web scraping) | 60s timeout (files can be large) |
| Poll Status | ❌ None | 0s (fast DB) | 10s timeout |
| Chat Message | ❌ None | ✅ Configurable | 30s timeout (includes Claude) |
| Record Review | ❌ None | ✅ 5s (metadata) | 15s timeout |
| Re-analyze | ❌ None | ✅ 10s (scraping) | 120s timeout (long operation) |

---

## Testing

See `test_api_timeouts.py` for verification tests that ensure:
1. Frontend fetch calls have timeout logic
2. Backend API calls respect configured timeouts
3. Timeout errors are properly handled
