```
 ██████╗ ██╗  ██╗ ██████╗ ███╗   ██╗ ██████╗ ██╗  ██╗
 ██╔══██╗██║  ██║██╔═══██╗████╗  ██║██╔═══██╗╚██╗██╔╝
 ██████╔╝███████║██║   ██║██╔██╗ ██║██║   ██║ ╚███╔╝ 
 ██╔═══╝ ██╔══██║██║   ██║██║╚██╗██║██║   ██║ ██╔██╗ 
 ██║     ██║  ██║╚██████╔╝██║ ╚████║╚██████╔╝██╔╝ ██╗
 ╚═╝     ╚═╝  ╚═╝ ╚═════╝ ╚═╝  ╚═══╝ ╚═════╝ ╚═╝  ╚═╝
```

**AI-powered Vinyl Collection Agent** – Cataloguing, Valuation, and Documentation

> ⭐ If you find Phonox useful, please **[star the repo](https://github.com/yourusername/phonox)** — it helps others discover the project and motivates further development.

---

## What is Phonox?

Phonox is an intelligent assistant for vinyl record collectors. It helps you:
- **📸 Identify records** by snapping photos or uploading images
- **💰 Get valuations** using multiple data sources (Discogs, MusicBrainz)
- **🎵 Find Spotify links** for listening to your collection
- **📝 Organize your collection** with metadata, ratings, and notes
- **💬 Chat about records** with an AI agent that remembers your collection

> 🖼️ **See it in action** → [UI Gallery & feature walkthrough](docs/gallery.md)
> 📝 **Blog** → [phonox-blog.web.app](https://phonox-blog.web.app/)

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

## Quick Start (3 Simple Steps)

### 1. Clone the Repository

```bash
git clone https://github.com/Hoshi42/phonox.git
cd phonox
```

### 2. Setup Environment with API Key

```bash
# Copy the environment template
cp .env.example .env

# Add your Anthropic API key
./phonox-cli configure --anthropic YOUR_ANTHROPIC_KEY
```

**Get your API key:** [console.anthropic.com](https://console.anthropic.com)

### 3. Install and Start

```bash
# Make executable and run (installs + starts everything)
chmod +x start-cli.sh
./start-cli.sh
```

The `start-cli.sh` script will:
- ✅ Build Docker images
- ✅ Start all services (database, backend, frontend)
- ✅ Initialize the database

**Done!** Open your browser:
- **Frontend (UI)**: http://localhost:5173
- **API Docs**: http://localhost:8000/docs
- **Backend Health**: http://localhost:8000/health

> 💬 Got it running? [Leave a ⭐ on GitHub](https://github.com/yourusername/phonox) or [open an issue](https://github.com/yourusername/phonox/issues) with feedback — it takes 10 seconds and means a lot!

---

## Key Environment Variables

The `.env` file contains all configuration. Key variables:

| Variable | Required | Description |
|----------|----------|-------------|
| `ANTHROPIC_API_KEY` | ✅ Yes | Claude AI API key from [console.anthropic.com](https://console.anthropic.com) |
| `TAVILY_API_KEY` | ⚠️ Optional | Web search API key from [tavily.com](https://tavily.com) |
| `DISCOGS_TOKEN` | ⚠️ Optional | Discogs personal access token – raises rate limit from 25 → 60 req/min |
| `DATABASE_URL` | ✅ Pre-configured | PostgreSQL connection (auto-configured for Docker) |

For all configuration options, see [`.env.example`](./.env.example)

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
./phonox-cli configure --vision-model claude-sonnet-5-5
./phonox-cli configure --chat-model claude-haiku-5-5

# Start services
./phonox-cli start

# Stop services
./phonox-cli stop

# Backup your data
./phonox-cli backup

# Restore from backup (use timestamp from backup folder)
./phonox-cli restore 20260128_143000
```

### Recommended Claude models

| Purpose | Environment variable | Recommended model |
|---|---|---|
| Image analysis | `ANTHROPIC_VISION_MODEL` | `claude-sonnet-5-5` |
| Chat and market valuation | `ANTHROPIC_CHAT_MODEL` | `claude-haiku-5-5` |
| Multi-image aggregation | `ANTHROPIC_AGGREGATION_MODEL` | `claude-sonnet-5-5` |
| Metadata enhancement | `ANTHROPIC_ENHANCEMENT_MODEL` | `claude-opus-5-5` |

These are the recommendations in `.env.example`, not a guarantee of the running
backend's effective configuration. Model variables must reach the backend process;
the current Compose file does not yet forward them. See the
[configuration guide](docs/getting-started/configuration.md#vision--chat-models)
and [current model pricing](docs/architecture/cost-model.md).

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
- **[API Reference](http://localhost:8000/docs)** – Interactive Swagger UI (live)
- **[Architecture](ARCHITECTURE.md)** – Component diagrams and data flows

### 🏗️ For Teams & Contributors
1. **[Contributing Guide](CONTRIBUTING.md)** – How to contribute code



---

## Architecture Overview

React PWA → FastAPI backend → LangGraph AI agent → PostgreSQL, with multi-source metadata enrichment (Discogs, MusicBrainz, Tavily/DuckDuckGo).

→ Full data flows, component diagrams, security and scaling notes: [ARCHITECTURE.md](ARCHITECTURE.md)

---

## Tech Stack

| Layer | Technology |
|-------|------------|
| Backend | Python 3.12, FastAPI, LangGraph, Pydantic v2, SQLAlchemy |
| Frontend | React 18, TypeScript, Vite, PWA |
| Database | PostgreSQL 16 |
| AI / Vision | Claude (Anthropic) — multimodal identification and chat |
| Web Search | Tavily + DuckDuckGo fallback |
| Metadata | Discogs API, MusicBrainz API, Spotify API |
| Infrastructure | Docker, Docker Compose |

See [ARCHITECTURE.md](ARCHITECTURE.md) for detailed component breakdown and data flows.

---

## Need Help?

### Common Questions

**Q: I don't have an Anthropic API key. Can I still use Phonox?**  
A: No, Claude API is required. Get a free tier key at [console.anthropic.com](https://console.anthropic.com).

**Q: Can I use Phonox without Docker?**  
A: Not recommended. Docker ensures all dependencies work correctly. If you must, install: Python 3.12, PostgreSQL 16, Node.js 20.

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

## What's New

See [CHANGELOG.md](CHANGELOG.md) for the full version history.

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
- **⭐ Star the repo**: If Phonox is useful to you, [a star on GitHub](https://github.com/yourusername/phonox) is the simplest way to show it

---

## Acknowledgments

- Built with [Claude AI](https://www.anthropic.com) for record identification and chat
- Uses [Tavily](https://tavily.com) for web search (with DuckDuckGo fallback)
- Data enrichment from [MusicBrainz](https://musicbrainz.org) and [Spotify API](https://developer.spotify.com)
- Powered by [FastAPI](https://fastapi.tiangolo.com), [React](https://react.dev), and [LangGraph](https://langchain.com/langgraph)

---

## ⭐ Show Your Support

If you find Phonox useful, please consider:
- **Starring the repository** on GitHub — it helps others discover the project
- **Opening an issue** with feedback, ideas, or bug reports
- **Sharing** it with other vinyl collectors

Every star and piece of feedback is genuinely appreciated and helps drive development forward.
