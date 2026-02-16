# Installation Guide

Detailed step-by-step installation instructions for Phonox.

## Quick Install (Recommended)

### Step 1: Clone the Repository

```bash
git clone https://github.com/your-username/phonox.git
cd phonox
```

### Step 2: Setup Environment with API Key

```bash
# Copy the environment template
cp .env.example .env

# Add your Anthropic API key
./phonox-cli configure --anthropic YOUR_ANTHROPIC_KEY

# Optional: Add Tavily for enhanced web search
./phonox-cli configure --tavily YOUR_TAVILY_KEY
```

**Get your API keys:**
- Anthropic: [console.anthropic.com](https://console.anthropic.com)
- Tavily (optional): [tavily.com](https://tavily.com)

### Step 3: Install and Start

```bash
# Make executable and run
chmod +x start-cli.sh
./start-cli.sh
```

**What `start-cli.sh` does:**
- ✅ Automatically builds all Docker images
- ✅ Starts database, backend, and frontend services
- ✅ Initializes the database with proper schema
- ✅ Creates necessary directories and permissions
- ✅ Runs health checks to verify everything works

**You're done!** Open http://localhost:5173 to start using Phonox.

---

## Alternative: Manual Docker Installation

If you prefer manual control or need to customize the installation:

```bash
# Clone
git clone https://github.com/your-username/phonox.git && cd phonox

# Setup
cp .env.example .env
# Edit .env with your API keys

# Run
docker compose up -d --build

# Open
# http://localhost:5173
```

---

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

**Web Search & Scraping** (optional - tune for network conditions):
```env
# Timeout for web scraping requests (seconds)
# Default: 10 (good balance between timeout risk and response time)
# Increase for slow internet, decrease for faster responses
WEB_SCRAPING_TIMEOUT=10

# Maximum URLs to scrape per search
# Default: 3 (balances content depth with response time)
# Increase for comprehensive searches, decrease for speed
WEB_SCRAPING_MAX_URLS=3
```

**Frontend Configuration** (optional):
```env
VITE_API_URL=http://localhost:8000
VITE_POLL_INTERVAL=2000
```

For all available options, see the `.env.example` file in the project root.

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
{"status":"healthy","version":"1.5.3","database":"connected"}
```

## Docker Compose Services

| Service | Image | Port | Purpose |
|---------|-------|------|---------|
| backend | python:3.12-slim | 8000 | FastAPI server |
| frontend | node:20-alpine | 5173 | React app |
| db | postgres:15 | 5432 | PostgreSQL database |

All services auto-restart on failure and have health checks enabled.
