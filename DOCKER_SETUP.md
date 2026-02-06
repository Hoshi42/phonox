# Phonox Docker Setup Guide

## Quick Start

### Prerequisites
- Docker Engine 20.10+
- Docker Compose 2.0+

### Start All Services

```bash
# Build and start both backend and frontend containers
docker-compose up -d --build

# Or without rebuilding (if images already exist)
docker-compose up -d

# View logs
docker-compose logs -f

# View specific service logs
docker-compose logs -f backend    # Backend logs
docker-compose logs -f frontend   # Frontend logs
```

### Access Services

- **Frontend**: http://localhost:5173
- **Backend API**: http://localhost:8000
- **API Docs**: http://localhost:8000/docs
- **Backend Health**: http://localhost:8000/health

## Development Workflow

### Hot Reload
Both services are configured with hot reload enabled:
- **Backend**: Uvicorn with `--reload` flag watches `./backend` directory
- **Frontend**: Vite dev server watches `./frontend` directory

Make changes to source code and they'll automatically reload in the containers.

### Running Tests

#### Backend Unit Tests
```bash
docker-compose exec backend python -m pytest tests/ -v
```

#### Backend Type Checking
```bash
docker-compose exec backend mypy backend/
```

#### Frontend E2E Tests
```bash
docker-compose exec frontend npm run test:e2e
```

### Database & Files
- **PostgreSQL database**: Managed by Docker Compose
  - Container: `phonox_db`
  - Data volume: `./data/postgres/data` (persistent storage)
  - Connection: `postgresql://phonox:phonox123@db:5432/phonox`
- **Image uploads**: Stored in `./data/uploads` (persistent)
- All data persists between container restarts
- Database backed up automatically in local filesystem

## Container Management

### Stop Services
```bash
docker-compose down
```

### Remove Everything (including volumes)
```bash
docker-compose down -v
```

### View Running Containers
```bash
docker-compose ps
```

### Access Container Shell
```bash
docker-compose exec backend bash       # Backend shell
docker-compose exec frontend sh        # Frontend shell
```

### Rebuild Specific Service
```bash
docker-compose build backend           # Rebuild backend only
docker-compose up -d backend           # Restart backend
```

## Docker Architecture

### Services

**phonox_backend** (Python 3.12-slim)
- FastAPI application
- Port: 8000
- Volume mounts: `./backend`, `./data/uploads`
- Database: Connects to `phonox_db` container
- Healthcheck: Curl to `/health` endpoint
- Auto-reload: Enabled

**phonox_frontend** (Node 20-alpine)
- Vite React dev server
- Port: 5173
- Volume mounts: `./frontend`, `node_modules`
- Healthcheck: Wget to root path
- Auto-reload: Enabled

**phonox_db** (PostgreSQL 15-alpine)
- PostgreSQL database server
- Port: 5432 (internal only, not exposed to host)
- Database: `phonox`
- User: `phonox`
- Password: `phonox123` (change for production!)
- Volume mount: `./data/postgres/data` (persistent storage)
- Healthcheck: pg_isready command

### Network
- Network: `phonox_network` (bridge driver)
- Container-to-container communication:
  - Backend → Database: `postgresql://phonox:phonox123@db:5432/phonox`
  - Frontend → Backend: `http://backend:8000`
- Host access:
  - Frontend UI: `http://localhost:5173`
  - Backend API: `http://localhost:8000`
  - Database: Not exposed (internal only)

## Troubleshooting

### Frontend can't connect to backend
The issue is typically a URL mismatch. Inside containers, use `http://backend:8000`. From the host, use `http://localhost:8000`.

**Check environment variables:**
```bash
docker-compose exec frontend printenv | grep VITE
```

### Ports already in use
```bash
# Kill existing containers
docker-compose down

# Find what's using the port (macOS/Linux)
lsof -i :8000    # Backend
lsof -i :5173    # Frontend
lsof -i :5432    # PostgreSQL (if exposed)
```

### Database connection issues
```bash
# Check database container is running
docker-compose ps db

# View database logs
docker-compose logs db

# Test database connectivity from backend
docker-compose exec backend python -c "from backend.database import engine; print('Connected!' if engine else 'Failed')"

# Database automatically retries connection (5 attempts with exponential backoff)
# If issues persist, check DATABASE_URL in docker-compose.yml
```

### Clear everything and start fresh
```bash
docker-compose down -v              # Remove all
docker system prune -a --volumes    # Clean up Docker
docker-compose up -d --build        # Rebuild and start
```

### Check service health
```bash
docker-compose ps                   # View health status
docker-compose exec backend curl http://localhost:8000/health
docker-compose exec frontend wget -q -O- http://localhost:5173
```

## Build Details

### Backend Build
- **Stage 1** (builder): Installs Python dependencies
- **Stage 2** (runtime): Slim image with only production dependencies
- **Size**: ~200MB (optimized with multi-stage build)

### Frontend Build
- **Stage 1** (builder): Installs npm dependencies
- **Stage 2** (runtime): Alpine-based Node with only app code
- **Size**: ~150MB (optimized with multi-stage build)

## Environment Variables

### Backend
- `PYTHONUNBUFFERED=1`: Direct output to logs
- `PYTHONDONTWRITEBYTECODE=1`: Don't write .pyc files

### Frontend
- `VITE_API_URL=http://backend:8000`: Backend API URL (inside container)

## Next Steps

1. **Run services**: `docker-compose up -d --build`
2. **Check health**: `docker-compose ps`
3. **View frontend**: Open http://localhost:5173
4. **Run tests**: 
   - Backend: `docker-compose exec backend python -m pytest tests/ -v`
   - Frontend: `docker-compose exec frontend npm run test:e2e`

## References

- [Docker Documentation](https://docs.docker.com/)
- [Docker Compose Documentation](https://docs.docker.com/compose/)
- [Python Docker Best Practices](https://docs.docker.com/language/python/)
- [Node Docker Best Practices](https://docs.docker.com/language/nodejs/)
