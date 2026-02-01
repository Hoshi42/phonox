```
 ██████╗ ██╗  ██╗ ██████╗ ███╗   ██╗ ██████╗ ██╗  ██╗
 ██╔══██╗██║  ██║██╔═══██╗████╗  ██║██╔═══██╗╚██╗██╔╝
 ██████╔╝███████║██║   ██║██╔██╗ ██║██║   ██║ ╚███╔╝ 
 ██╔═══╝ ██╔══██║██║   ██║██║╚██╗██║██║   ██║ ██╔██╗ 
 ██║     ██║  ██║╚██████╔╝██║ ╚████║╚██████╔╝██╔╝ ██╗
 ╚═╝     ╚═╝  ╚═╝ ╚═════╝ ╚═╝  ╚═══╝ ╚═════╝ ╚═╝  ╚═╝
```

**AI-powered Vinyl Collection Agent** – Cataloguing, Valuation, and Documentation

---

## What is Phonox?

Phonox is an intelligent assistant for vinyl record collectors. It helps you:
- **📸 Identify records** by snapping photos or uploading images
- **💰 Get valuations** using multiple data sources (Discogs, MusicBrainz)
- **🎵 Find Spotify links** for listening to your collection
- **📝 Organize your collection** with metadata, ratings, and notes
- **💬 Chat about records** with an AI agent that remembers your collection

Perfect for collectors managing large vinyl libraries or insuring valuable collections.

---

## Prerequisites

Before you start, make sure you have:

1. **Docker & Docker Compose** installed
   - [Windows/Mac](https://www.docker.com/products/docker-desktop)
   - [Linux](https://docs.docker.com/engine/install/)
   - Verify: Run `docker --version` and `docker compose version`

2. **Git** (to clone the repository)
   - [Install Git](https://git-scm.com/downloads)

3. **API Keys** (optional but recommended)
   - [Anthropic API Key](https://console.anthropic.com) (for Claude AI)
   - [Tavily API Key](https://tavily.com) (for web search, optional – DuckDuckGo fallback is free)

---

## Quick Start (Docker)

### 1. Clone and Install

```bash
# Clone the repository
git clone https://github.com/yourusername/phonox.git
cd phonox

# Install and start (builds Docker images + starts services)
./phonox-cli install --up
```

If you don't have the CLI, use Docker directly:
```bash
docker compose up -d
```

### 2. Configure API Keys (Optional)

```bash
# Set your API keys
./phonox-cli configure --anthropic YOUR_ANTHROPIC_KEY

# Optional: Add Tavily for enhanced search
./phonox-cli configure --tavily YOUR_TAVILY_KEY

# Optional: Configure Anthropic models (for advanced users)
./phonox-cli configure --vision-model claude-sonnet-4-5-20250929 --chat-model claude-haiku-4-5-20251001
```

Or edit `.env` file directly. Use `.env.example` as a reference:

```bash
# Copy the template
cp .env.example .env

# Edit with your values
nano .env
```

**Key Environment Variables:**

| Variable | Required | Description |
|----------|----------|-------------|
| `ANTHROPIC_API_KEY` | ✅ Yes | Claude AI API key from [console.anthropic.com](https://console.anthropic.com) |
| `TAVILY_API_KEY` | ⚠️ Optional | Web search API key from [tavily.com](https://tavily.com) |
| `DATABASE_URL` | ✅ Pre-configured | PostgreSQL connection (auto-configured for Docker) |
| `VITE_API_URL` | ⚠️ Optional | Backend API URL (auto-detected if not set) |
| `DB_MAX_RETRIES` | ⚠️ Optional | Database connection retry attempts (default: 5) |
| `DB_RETRY_DELAY` | ⚠️ Optional | Initial retry delay in seconds (default: 2) |

For all configuration options, see [`.env.example`](./.env.example)

### 3. Access the Application

Open your browser and visit:
- **Frontend** (UI): http://localhost:5173
- **API Docs**: http://localhost:8000/docs
- **Backend Health**: http://localhost:8000/health

You should see Phonox ready to use!

---

## How to Use Phonox

### Identify a Vinyl Record

1. Click **"Upload Image"** on the home page
2. Take a photo or upload an image of:
   - The album cover (front or back)
   - The barcode (if visible)
   - The vinyl itself (for condition assessment)
3. Phonox AI will:
   - Scan for the barcode
   - Search Discogs and MusicBrainz
   - Extract album metadata automatically
4. Review the results and save to your collection

### Manage Your Collection

1. Visit **"Register"** to see all your vinyl records
2. **Edit** any record to:
   - Add notes or condition notes
   - Add Spotify link
   - Update valuation
   - Rate the record
3. **Delete** records from your collection
4. **Export** your collection (future feature)

### Chat with the Agent

1. Open the **Chat** panel on the right
2. Ask questions about your collection:
   - "What's my rarest record?"
   - "Show me all records from the 80s"
   - "What's the total value of my collection?"
3. The agent remembers context from your collection

---

## How to Stop, Start, and Manage Services

### Start Services
```bash
./phonox-cli start
# or
docker compose up -d
```

### Stop Services
```bash
./phonox-cli stop
# or
docker compose down
```

### View Logs
```bash
docker compose logs -f backend
docker compose logs -f frontend
```

### Check Service Status
```bash
./phonox-cli status
# or
curl http://localhost:8000/health
```

---

## Phonox CLI Commands

Full CLI Reference:

```bash
# Install (build Docker images)
./phonox-cli install

# Install + start services
./phonox-cli install --up

# Configure API keys and models
./phonox-cli configure --anthropic YOUR_KEY --tavily YOUR_KEY

# Configure Anthropic models (for advanced users)
./phonox-cli configure --vision-model claude-sonnet-4-5-20250929
./phonox-cli configure --chat-model claude-haiku-4-5-20251001

# Start services
./phonox-cli start

# Stop services
./phonox-cli stop

# Backup your data
./phonox-cli backup

# Restore from backup (use timestamp from backup folder)
./phonox-cli restore 20260128_143000
```

### Interactive Menu

Run without arguments to launch interactive menu:
```bash
./phonox-cli
# Shows menu with all options above
```

---

## Troubleshooting & Maintenance

### Common Issues

#### ❌ "Port already in use" (8000 or 5173)
```bash
# Kill process using port 8000
lsof -i :8000 | grep LISTEN | awk '{print $2}' | xargs kill -9

# Or restart Docker
docker compose down
docker compose up -d
```

#### ❌ "Database connection refused"
```bash
# Reset database
docker compose down -v
docker compose up -d
```

#### ❌ Images not uploading
```bash
# Check upload folder permissions
ls -la data/uploads/

# Restart services
docker compose restart backend frontend
```

#### ❌ API keys not working
```bash
# Verify .env file
cat .env

# Restart backend to reload keys
docker compose restart backend
```

### Regular Maintenance

#### Backup Your Data (Weekly)
```bash
./phonox-cli backup
# Backups stored in: ./backups/
```

#### View Backup History
```bash
ls -lh backups/
```

#### Restore from a Backup
```bash
./phonox-cli restore 20260128_143000
```

#### Check Database Size
```bash
docker compose exec db psql -U phonox -d phonox -c "
  SELECT 
    schemaname,
    sum(pg_total_relation_size(schemaname||'.'||tablename)) AS size
  FROM pg_tables
  GROUP BY schemaname
  ORDER BY size DESC;"
```

#### View Vinyl Records in Database
```bash
docker compose exec db psql -U phonox -d phonox -c "
  SELECT id, title, artist, release_date, confidence, created_at
  FROM vinyl_records
  ORDER BY created_at DESC
  LIMIT 10;"
```

---

## Testing

### Run All Tests
```bash
docker compose exec backend pytest tests/ -v
```

### Run Specific Test Categories
```bash
# Unit tests
docker compose exec backend pytest tests/unit -v

# Integration tests
docker compose exec backend pytest tests/integration -v

# With coverage report
docker compose exec backend pytest tests/ --cov=backend --cov-report=html
```

### View Test Results
```bash
# Open coverage report
open htmlcov/index.html  # macOS
xdg-open htmlcov/index.html  # Linux
start htmlcov/index.html  # Windows
```

### 📖 Getting Started
- **[What is Phonox?](#what-is-phonox)** – Overview and features
- **[How to Use](#how-to-use-phonox)** – Step-by-step user guide
- **[Troubleshooting](#troubleshooting--maintenance)** – Common issues and fixes

### 👨‍💻 For Developers
- **[Tech Stack Guide](docs/tech-stack.md)** – Architecture and technologies
- **[Requirements Spec](docs/requirements_en.md)** – Complete feature list
- **[Testing Guide](TESTING_GUIDE.md)** – How to write and run tests

### 🏗️ For Teams & Contributors
1. **[Implementation Plan](.github/agents/implementation-plan.md)** – Project roadmap and progress
2. **[Contributing Guide](CONTRIBUTING.md)** – How to contribute code
3. **[Agent Collaboration Instructions](.github/agents/instructions.md)** – Team workflow
4. **[Deployment Guide](.github/agents/deployment.md)** – Production setup

---

## Project Structure

```
phonox/
├── README.md (this file)
├── requirements.txt (Python dependencies)
├── docker-compose.yml (Local development)
├── Dockerfile.backend (FastAPI image)
├── Dockerfile.frontend (Vite React image)
│
├── docs/
│   ├── tech-stack.md
│   ├── requirements_en.md
│   └── .github/agents/
│       ├── agent.md (Agent architecture)
│       ├── architect.md (Architect role)
│       ├── tools.md (Tool engineer role)
│       ├── frontend.md (Frontend role)
│       ├── deployment.md (Docker & CI/CD)
│       ├── testing.md (Testing strategy)
│       ├── implementation-plan.md (Roadmap)
│       └── instructions.md (Collaboration guide)
│
├── backend/
│   ├── main.py (FastAPI entry point)
   ├── database.py (SQLAlchemy ORM)
   ├── agent/
   │   ├── state.py (State models)
   │   ├── graph.py (LangGraph workflow)
   │   ├── vision.py (Vision extraction)
   │   ├── websearch.py (Web search integration)
   │   ├── metadata.py (Metadata lookup)
   │   └── barcode_utils.py (Barcode extraction)
   ├── api/
   │   ├── routes.py (Identification endpoints)
   │   ├── register.py (Register endpoints)
   │   └── models.py (Pydantic models)
   ├── tools/
   │   └── web_tools.py (Web search tools)
   └── tests/ (unit, integration, api tests)
│
└── frontend/
    ├── src/
    │   ├── components/
    │   │   ├── ImageUpload.tsx
    │   │   ├── ResultsView.tsx
    │   │   ├── ReviewForm.tsx
    │   │   ├── ChatPanel.tsx
    │   │   ├── VinylCard.tsx
    │   │   ├── VinylRegister.tsx
    │   │   └── AnalysisModal.tsx
    │   └── App.tsx
    └── package.json
```





---

## Architecture Overview (Technical Details)

### How It Works

```
┌─────────────────────────────────────────────────────────┐
│ Frontend (React)                                        │
│ - Upload images                                         │
│ - View collection                                       │
│ - Chat with AI agent                                    │
└────────────────────┬────────────────────────────────────┘
                     │ HTTP
                     ▼
┌─────────────────────────────────────────────────────────┐
│ Backend (FastAPI)                                       │
│ - AI Agent (LangGraph)                                  │
│ - Image Recognition                                     │
│ - Metadata Lookup                                       │
└────────────────────┬────────────────────────────────────┘
                     │
        ┌────────────┼────────────┐
        ▼            ▼            ▼
    Database    Discogs API   MusicBrainz
   (PostgreSQL)  (Metadata)    (Metadata)
```

### Key Components

- **Agent** – AI decision-maker using LangGraph orchestration
- **Tools** – Plugins for Discogs, MusicBrainz, image extraction, web search
- **Database** – PostgreSQL stores your vinyl collection
- **API** – FastAPI provides endpoints for the frontend
- **Frontend** – React PWA for mobile and desktop browsers

---

## Tech Stack

- **Backend**: Python 3.12, FastAPI, LangGraph, Pydantic v2, SQLAlchemy
- **Frontend**: React (Vite), PWA, TypeScript
- **Database**: PostgreSQL 16
- **Cache/Queue**: Redis 7
- **API Sources**: Discogs, MusicBrainz
    - Websearch: Tavily (if configured) + DuckDuckGo fallback
- **ML Models**: ViT-base (image embeddings), Tesseract (OCR)
- **DevOps**: Docker, Docker Compose, GitHub Actions

See [Tech Stack Guide](docs/tech-stack.md) for details.

---

---

## Need Help?

### Common Questions

**Q: I don't have an Anthropic API key. Can I still use Phonox?**  
A: No, Claude API is required. Get a free tier key at [console.anthropic.com](https://console.anthropic.com).

**Q: Can I use Phonox without Docker?**  
A: Not recommended. Docker ensures all dependencies work correctly. If you must, install: Python 3.12, PostgreSQL 16, Redis 7, Node.js 18.

**Q: How do I backup my vinyl collection?**  
A: Run `./phonox-cli backup` weekly. Backups are stored in `./backups/`.

**Q: Can I run Phonox on my phone?**  
A: Yes! It's a Progressive Web App (PWA). Open http://localhost:5173 on your phone and tap "Install" or "Add to Home Screen".

**Q: How do I import my existing vinyl spreadsheet?**  
A: Currently manual. We're working on CSV import (see roadmap). For now, use the UI to add records.

### Get Support

- 📖 **Documentation**: See links above
- 🐛 **Report Issues**: Open an issue on GitHub
- 💬 **Discuss Features**: Start a discussion
- 👥 **Join Community**: See CONTRIBUTING.md

---

## What's New (Latest Version: 1.2.1)

✨ **Version 1.2.1** (January 28, 2026)
- Cleaned up debug artifacts
- Improved stability
- Fixed white screen issues

See [CHANGELOG.md](CHANGELOG.md) for complete history.

---

## Status & Roadmap

**Last Updated**: 2026-01-28  
**Current Version**: 1.2.1  
**Status**: Production Ready ✅

### Completed Features
- ✅ Image-based vinyl identification
- ✅ Metadata lookup (Discogs, MusicBrainz)
- ✅ AI-powered valuation
- ✅ Web-based UI (mobile + desktop)
- ✅ Spotify integration
- ✅ Enhanced web search

### Planned Features
- 🔄 CSV import/export
- 🔄 Barcode printing
- 🔄 Collection insurance reports
- 🔄 Social sharing
- 🔄 Mobile app (iOS/Android)

See [Implementation Plan](.github/agents/implementation-plan.md) for details.

---

## License

This project is licensed under the MIT License - see [LICENSE](LICENSE) file for details.

---

## Contributing

Contributions are welcome! Please see [Contributing Guide](CONTRIBUTING.md) for guidelines on how to get started, including:
- Setting up your development environment
- Git workflow and branching strategy
- Code style and commit message conventions
- Testing and validation procedures

---

## Support

- **Issues & Feature Requests**: [GitHub Issues](https://github.com/yourusername/phonox/issues)
- **Documentation**: See [docs/](docs/) folder for detailed technical documentation

---

## Acknowledgments

- Built with [Claude AI](https://www.anthropic.com) for record identification and chat
- Uses [Tavily](https://tavily.com) for web search (with DuckDuckGo fallback)
- Data enrichment from [MusicBrainz](https://musicbrainz.org) and [Spotify API](https://developer.spotify.com)
- Powered by [FastAPI](https://fastapi.tiangolo.com), [React](https://react.dev), and [LangGraph](https://langchain.com/langgraph)

