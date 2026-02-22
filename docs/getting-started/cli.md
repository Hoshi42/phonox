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

Run without arguments for a full-screen interactive menu:

```bash
./phonox-cli
```

The interactive menu uses a **curses-based arrow-key interface**. Use **↑ / ↓** to move the highlight bar, **Enter** to select, and **q** or **Esc** to cancel or go back.

The header displays:
- The Phonox ASCII logo (magenta)
- A live status panel showing each service individually:
  - **Frontend**, **Backend**, **DB** — each with a ✔ / ✘ icon
  - **Network** status and the **latest backup** timestamp

No mouse or numbered key input is required.

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

Open the interactive API key and model configurator.

```bash
./phonox-cli configure
```

**How it works:**

A curses menu lists all configurable keys with their current values masked:

```
  Anthropic API key          ****…TgAA
  Tavily API key             ****…UxT4
  Vision model               claude-sonnet-4-6
  Chat model                 claude-haiku-4-5-20251001
  Aggregation model          claude-sonnet-4-6
  Enhancement model          claude-opus-4-5
  ──────────────────────────────────────
  Save & apply
  Cancel
```

Select a key, type the new value (leave blank to keep the current value), then choose **Save & apply** to write the changes to `.env`. The running containers are restarted automatically so changes take effect immediately.

**Configurable keys:**

| Key | Purpose | Secret |
|-----|---------|--------|
| `ANTHROPIC_API_KEY` | Anthropic AI API access | Yes |
| `TAVILY_API_KEY` | Web search API access | Yes |
| `ANTHROPIC_VISION_MODEL` | Model for image analysis | No |
| `ANTHROPIC_CHAT_MODEL` | Model for conversational chat | No |
| `ANTHROPIC_AGGREGATION_MODEL` | Model for merging multi-image results | No |
| `ANTHROPIC_ENHANCEMENT_MODEL` | Model for metadata enrichment | No |

**Prerequisites:** A `.env` file must exist. Create one from the template first:
```bash
cp .env.example .env
```

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

Restore database and images from a previous backup — interactively.

```bash
./phonox-cli restore
```

**How it works:**

A curses menu lists all available backups sorted newest-first:

```
  2026-02-22  22:26:04
  2026-02-16  23:23:22
  2026-02-16  22:49:52
  2026-02-11  21:28:24
  ─────────────────────
  Cancel
```

Select a backup, then type `yes` to confirm. The CLI then restores the PostgreSQL database from the SQL dump and extracts the image archive.

**⚠️ Warning:** This overwrites current data. Always create a backup first!

**When to use:**
- Recovering from data loss
- Rolling back changes
- Testing with previous data
- Migrating to a new system

---

### manage-users

Rename vinyl record collections (user tags) directly from the CLI.

```bash
./phonox-cli manage-users
```

**How it works:**

A curses menu lists all collections with their record counts:

```
  Jan (142 records)
  ─────────────────
  Back
```

Select a collection, then choose **Rename collection** and type the new name. All records in that collection are updated instantly via a database query.

> **Note:** Collections are derived from the `user_tag` field on records — a collection exists only while it has records. Empty collections cannot appear in the list and therefore cannot be created or deleted independently.

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

---

## Interactive Menu

When run without arguments, Phonox CLI opens a full-screen curses interface:

```
 ██████╗ ██╗  ██╗ ██████╗ ███╗   ██╗ ██████╗ ██╗  ██╗
 ██╔══██╗██║  ██║██╔═══██╗████╗  ██║██╔═══██╗╚██╗██╔╝
 ██████╔╝███████║██║   ██║██╔██╗ ██║██║   ██║ ╚███╔╝
 ██╔═══╝ ██╔══██║██║   ██║██║╚██╗██║██║   ██║ ██╔██╗
 ██║     ██║  ██║╚██████╔╝██║ ╚████║╚██████╔╝██╔╝ ██╗
 ╚═╝     ╚═╝  ╚═╝ ╚═════╝ ╚═╝  ╚═══╝ ╚═════╝ ╚═╝  ╚═╝
 Vinyl Intelligence Console

──────  Status  ──────
  Frontend ✔   Backend ✔   DB ✔
  Network ✔   Backup 2026-02-22  22:26

┌──────────────────────────────────┐
│ Phonox — Main Menu               │
├──────────────────────────────────┤
│   Install (build images)         │
│   Install + start                │
│ ▶ Configure API keys             │
│   Start containers               │
│   Stop containers                │
│   Restart containers             │
│   Backup                         │
│   Restore                        │
│   Manage collections             │
│   View documentation (MkDocs)    │
│   Exit                           │
└──────────────────────────────────┘
  ↑/↓ navigate  Enter select  q/Esc cancel
```

### Navigation

| Key | Action |
|-----|--------|
| `↑` / `↓` | Move highlight bar |
| `Enter` | Select item |
| `q` or `Esc` | Cancel / go back |

### Status Panel

The header status panel refreshes each time the menu opens:

- **Frontend ✔ / ✘** — Vite dev server container state
- **Backend ✔ / ✘** — FastAPI backend container state
- **DB ✔ / ✘** — PostgreSQL container state
- **Network ✔ / ✘** — Docker network status
- **Backup** — Timestamp of the most recent backup set

Icons are colour-coded: green (✔ running), yellow (⚠ degraded), red (✘ down).

---

## Common Workflows

### First-Time Setup

```bash
# 1. Install and start
./phonox-cli install --up

# 2. Configure API keys interactively
./phonox-cli configure
# — or open the interactive menu and select "Configure API keys"

# 3. Access the application
# Frontend: http://localhost:5173
# API:      http://localhost:8000
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
# Create a backup
./phonox-cli backup

# Restore interactively (pick from list)
./phonox-cli restore
```

### Troubleshooting Workflow

```bash
# If database has issues
./phonox-cli restart

# If containers won't start
./phonox-cli stop
./phonox-cli install --skip-build
./phonox-cli start

# Check status at a glance
./phonox-cli  # open the interactive menu
```

---

## Requirements

### System Requirements

- **Docker** - Container runtime
- **Docker Compose v2** - Multi-container orchestration
- **Python 3.8+** - For CLI script (uses only stdlib: `curses`, `subprocess`, `re`)
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

---

## Environment Variables

The `configure` command manages these keys in `.env`:

| Variable | Purpose | Secret |
|----------|---------|--------|
| `ANTHROPIC_API_KEY` | Anthropic AI API access | Yes |
| `TAVILY_API_KEY` | Web search API access | Yes |
| `ANTHROPIC_VISION_MODEL` | Model for image analysis | No |
| `ANTHROPIC_CHAT_MODEL` | Model for conversational chat | No |
| `ANTHROPIC_AGGREGATION_MODEL` | Model for merging multi-image results | No |
| `ANTHROPIC_ENHANCEMENT_MODEL` | Model for metadata enrichment | No |

Additional variables (database, retry, scraping, etc.) can be edited directly in `.env` — see [Configuration Guide](configuration.md) for full details.

---

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

# Log out and back in, or use sudo
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

---

## Advanced Usage

### Custom Backup Location

Edit `scripts/backup.sh` to change the backup directory:

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

---

## Next Steps

- [Installation Guide](installation.md) - Full setup instructions
- [Configuration Guide](configuration.md) - Detailed config options
- [Database Retry](../database-retry.md) - Database troubleshooting
