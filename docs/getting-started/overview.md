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
- Anthropic (required): [console.anthropic.com](https://console.anthropic.com/account/keys)
- Tavily (optional): [tavily.com](https://tavily.com)

**Required environment variables:**
```env
ANTHROPIC_API_KEY=sk-ant-...
TAVILY_API_KEY=tvly-...  # optional
DATABASE_URL=postgresql://phonox:phonox123@db:5432/phonox  # pre-configured
```

See the `.env.example` file in the project root for all available configuration options.

### Step 3: Install and Start

```bash
# Make executable and run (installs + starts everything)
chmod +x start-cli.sh
./start-cli.sh
```

The `start-cli.sh` script automatically:
- ✅ Builds Docker images
- ✅ Starts all services (database, backend, frontend)
- ✅ Initializes the database
- ✅ Runs health checks

### Step 4: Access the Application

**You're done!** Open your browser:

| Component | URL |
|-----------|-----|
| **Frontend** | http://localhost:5173 |
| **Backend API** | http://localhost:8000 |
| **API Documentation** | http://localhost:8000/docs |
| **ReDoc** | http://localhost:8000/redoc |

### Step 5: Verify Installation

Open **http://localhost:5173** - you should see the Phonox interface with:
- Upload area with drag-and-drop in the center
- Chat panel on the right
- "My Collection" button (top right)

---

## Alternative: Manual Docker Installation

If you prefer manual control:

```bash
# Setup environment
cp .env.example .env
# Edit .env with your API keys

# Build and start
docker compose up -d --build

# Check status
docker compose ps
```

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
- �️ **[CLI Tool](cli.md)** - Command-line management
- 🤝 **[Contributing](../contributing.md)** - For developers

## Getting Help

- Check [Database Connection Guide](../database-retry.md) for connection issues
- Search [GitHub Issues](https://github.com/your-username/phonox/issues)
- Ask in [GitHub Discussions](https://github.com/your-username/phonox/discussions)
