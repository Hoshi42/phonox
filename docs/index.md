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
- Upload photos of your vinyl records
- Get instant identification using Claude 3.5 Sonnet vision analysis
- Automatic metadata enrichment from Discogs, MusicBrainz, and Spotify

### 💾 Collection Management
- Build your personal vinyl collection
- Track condition, value, and notes
- Sort by artist, title, year, or estimated value
- Export your collection data

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

# 3. Start services
docker-compose up -d

# 4. View logs
docker-compose logs -f
```

## 📚 Documentation

- **[Getting Started](getting-started/overview.md)** - Installation and setup
- **[User Guide](user-guide/uploading.md)** - How to use Phonox
- **[API Reference](api/introduction.md)** - Complete API documentation
- **[Architecture](architecture/system-design.md)** - System design and internals
- **[Development](development/setup.md)** - Developer setup and contribution
- **[Deployment](deployment/cloud-run.md)** - Production deployment guides

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
- **Claude 3.5 Sonnet** - Vision and chat models

### External Services
- **Anthropic Claude** - AI vision and chat
- **Tavily** - Web search API
- **Discogs** - Vinyl metadata
- **MusicBrainz** - Music metadata
- **Spotify** - Music streaming data

### Infrastructure
- **PostgreSQL** - Production database
- **Docker** - Containerization
- **Docker Compose** - Local development
- **Cloud Run** - Serverless deployment

## 📊 System Architecture

Phonox uses a 6-node LangGraph workflow for record identification:

```
Image Upload
    ↓
Vision Analysis (Claude)
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

See [System Design](architecture/system-design.md) for detailed architecture.

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

**Version**: 1.3.2  
**Status**: Active Development  
**Last Updated**: January 29, 2026

See [Changelog](changelog.md) for version history.

---

Ready to get started? → [Installation Guide](getting-started/installation.md)
