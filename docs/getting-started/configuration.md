# Configuration Guide

Complete reference for configuring Phonox via environment variables.

## Overview

Phonox is configured using environment variables stored in a `.env` file. Copy `.env.example` to `.env` and update with your values.

```bash
cp .env.example .env
nano .env
```

---

## Essential Configuration

### Anthropic API (Required)

**`ANTHROPIC_API_KEY`**
- **Required**: Yes
- **Description**: Your Anthropic API key for Claude AI vision and chat
- **Get it from**: [console.anthropic.com/account/keys](https://console.anthropic.com/account/keys)
- **Example**: `ANTHROPIC_API_KEY=sk-ant-v1-xxxxxxxx...`

### Tavily API (Optional)

**`TAVILY_API_KEY`**
- **Required**: No
- **Description**: Web search API for enhanced metadata enrichment
- **Default**: Uses DuckDuckGo fallback if not provided
- **Get it from**: [tavily.com](https://tavily.com)
- **Example**: `TAVILY_API_KEY=tvly-xxxxxxxx...`

### Discogs API (Optional)

**`DISCOGS_TOKEN`**
- **Required**: No
- **Description**: Personal access token for authenticated Discogs requests — raises the rate limit from 25 to 60 requests per minute and improves metadata lookup reliability
- **Get it from**: [discogs.com/settings/developers](https://www.discogs.com/settings/developers) → *Generate new token*
- **Example**: `DISCOGS_TOKEN=abcXYZ123...`

---

## Database Configuration

### Connection (Pre-configured for Docker)

**`DATABASE_URL`**
- **Default**: `postgresql://phonox:your_secure_password_here@db:5432/phonox`
- **Format**: `postgresql://username:password@host:port/database`
- **For local development**: `postgresql://phonox:password@localhost:5432/phonox`
- **For production**: Use a managed PostgreSQL service

### Connection Retry Logic

Handles slow database startup or temporary connection issues.

**`DB_MAX_RETRIES`**
- **Default**: `5`
- **Description**: Maximum connection attempts before failing
- **Increase when**: Database takes longer than expected to start
- **Example**: `DB_MAX_RETRIES=10` (for very slow databases)

**`DB_RETRY_DELAY`**
- **Default**: `2`
- **Description**: Initial delay between retry attempts (seconds)
- **Behavior**: Uses exponential backoff (2 → 4 → 8 → 16 → 30)
- **Example**: `DB_RETRY_DELAY=5` (slower databases)

**`DB_MAX_RETRY_DELAY`**
- **Default**: `30`
- **Description**: Maximum delay between retry attempts (seconds)
- **Example**: `DB_MAX_RETRY_DELAY=60` (very slow startup environments)

---

## Web Search & Scraping

Configure how Phonox searches the web and scrapes content for metadata enrichment.

### Timeout

**`WEB_SCRAPING_TIMEOUT`**
- **Default**: `10` (seconds)
- **Description**: Timeout for individual web scraping requests
- **Tune it**:
  - **Increase** (15-20s): Slow internet, want more complete content
  - **Decrease** (5s): Fast responses needed, ok with less content
  - **Production**: 8-10s is typical
- **Example**: `WEB_SCRAPING_TIMEOUT=15`

### URL Limits

**`WEB_SCRAPING_MAX_URLS`**
- **Default**: `3` (URLs)
- **Description**: Maximum number of URLs to scrape per web search
- **Tune it**:
  - **Increase** (5-7): Comprehensive searches, more context (slower)
  - **Decrease** (1-2): Fast responses, minimal content
  - **Production**: 3-5 is typical
- **Example**: `WEB_SCRAPING_MAX_URLS=5`

### Configuration Examples

**Fast Responses (Limited Content)**
```env
WEB_SCRAPING_TIMEOUT=5
WEB_SCRAPING_MAX_URLS=1
```

**Balanced (Default)**
```env
WEB_SCRAPING_TIMEOUT=10
WEB_SCRAPING_MAX_URLS=3
```

**Comprehensive (Slow)**
```env
WEB_SCRAPING_TIMEOUT=20
WEB_SCRAPING_MAX_URLS=5
```

---

## Frontend Configuration

### API URL

**`VITE_API_URL`**
- **Default**: Auto-detected (uses same host as frontend)
- **Description**: Backend API URL for frontend requests
- **Examples**:
  - Local development: `http://localhost:8000`
  - Docker compose: `http://backend:8000`
  - Production: `https://api.example.com`
- **Leave empty** for auto-detection in most cases

### Polling

**`VITE_POLL_INTERVAL`**
- **Default**: `2000` (milliseconds)
- **Description**: How often frontend polls for job status
- **Tune it**:
  - **Decrease** (1000): More responsive, higher server load
  - **Increase** (5000): Less responsive, lower server load
- **Example**: `VITE_POLL_INTERVAL=3000`

### Environment

**`VITE_ENV`**
- **Default**: `development`
- **Options**: `development`, `staging`, `production`
- **Description**: Frontend environment profile
- **Example**: `VITE_ENV=production`

---

## Vision & Chat Models

The recommendations below match `.env.example`. They must be set explicitly in
the **backend process environment**; they do not change the older code-level
fallbacks automatically.

!!! warning "Docker Compose model settings"
    The current Compose file does not forward these four model variables.
    A project `.env` supplies values for Compose interpolation, but does not
    automatically export every value into the container. Add these entries
    under `services.backend.environment` before recreating the backend:

    ```yaml
    ANTHROPIC_VISION_MODEL: ${ANTHROPIC_VISION_MODEL:-claude-sonnet-5-5}
    ANTHROPIC_CHAT_MODEL: ${ANTHROPIC_CHAT_MODEL:-claude-haiku-5-5}
    ANTHROPIC_AGGREGATION_MODEL: ${ANTHROPIC_AGGREGATION_MODEL:-claude-sonnet-5-5}
    ANTHROPIC_ENHANCEMENT_MODEL: ${ANTHROPIC_ENHANCEMENT_MODEL:-claude-opus-5-5}
    ```

    Apply with `docker compose up -d --force-recreate backend`; a plain restart
    does not update the container's environment. This documentation update
    does not change the Compose file or certify every analysis path with 5.5.

### Vision Model (Image Analysis)

**`ANTHROPIC_VISION_MODEL`**
- **Recommended**: `claude-sonnet-5-5`
- **Options**:
  - `claude-sonnet-5-5` (balanced vision recommendation)
  - `claude-haiku-5-5` (lower-cost option; evaluate extraction quality first)
- **Description**: Model used for vinyl record image analysis
- **Example**: `ANTHROPIC_VISION_MODEL=claude-sonnet-5-5`

### Chat Model (Conversations)

**`ANTHROPIC_CHAT_MODEL`**
- **Recommended**: `claude-haiku-5-5`
- **Options**:
  - `claude-haiku-5-5` (fast, lower-cost option)
  - `claude-sonnet-5-5` (alternative for more demanding conversations)
- **Description**: Model used for chat responses
- **Example**: `ANTHROPIC_CHAT_MODEL=claude-haiku-5-5`

### Aggregation and Enhancement Models

| Variable | Recommended model | Purpose |
|---|---|---|
| `ANTHROPIC_AGGREGATION_MODEL` | `claude-sonnet-5-5` | Merge results from multiple images |
| `ANTHROPIC_ENHANCEMENT_MODEL` | `claude-opus-5-5` | Resolve metadata conflicts during enhancement |

For lower enhancement costs, evaluate `claude-sonnet-5-5` as an alternative to
Opus. See [model pricing and estimation](../architecture/cost-model.md).

---

## Backend Configuration

### Python Optimization

**`PYTHONDONTWRITEBYTECODE`**
- **Default**: `1`
- **Description**: Prevent Python from writing `.pyc` files
- **Keep as**: `1` (reduces disk writes in containers)

**`PYTHONUNBUFFERED`**
- **Default**: `1`
- **Description**: Unbuffered Python output (important for logs)
- **Keep as**: `1` (ensures logs appear in real-time)

---

## Docker Environment

When running with Docker Compose, variables are loaded from `.env` automatically.

```bash
# Start with current .env
docker-compose up -d

# Override specific variable
ANTHROPIC_API_KEY=new-key docker-compose up -d

# View environment in container
docker-compose exec backend env | grep ANTHROPIC
```

---

## Troubleshooting Configuration

### "ANTHROPIC_API_KEY not set"
- Copy `.env.example` to `.env`
- Add your actual API key to `.env`
- Restart containers: `docker-compose restart`

### "Web search timing out"
- Increase `WEB_SCRAPING_TIMEOUT` (current: 10s)
- Check internet connection
- Try different Tavily API key

### "Database connection failing"
- Check `DATABASE_URL` is correct
- Verify database is running: `docker-compose ps`
- Increase `DB_MAX_RETRIES` or `DB_RETRY_DELAY`

### "Slow identification"
- Decrease `WEB_SCRAPING_MAX_URLS` to 1-2
- Decrease `WEB_SCRAPING_TIMEOUT` to 5s
- Use the recommended lower-cost chat model: `claude-haiku-5-5`

---

## Complete Configuration Example

```env
# API Keys
ANTHROPIC_API_KEY=sk-ant-v1-xxxxx
TAVILY_API_KEY=tvly-xxxxx

# Database
DATABASE_URL=postgresql://phonox:secure_password@db:5432/phonox
DB_MAX_RETRIES=5
DB_RETRY_DELAY=2
DB_MAX_RETRY_DELAY=30

# Web Search - Balanced for production
WEB_SCRAPING_TIMEOUT=10
WEB_SCRAPING_MAX_URLS=3

# Frontend
VITE_API_URL=http://backend:8000
VITE_POLL_INTERVAL=2000
VITE_ENV=production

# AI Models
ANTHROPIC_VISION_MODEL=claude-sonnet-5-5
ANTHROPIC_CHAT_MODEL=claude-haiku-5-5
ANTHROPIC_AGGREGATION_MODEL=claude-sonnet-5-5
ANTHROPIC_ENHANCEMENT_MODEL=claude-opus-5-5

# Backend
PYTHONDONTWRITEBYTECODE=1
PYTHONUNBUFFERED=1
```

---

## Further Help

- See `.env.example` file in the project root for all available options
- Check [Installation Guide](installation.md) for setup help
- See [Database Troubleshooting](../database-retry.md) for connection issues
