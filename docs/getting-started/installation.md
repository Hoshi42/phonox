# Installation Guide

Detailed step-by-step installation instructions for Phonox.

## Quick Install (5 minutes)

```bash
# Clone
git clone https://github.com/your-username/phonox.git && cd phonox

# Setup
cp .env.example .env
# Edit .env with your API keys

# Run
docker-compose up -d --build

# Open
# http://localhost:5173
```

## Detailed Installation

See [Getting Started Overview](overview.md) for comprehensive setup instructions.

## Environment Configuration

All configuration is done via `.env` file. Copy `.env.example` to `.env` and update with your values.

### Minimum Required

```env
# Anthropic API (for AI vision & chat)
ANTHROPIC_API_KEY=sk-ant-...

# Tavily API (for web search) - optional
TAVILY_API_KEY=tvly-...

# Database (default works for Docker)
DATABASE_URL=postgresql://phonox:phonox123@db:5432/phonox
```

### Advanced Configuration

**Database Connection Retry** (optional - handles slow database startup):
```env
DB_MAX_RETRIES=5
DB_RETRY_DELAY=2
DB_MAX_RETRY_DELAY=30
```

**Frontend Configuration** (optional):
```env
VITE_API_URL=http://localhost:8000
VITE_POLL_INTERVAL=2000
```

For all available options, see [`.env.example`](../../.env.example)

## Verification

```bash
# Check services running
docker-compose ps

# View logs
docker-compose logs -f

# Test API
curl http://localhost:8000/api/v1/health
```

Expected response:
```json
{"status":"healthy","version":"1.3.2","database":"connected"}
```

## Docker Compose Services

| Service | Image | Port | Purpose |
|---------|-------|------|---------|
| backend | python:3.12-slim | 8000 | FastAPI server |
| frontend | node:20-alpine | 5173 | React app |
| db | postgres:15 | 5432 | PostgreSQL database |

All services auto-restart on failure and have health checks enabled.
