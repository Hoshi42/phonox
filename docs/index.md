# Phonox - AI-Powered Vinyl Record Identification

Welcome to Phonox! An intelligent vinyl record identification system powered by AI, computer vision, and web search.

## 🎯 What is Phonox?

Phonox is an AI-powered application that helps you:
- **Identify vinyl records** from photos using advanced computer vision
- **Get detailed metadata** including artist, title, release year, and catalog information
- **Estimate value** of your records based on current market data
- **Manage your collection** with detailed tracking and organization
- **Chat with AI** about your vinyl records and get recommendations

## ✨ Key Features

### 🤖 AI-Powered Identification
- Upload photos of your vinyl records (1-5 images)
- Get instant identification using Claude Sonnet 4 vision analysis
- Automatic barcode detection (UPC/EAN)
- Automatic metadata enrichment from Discogs, MusicBrainz, and Spotify

### 💾 Collection Management
- Build your personal vinyl collection in PostgreSQL database
- Track condition, value, and notes
- Multiple user/collector support
- Filter and search your records
- Add images to existing records

### 💬 Intelligent Chat
- Ask questions about your records
- Get music recommendations
- Get historical context about artists and albums
- Web search integration for current information

### 📊 Value Estimation
- Automatic market price estimation
- Based on real Discogs market data
- Supports multiple currencies (EUR, USD)

### 📱 Mobile-Friendly
- Fully responsive design
- Optimized for touch interfaces
- Works great on tablets and phones

## 🚀 Quick Start

### For Users

```bash
# 1. Start the application
docker-compose up -d

# 2. Open in your browser
# Frontend: http://localhost:5173
# API Docs: http://localhost:8000/docs
```

### For Developers

```bash
# 1. Clone the repository
git clone https://github.com/your-username/phonox.git
cd phonox

# 2. Set up environment
cp .env.example .env
# Edit .env with your API keys

# 3. Use CLI for management
./phonox-cli install --up  # Install and start

# Or start services manually
docker-compose up -d

# 4. View logs
docker-compose logs -f
```

## 📚 Documentation

- **[Getting Started](getting-started/overview.md)** - Installation and setup
- **[Installation Guide](getting-started/installation.md)** - Detailed installation
- **[Quick Start](getting-started/quick-start.md)** - Get started in 5 minutes
- **[API Reference](api/introduction.md)** - Complete API documentation
- **[Database & Retry Configuration](database-retry.md)** - Connection troubleshooting
- **[Contributing](contributing.md)** - How to contribute

## 💻 CLI Tools

Phonox includes a management CLI for common tasks:

```bash
# Interactive menu
./phonox-cli

# Or specific commands
./phonox-cli install --up       # Install and start
./phonox-cli configure          # Configure API keys
./phonox-cli start              # Start containers
./phonox-cli stop               # Stop containers
./phonox-cli restart            # Restart containers
./phonox-cli backup             # Backup database
./phonox-cli restore <timestamp> # Restore from backup
./phonox-cli docs               # View documentation locally
```

## 🛠️ Tech Stack

### Frontend
- **React 18** - Modern UI framework
- **TypeScript** - Type safety
- **Vite** - Lightning-fast build tool
- **CSS Modules** - Scoped styling

### Backend
- **FastAPI** - Modern Python web framework
- **SQLAlchemy** - ORM for database operations
- **LangGraph** - Orchestration for AI workflows
- **Claude Sonnet 4** - Vision analysis
- **Claude Haiku 4.5** - Chat assistant

### External Services
- **Anthropic Claude** - AI vision and chat
- **Tavily** - Web search API
- **Discogs** - Vinyl metadata
- **MusicBrainz** - Music metadata
- **Spotify** - Music streaming data

### Infrastructure
- **PostgreSQL 15** - Production database
- **Docker** - Containerization
- **Docker Compose** - Multi-container orchestration

## 📊 System Architecture

Phonox uses a 6-node LangGraph workflow for record identification:

```
Image Upload
    ↓
Vision Analysis (Claude Sonnet 4)
    ↓
Metadata Lookup (Discogs/MusicBrainz)
    ↓
Confidence Gate (>0.85? → Auto-commit)
    ↓
Web Search Fallback (if uncertain)
    ↓
Result Refinement
    ↓
User Review & Storage
```

## 🔑 Required API Keys

Get free or affordable API keys from:

| Service | Cost | Purpose |
|---------|------|---------|
| [Anthropic](https://console.anthropic.com) | Pay-per-use (~$0.002 per image) | Vision & chat AI |
| [Tavily](https://tavily.com) | Free tier (100 calls/month) | Web search |
| Discogs | Free API | Vinyl metadata |
| MusicBrainz | Free API | Music metadata |
| Spotify | Free API | Album data |

## 💡 Examples

### Identify a Record

```python
import requests

# Upload image
with open('vinyl.jpg', 'rb') as f:
    files = {'images': f}
    response = requests.post(
        'http://localhost:8000/api/v1/identify',
        files=files
    )
    record_id = response.json()['record_id']

# Poll for results
import time
while True:
    result = requests.get(f'http://localhost:8000/api/v1/identify/{record_id}')
    if result.json()['status'] == 'complete':
        break
    time.sleep(2)

# View results
print(result.json()['metadata'])
```

### Add to Collection

```python
requests.post('http://localhost:8000/api/register/add', json={
    'user_tag': 'collector1',
    'vinyl_record': {
        'artist': 'The Beatles',
        'title': 'Abbey Road',
        'year': 1969,
        'label': 'Apple Records'
    }
})
```

See [API Examples](api/examples.md) for more.

## 🤝 Contributing

We welcome contributions! See [CONTRIBUTING.md](contributing.md) for:
- How to report issues
- How to submit pull requests
- Development guidelines
- License agreement

## 📄 License

Phonox is licensed under the [MIT License](license.md).

Copyright © 2026 Phonox Contributors

## 🆘 Support

- **GitHub Issues**: [Report bugs or request features](https://github.com/your-username/phonox/issues)
- **Discussions**: [Ask questions and share ideas](https://github.com/your-username/phonox/discussions)
- **Documentation**: [Detailed guides and references](.)

## 🎵 Project Status

**Version**: 1.5.3  
**Status**: Active Development  
**Last Updated**: February 6, 2026

See [Changelog](changelog.md) for version history.

---

Ready to get started? → [Installation Guide](getting-started/installation.md)
