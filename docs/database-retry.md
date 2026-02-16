# Database Connection & Retry Configuration

The Phonox backend includes automatic database connection retry logic with exponential backoff and comprehensive alerting. This ensures reliable connections even when the database is temporarily unavailable.

## Quick Troubleshooting

### Issue: "could not translate host name 'db' to address"

This is a Docker network DNS resolution issue. The database container exists but the network can't resolve its hostname.

**Solution:**
```bash
# Restart backend container
docker-compose restart backend

# The retry logic will automatically handle the reconnection
```

### Issue: "Database system is starting up"

PostgreSQL is performing recovery after an unclean shutdown. This is normal.

**Solution:**
```bash
# Wait for automatic retry (usually completes within 30 seconds)
# Monitor logs:
docker-compose logs -f backend
```

## Configuration

All retry settings are configured via environment variables in `.env`:

### Environment Variables

```env
# Maximum number of connection attempts (default: 5)
DB_MAX_RETRIES=5

# Initial retry delay in seconds (default: 2)
DB_RETRY_DELAY=2

# Maximum retry delay in seconds (default: 30)
DB_MAX_RETRY_DELAY=30
```

### Exponential Backoff Schedule

Default configuration (DB_RETRY_DELAY=2, DB_MAX_RETRY_DELAY=30):

| Attempt | Delay | Total Time |
|---------|-------|-----------|
| 1 | 2s | 2s |
| 2 | 4s | 6s |
| 3 | 8s | 14s |
| 4 | 16s | 30s |
| 5 | 30s (capped) | 60s |

### Custom Configuration Examples

**For slow database startup:**
```env
DB_MAX_RETRIES=10
DB_RETRY_DELAY=3
DB_MAX_RETRY_DELAY=60
```

**For fast local development:**
```env
DB_MAX_RETRIES=3
DB_RETRY_DELAY=1
DB_MAX_RETRY_DELAY=10
```

## How It Works

### Startup Process

1. Backend container starts
2. Attempts to connect to database
3. If connection fails:
   - Logs the error with details
   - Waits exponentially longer between attempts
   - Retries up to `DB_MAX_RETRIES` times
4. If all retries fail:
   - Logs a critical alert with:
     - Masked database URL
     - Possible causes
     - Troubleshooting steps
   - Application fails to start (prevents silent failures)

### Connection Features

- **Connection Pooling**: Reuses database connections efficiently
- **Pre-ping**: Tests connections before using them
- **Pool Recycling**: Refreshes connections after 1 hour to prevent stale connections
- **URL Masking**: Passwords not exposed in logs for security

## Monitoring

### Check Database Health

```bash
curl http://localhost:8000/health
```

Response when connected:
```json
{
  "status": "healthy",
  "dependencies": {
    "database": "connected"
  }
}
```

Response when disconnected:
```json
{
  "status": "healthy",
  "dependencies": {
    "database": "disconnected"
  }
}
```

### View Connection Logs

```bash
# Watch backend logs in real-time
docker-compose logs -f backend

# Search for retry attempts
docker-compose logs backend | grep "DATABASE CONNECTION ATTEMPT"

# Search for critical alerts
docker-compose logs backend | grep "CRITICAL"
```

## Common Issues & Solutions

### "Port already in use" (5432)

The database port is in use by another process.

**Solution:**
```bash
# Free the port
lsof -i :5432 | grep LISTEN | awk '{print $2}' | xargs kill -9

# Or stop other containers
docker-compose down
docker-compose up -d
```

### "Database connection refused"

The database container isn't running or isn't healthy.

**Solution:**
```bash
# Check container status
docker-compose ps

# View database logs
docker-compose logs db

# Rebuild and restart
docker-compose down -v
docker-compose up -d --build
```

### "Incorrect credentials in DATABASE_URL"

The password or username in DATABASE_URL is wrong.

**Solution:**
```bash
# Verify .env file
cat .env | grep DATABASE_URL

# Should match POSTGRES_USER and POSTGRES_PASSWORD
cat .env | grep POSTGRES

# Update .env if needed
nano .env

# Restart backend
docker-compose restart backend
```

### "Database too many connections"

All connection slots are in use.

**Solution:**
```bash
# Restart services to reset connections
docker-compose restart backend frontend

# Or increase max connections (advanced)
docker-compose exec db psql -U phonox -d phonox -c "ALTER SYSTEM SET max_connections = 200; SELECT pg_reload_conf();"
```

## Advanced Topics

### Connection Pool Configuration

The connection pool is configured in `backend/db_connection.py`:

```python
# Test connections before using them
pool_pre_ping=True

# Recycle connections after 1 hour
pool_recycle=3600
```

### Custom Retry Logic

To modify retry behavior, edit `backend/db_connection.py`:

```python
def _get_retry_delay(self, attempt: int) -> int:
    """Calculate exponential backoff delay."""
    delay = min(
        self.initial_retry_delay * (2 ** (attempt - 1)), 
        self.max_retry_delay
    )
    return delay
```

### Debugging Connection Issues

Enable verbose logging:

```python
# In backend/main.py, set echo=True
engine = create_engine(
    DATABASE_URL,
    pool_pre_ping=True,
    pool_recycle=3600,
    echo=True  # Logs all SQL statements
)
```

## Health Check Integration

The database health is checked during:

1. **Application Startup**: Via `lifespan` context manager
2. **Runtime**: Via `/health` endpoint
3. **Dependency Injection**: Before handling API requests

Failed health checks return HTTP 503 (Service Unavailable).

## References

- [Installation Guide](getting-started/installation.md) - Environment configuration
- [Configuration Guide](getting-started/configuration.md) - All environment variables
