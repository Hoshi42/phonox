# Database Connection Retry and Alerting

## Overview

The Phonox backend now includes a robust database connection management system with automatic retry logic and comprehensive alerting. This ensures reliable connections even when the database is temporarily unavailable.

## Features

### Automatic Retry Logic
- **Exponential Backoff**: Retry delays increase exponentially between attempts
  - Attempt 1: 2 seconds
  - Attempt 2: 4 seconds
  - Attempt 3: 8 seconds
  - Attempt 4: 16 seconds
  - Attempt 5: 30 seconds (capped at max)

- **Configurable Parameters**:
  - `DB_MAX_RETRIES`: Maximum number of connection attempts (default: 5)
  - `DB_RETRY_DELAY`: Initial retry delay in seconds (default: 2)
  - `DB_MAX_RETRY_DELAY`: Maximum retry delay in seconds (default: 30)

### Alerting System
When connection failures occur, the system provides:

1. **Per-Attempt Logging**: Each failed attempt is logged with the specific error
2. **Critical Alert**: When all retries are exhausted, a critical alert is logged with:
   - Masked database connection URL
   - Possible causes
   - Recommended troubleshooting steps
   - Instructions for recovery

3. **Graceful Degradation**: The API returns HTTP 503 (Service Unavailable) if the database isn't ready

## Configuration

### Environment Variables

Add these to your `.env` file or `docker-compose.yml`:

```bash
# Database connection retry settings
DB_MAX_RETRIES=5              # Number of retry attempts
DB_RETRY_DELAY=2              # Initial delay between retries (seconds)
DB_MAX_RETRY_DELAY=30         # Maximum delay between retries (seconds)
```

### Docker Compose Example

```yaml
environment:
  DATABASE_URL: postgresql://phonox:phonox123@db:5432/phonox
  DB_MAX_RETRIES: 5
  DB_RETRY_DELAY: 2
  DB_MAX_RETRY_DELAY: 30
```

## Logs

### Successful Connection
```
INFO:backend.db_connection:Attempting database connection (attempt 1/5)...
INFO:backend.db_connection:✅ Database connection established successfully!
INFO:backend.main:✅ Database tables created/verified
INFO:     Application startup complete.
```

### Connection Failure with Retry
```
INFO:backend.db_connection:Attempting database connection (attempt 1/5)...
ERROR:backend.db_connection:DATABASE CONNECTION ATTEMPT 1/5 FAILED: could not translate host name "db" to address: Name or service not known
WARNING:backend.db_connection:Retrying in 2 seconds... (4 retries remaining)
```

### Critical Alert (All Retries Exhausted)
```
CRITICAL:backend.db_connection:
======================================================================
🚨 CRITICAL: DATABASE CONNECTION FAILED AFTER 5 RETRIES
======================================================================
DATABASE URL: postgresql://phonox:***@db:5432/phonox
The application cannot connect to the database.
Possible causes:
  - PostgreSQL service is not running
  - Network connectivity issues (Docker network DNS resolution)
  - Incorrect credentials in DATABASE_URL
  - Database server is unreachable

Actions to take:
  1. Check if PostgreSQL container is running: docker-compose ps
  2. Try restarting containers: docker-compose restart
  3. Check container logs: docker-compose logs db
  4. Verify DATABASE_URL environment variable
======================================================================
```

## Troubleshooting

### Common Issues

#### "could not translate host name 'db' to address"
- **Cause**: Docker network DNS issue
- **Solution**: 
  ```bash
  docker-compose restart backend
  ```

#### Connection timeout
- **Cause**: Database taking longer to start
- **Solution**: Increase `DB_MAX_RETRIES` or `DB_RETRY_DELAY`
  ```yaml
  DB_MAX_RETRIES: 10
  DB_RETRY_DELAY: 5
  ```

#### "Database system is starting up"
- **Cause**: PostgreSQL is performing recovery
- **Solution**: Wait for retry logic to succeed (normal operation)

### Monitoring

Monitor connection health:
```bash
curl http://localhost:8000/health
```

Response when connected:
```json
{
  "status": "healthy",
  "version": "1.0.0",
  "timestamp": "2026-02-01T11:42:21.480479",
  "dependencies": {
    "database": "connected",
    "claude_api": "available",
    "tavily_api": "available"
  }
}
```

Response when database unavailable:
```json
{
  "status": "healthy",
  "version": "1.0.0",
  "timestamp": "2026-02-01T11:42:21.480479",
  "dependencies": {
    "database": "disconnected",
    "claude_api": "available",
    "tavily_api": "available"
  }
}
```

## Implementation Details

### DatabaseConnectionManager Class

Located in `backend/db_connection.py`

**Key Methods**:
- `connect()`: Establishes connection with retry logic
- `get_engine()`: Returns SQLAlchemy engine
- `get_session_maker()`: Returns session maker
- `is_connected()`: Checks current connection status
- `close()`: Gracefully closes connection

**Features**:
- Connection pooling with `pool_pre_ping=True` (tests connections before use)
- Pool recycling every 1 hour
- Masked URL logging (passwords not exposed)
- Comprehensive error handling

## Integration

The retry logic is integrated at application startup in `backend/main.py`:

```python
@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifespan context manager for app startup/shutdown."""
    global engine, SessionLocal
    
    # Startup
    logger.info("Starting Phonox API server")
    
    try:
        # Connect to database with retries
        db_manager.connect()
        engine = db_manager.get_engine()
        SessionLocal = db_manager.get_session_maker()
        # ... rest of initialization
    except Exception as e:
        logger.critical(f"❌ Failed to initialize database: {e}")
        raise
```

## Future Enhancements

Potential improvements:
- Circuit breaker pattern for connection pool failures
- Metrics collection (retry counts, success rates)
- Webhook/email notifications for critical failures
- Automatic container restart on persistent failures
- Health check probes with custom thresholds
