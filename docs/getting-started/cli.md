# Command Line Interface (CLI)

Phonox includes two command-line tools for managing the application.

## Quick Start: start-cli.sh

The simplest way to install and start Phonox:

```bash
chmod +x start-cli.sh
./start-cli.sh
```

**What it does:**
- Builds all Docker images
- Starts database, backend, and frontend services
- Initializes the database
- Runs health checks

**Use this for:** First-time installation and quick startup.

---

## Advanced: phonox-cli

For configuration and management tasks:

```bash
./phonox-cli [command] [options]
```

### Interactive Mode

Run without arguments for an interactive menu:

```bash
./phonox-cli
```

The interactive menu displays:
- Container status
- Network status
- Backup information
- Numbered menu options

---

## Available Commands

### install

Build Docker images and prepare directories.

```bash
# Basic installation (build only)
./phonox-cli install

# Skip building if images exist
./phonox-cli install --skip-build

# Install and start immediately
./phonox-cli install --up
```

**What it does:**
- Creates required directories (`backups/`, `data/uploads/`, `data/postgres/data/`)
- Builds Docker images for backend and frontend
- Optionally starts containers and initializes database

**First-time setup:**
```bash
./phonox-cli install --up
```

---

### configure

Set API keys and model configuration in `.env` file.

**Prerequisites:** You must first create `.env` from the template:
```bash
cp .env.example .env
```

**Usage:**
```bash
# Configure Anthropic API key
./phonox-cli configure --anthropic sk-ant-xxxxx

# Configure Tavily web search key
./phonox-cli configure --tavily tvly-xxxxx

# Configure multiple at once
./phonox-cli configure \
  --anthropic sk-ant-xxxxx \
  --tavily tvly-xxxxx
```

**After configuring, restart services:**
```bash
./phonox-cli restart
```

**Configuration Keys:**
- `--anthropic` - Anthropic API key (required for AI features)
- `--tavily` - Tavily API key (optional, for web search)
- `--vision-model` - Model for image analysis (default: claude-sonnet-4-5-20250929)
- `--chat-model` - Model for chat (default: claude-haiku-4-5-20251001)

---

### start

Start all Docker containers (backend, frontend, database).

```bash
./phonox-cli start
```

**What it does:**
- Checks Docker network status
- Starts containers in detached mode
- Verifies database health
- Reports ready status

**When to use:**
- After installation
- After stopping containers
- To resume work

---

### stop

Stop all running Docker containers.

```bash
./phonox-cli stop
```

**What it does:**
- Gracefully stops all services
- Preserves data volumes
- Cleans up containers

**When to use:**
- Done working for the day
- Before system maintenance
- To free up resources

---

### restart

Stop and restart containers with network recovery.

```bash
./phonox-cli restart
```

**What it does:**
- Stops all containers
- Recreates network if needed
- Starts containers fresh
- Checks database health

**When to use:**
- Database connection issues
- Network problems
- After configuration changes
- To clear temporary state

---

### backup

Create a backup of the database and uploaded images.

```bash
./phonox-cli backup
```

**What it does:**
- Exports PostgreSQL database to SQL file
- Archives uploaded images to tar.gz
- Timestamps backup files
- Saves to `./backups/` directory

**Backup files:**
```
backups/
├── phonox_db_20260206_143022.sql         # Database dump
└── phonox_uploads_20260206_143022.tar.gz # Image archive
```

**When to use:**
- Before major updates
- Regular scheduled backups
- Before restore operations
- For data safety

---

### restore

Restore database and images from a previous backup.

```bash
# List available backups
ls -lh backups/

# Restore specific backup
./phonox-cli restore 20260206_143022
```

**What it does:**
- Restores PostgreSQL database from SQL dump
- Extracts uploaded images from archive
- Replaces current data

**⚠️ Warning:** This overwrites current data. Always backup first!

**When to use:**
- Recovering from data loss
- Rolling back changes
- Testing with previous data
- Migrating to new system

---

### docs

Start the MkDocs documentation server.

```bash
./phonox-cli docs
```

**What it does:**
- Creates Python virtual environment if needed
- Installs MkDocs dependencies
- Starts documentation server at http://localhost:8001
- Watches for file changes and auto-reloads

**Access documentation:**
- Open http://localhost:8001 in your browser
- Press Ctrl+C to stop the server

**When to use:**
- Reading documentation offline
- Contributing to docs
- Previewing doc changes

---

## Interactive Menu

When run without arguments, Phonox CLI presents an interactive menu:

```
 ██████╗ ██╗  ██╗ ██████╗ ███╗   ██╗ ██████╗ ██╗  ██╗
 ██╔══██╗██║  ██║██╔═══██╗████╗  ██║██╔═══██╗╚██╗██╔╝
 ██████╔╝███████║██║   ██║██╔██╗ ██║██║   ██║ ╚███╔╝ 
 ██╔═══╝ ██╔══██║██║   ██║██║╚██╗██║██║   ██║ ██╔██╗ 
 ██║     ██║  ██║╚██████╔╝██║ ╚████║╚██████╔╝██╔╝ ██╗
 ╚═╝     ╚═╝  ╚═╝ ╚═════╝ ╚═╝  ╚═══╝ ╚═════╝ ╚═╝  ╚═╝
Vinyl Intelligence Console

Status
────────────────────────────────────────────
Containers:
NAME                 STATUS              PORTS
phonox-backend-1     Up 2 hours          0.0.0.0:8000->8000/tcp
phonox-frontend-1    Up 2 hours          0.0.0.0:5173->5173/tcp
phonox-db-1          Up 2 hours          5432/tcp
Network: phonox_phonox_network
Backups: 3 set(s) (latest: 20260206_143022)

Menu
────────────────────────────────────────────
1) Install (build images)
2) Install + start
3) Configure API keys
4) Start containers
5) Stop containers
6) Restart containers (with recovery)
7) Backup
8) Restore
9) View documentation (MkDocs)
0) Exit

Select an option: 
```

### Menu Options

1. **Install** - Build Docker images only
2. **Install + start** - Build and start immediately (recommended for first run)
3. **Configure API keys** - Interactive prompt for API keys
4. **Start** - Launch containers
5. **Stop** - Stop containers
6. **Restart** - Full restart with recovery
7. **Backup** - Create backup now
8. **Restore** - Restore from backup (prompts for timestamp)
9. **View documentation** - Start MkDocs server
0. **Exit** - Quit CLI

## Common Workflows

### First-Time Setup

```bash
# 1. Configure API keys
./phonox-cli configure --anthropic sk-ant-xxxxx --tavily tvly-xxxxx

# 2. Install and start
./phonox-cli install --up

# 3. Access application
# Frontend: http://localhost:5173
# API: http://localhost:8000
```

### Daily Use

```bash
# Start in the morning
./phonox-cli start

# Stop at end of day
./phonox-cli stop
```

### Backup Workflow

```bash
# Weekly backup
./phonox-cli backup

# Verify backup exists
ls -lh backups/

# Restore if needed
./phonox-cli restore 20260206_143022
```

### Troubleshooting Workflow

```bash
# If database has issues
./phonox-cli restart

# If containers won't start
./phonox-cli stop
./phonox-cli install --skip-build
./phonox-cli start

# Check status
./phonox-cli  # Run interactive mode to see status
```

## Requirements

### System Requirements

- **Docker** - Container runtime
- **Docker Compose** - Multi-container orchestration
- **Python 3.8+** - For CLI script
- **Bash** - For wrapper scripts

### Checking Installation

```bash
# Check Docker
docker --version
docker compose version

# Check Python
python3 --version

# Check Phonox CLI
./phonox-cli --help
```

## Environment Variables

The CLI manages these environment variables in `.env`:

| Variable | Purpose | Default | Required |
|----------|---------|---------|----------|
| `ANTHROPIC_API_KEY` | Anthropic AI API access | - | Yes |
| `TAVILY_API_KEY` | Web search API access | - | No |
| `ANTHROPIC_VISION_MODEL` | Image analysis model | claude-sonnet-4-5-20250929 | No |
| `ANTHROPIC_CHAT_MODEL` | Chat model | claude-haiku-4-5-20251001 | No |
| `DATABASE_URL` | PostgreSQL connection | Set by docker-compose | Auto |

## Troubleshooting

### CLI Won't Run

```bash
# Make scripts executable
chmod +x phonox-cli start-cli.sh

# Run with explicit interpreter
python3 scripts/phonox_cli.py
```

### Docker Not Found

```bash
# Install Docker
# See: https://docs.docker.com/get-docker/

# Verify installation
docker --version
docker compose version
```

### Permission Denied

```bash
# Add user to docker group (Linux)
sudo usermod -aG docker $USER

# Log out and back in
# Or use sudo
sudo ./phonox-cli start
```

### Database Won't Start

```bash
# Check logs
docker compose logs db

# Restart with recovery
./phonox-cli restart

# If still failing, rebuild
./phonox-cli stop
docker compose down -v  # ⚠️ Deletes data!
./phonox-cli install --up
```

### Network Issues

```bash
# Restart with network recovery
./phonox-cli restart

# Manual network reset
docker compose down
docker network prune
./phonox-cli start
```

## Advanced Usage

### Custom Backup Location

Edit `scripts/backup.sh` to change backup directory:

```bash
BACKUP_DIR="./backups"  # Change this path
```

### Automated Backups

Add to crontab for daily backups:

```bash
# Edit crontab
crontab -e

# Add daily backup at 2 AM
0 2 * * * cd /path/to/phonox && ./phonox-cli backup
```

### Scripting with CLI

```bash
#!/bin/bash
# Example: backup before update

cd /path/to/phonox

# Create backup
./phonox-cli backup

# Pull latest code
git pull

# Restart containers
./phonox-cli restart

# Check status
docker compose ps
```

## Next Steps

- [Installation Guide](installation.md) - Full setup instructions
- [Configuration Guide](configuration.md) - Detailed config options
- [Database Retry](../database-retry.md) - Database troubleshooting
