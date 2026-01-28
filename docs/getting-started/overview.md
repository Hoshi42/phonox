# Getting Started with Phonox

Learn how to install and set up Phonox for your vinyl record collection.

## Prerequisites

Before you begin, make sure you have:

- **Docker & Docker Compose** installed
  - [Install Docker](https://docs.docker.com/get-docker/)
  - [Install Docker Compose](https://docs.docker.com/compose/install/)

- **Git** (for cloning the repository)
  - [Install Git](https://git-scm.com/downloads)

- **API Keys** (free or paid)
  - Anthropic API key ([get here](https://console.anthropic.com/account/keys))
  - Tavily API key ([get here](https://tavily.com/))

## System Requirements

| Component | Minimum | Recommended |
|-----------|---------|-------------|
| CPU | 2 cores | 4 cores |
| RAM | 2GB | 4GB |
| Disk | 1GB | 5GB |
| OS | Linux/Mac/Windows | Linux |

## Installation Steps

### 1. Clone the Repository

```bash
git clone https://github.com/your-username/phonox.git
cd phonox
```

### 2. Set Up Environment Variables

```bash
# Copy the example environment file
cp .env.example .env

# Edit with your API keys
nano .env  # or use your preferred editor
```

**Required environment variables:**
```
ANTHROPIC_API_KEY=sk-ant-...
TAVILY_API_KEY=tvly-...
DATABASE_URL=postgresql://phonox:phonox123@db:5432/phonox
```

### 3. Start Services

```bash
# Build and start all services
docker-compose up -d --build

# Check status
docker-compose ps
```

You should see:
- `phonox_backend` - Running on http://localhost:8000
- `phonox_frontend` - Running on http://localhost:5173
- `phonox_db` - PostgreSQL database

### 4. Access the Application

| Component | URL |
|-----------|-----|
| **Frontend** | http://localhost:5173 |
| **Backend API** | http://localhost:8000 |
| **API Documentation** | http://localhost:8000/docs |
| **ReDoc** | http://localhost:8000/redoc |

### 5. Verify Installation

Open your browser and go to: **http://localhost:5173**

You should see the Phonox interface with:
- Chat panel on the left
- Upload area in the center
- Collection panel on the right

## Common Issues

### Ports Already in Use

If you get "Address already in use" error:

```bash
# Find what's using the ports
lsof -i :8000  # Backend
lsof -i :5173  # Frontend

# Kill the process (on Linux/Mac)
kill -9 <PID>

# Or change ports in docker-compose.yml
```

### Docker Not Running

```bash
# Start Docker daemon
sudo systemctl start docker  # Linux
open -a Docker              # Mac
# Or start Docker Desktop
```

### API Key Errors

Make sure your `.env` file has valid API keys:

```bash
# Test your Anthropic API key
curl -X GET https://api.anthropic.com/v1/messages \
  -H "x-api-key: $ANTHROPIC_API_KEY" \
  -H "anthropic-version: 2023-06-01"
```

### Database Connection Error

```bash
# Wait for database to be ready
docker-compose logs db

# If stuck, restart
docker-compose down
docker-compose up -d --build
```

## What's Next?

- ✅ **[Quick Start Guide](quick-start.md)** - Your first vinyl identification
- 📖 **[User Guide](../user-guide/uploading.md)** - Learn all features
- 🔧 **[Development Setup](../development/setup.md)** - For developers

## Getting Help

- Check [Troubleshooting](../development/setup.md#troubleshooting)
- Search [GitHub Issues](https://github.com/your-username/phonox/issues)
- Ask in [GitHub Discussions](https://github.com/your-username/phonox/discussions)
