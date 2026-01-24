# Deployment & Infrastructure

## Local Development (Docker Desktop)

### Prerequisites
- Docker Desktop (latest) installed
- Docker Compose v2+
- 2+ GB RAM allocation to Docker

### Quick Start

```bash
# Clone and setup
cd phonox
docker compose up -d

# Logs
docker compose logs -f

# Shutdown
docker compose down
```

---

## Docker Architecture

### Services

#### Backend (FastAPI + Agent)
- **Image**: `phonox-backend:latest`
- **Port**: `8000`
- **Environment**:
  - `PYTHONUNBUFFERED=1` (logging)
  - `LLM_PROVIDER=openai` (configurable)
  - `DB_URL=postgresql://user:pass@postgres:5432/phonox`
  - `REDIS_URL=redis://redis:6379`
  - `LOG_LEVEL=INFO`

#### Frontend (React Vite)
- **Image**: `phonox-frontend:latest`
- **Port**: `5173` (dev) / `3000` (prod)
- **Dev mode**: HMR enabled via `VITE_API_URL=http://localhost:8000`

#### PostgreSQL
- **Image**: `postgres:16-alpine`
- **Port**: `5432`
- **Volume**: `postgres_data:/var/lib/postgresql/data`
- **Init**: Migrations auto-run via `docker-entrypoint-initdb.d/`

#### Redis
- **Image**: `redis:7-alpine`
- **Port**: `6379`
- **Volume**: `redis_data:/data`
- **Purpose**: Job queue, caching

---

## Dockerfile Strategy

### Backend Dockerfile

```dockerfile
# Dockerfile
FROM python:3.12-slim as builder

WORKDIR /build
COPY requirements.txt .
RUN pip install --user --no-cache-dir -r requirements.txt

FROM python:3.12-slim

WORKDIR /app
ENV PYTHONUNBUFFERED=1

COPY --from=builder /root/.local /root/.local
ENV PATH=/root/.local/bin:$PATH

COPY . .

CMD ["uvicorn", "backend.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

### Frontend Dockerfile (Dev)

```dockerfile
FROM node:20-alpine

WORKDIR /app
ENV VITE_API_URL=http://localhost:8000

COPY package.json package-lock.json ./
RUN npm install

COPY . .

EXPOSE 5173
CMD ["npm", "run", "dev", "--", "--host"]
```

### Production Frontend

```dockerfile
FROM node:20-alpine as builder
WORKDIR /app
COPY package.json package-lock.json ./
RUN npm install
COPY . .
RUN npm run build

FROM nginx:alpine
COPY --from=builder /app/dist /usr/share/nginx/html
COPY nginx.conf /etc/nginx/nginx.conf
EXPOSE 80
```

---

## Docker Compose (docker-compose.yml)

### Structure

```yaml
version: '3.9'

services:
  postgres:
    image: postgres:16-alpine
    environment:
      POSTGRES_USER: phonox
      POSTGRES_PASSWORD: phonox_dev
      POSTGRES_DB: phonox
    ports:
      - "5432:5432"
    volumes:
      - postgres_data:/var/lib/postgresql/data
      - ./backend/migrations/init.sql:/docker-entrypoint-initdb.d/init.sql
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U phonox"]
      interval: 5s
      timeout: 5s
      retries: 5

  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"
    volumes:
      - redis_data:/data
    healthcheck:
      test: ["CMD", "redis-cli", "ping"]
      interval: 5s
      timeout: 5s
      retries: 5

  backend:
    build:
      context: ./backend
      dockerfile: Dockerfile
    ports:
      - "8000:8000"
    environment:
      DB_URL: postgresql://phonox:phonox_dev@postgres:5432/phonox
      REDIS_URL: redis://redis:6379
      PYTHONUNBUFFERED: "1"
      LOG_LEVEL: INFO
    depends_on:
      postgres:
        condition: service_healthy
      redis:
        condition: service_healthy
    volumes:
      - ./backend:/app
    command: uvicorn backend.main:app --host 0.0.0.0 --port 8000 --reload

  frontend:
    build:
      context: ./frontend
      dockerfile: Dockerfile
    ports:
      - "5173:5173"
    environment:
      VITE_API_URL: http://localhost:8000
    depends_on:
      - backend
    volumes:
      - ./frontend:/app
      - /app/node_modules

volumes:
  postgres_data:
  redis_data:
```

---

## Development Workflow

### Using Docker Desktop

1. **Start Services**
   ```bash
   docker compose up -d
   ```

2. **View Logs**
   ```bash
   # All services
   docker compose logs -f
   
   # Specific service
   docker compose logs -f backend
   ```

3. **Access Services**
   - Frontend: `http://localhost:5173`
   - Backend API: `http://localhost:8000`
   - API Docs: `http://localhost:8000/docs`
   - Postgres: `localhost:5432` (pgAdmin optional)
   - Redis: `localhost:6379`

4. **Stop Services**
   ```bash
   docker compose down
   ```

5. **Rebuild After Changes**
   ```bash
   docker compose up -d --build
   ```

---

## Agent Logging & Monitoring (Local)

### Backend Logging Structure

```python
# backend/logging_config.py
import logging
import json
from datetime import datetime

class AgentLogHandler(logging.Handler):
    """Logs agent state transitions as JSON"""
    
    def emit(self, record):
        log_entry = {
            "timestamp": datetime.utcnow().isoformat(),
            "level": record.levelname,
            "module": record.module,
            "agent_step": record.__dict__.get("agent_step"),
            "state": record.__dict__.get("state"),
            "confidence": record.__dict__.get("confidence"),
            "message": record.getMessage()
        }
        print(json.dumps(log_entry))
```

### Access Agent Logs

```bash
# Watch agent decisions in real-time
docker compose logs -f backend | grep -i "agent\|confidence\|decision"
```

---

## Testing Strategy (Integration)

### Run Tests in Container

```bash
# Unit tests
docker compose exec backend pytest tests/unit -v

# Integration tests (with services)
docker compose exec backend pytest tests/integration -v

# Agent flow tests
docker compose exec backend pytest tests/agent -v
```

---

## CI/CD (GitHub Actions)

### `.github/workflows/test.yml`

```yaml
name: Test & Build

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    services:
      postgres:
        image: postgres:16-alpine
        env:
          POSTGRES_PASSWORD: test
          POSTGRES_DB: phonox_test
        options: >-
          --health-cmd pg_isready
          --health-interval 10s
          --health-timeout 5s
          --health-retries 5
      redis:
        image: redis:7-alpine
        options: >-
          --health-cmd "redis-cli ping"
          --health-interval 10s
          --health-timeout 5s
          --health-retries 5
    
    steps:
      - uses: actions/checkout@v3
      - uses: actions/setup-python@v4
        with:
          python-version: '3.12'
      - run: pip install -r requirements.txt pytest
      - run: pytest tests/ -v
      
  build:
    needs: test
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - uses: docker/setup-buildx-action@v2
      - uses: docker/build-push-action@v4
        with:
          context: ./backend
          push: false
```

---

## Troubleshooting

### Issue: Port already in use
```bash
# Kill process on port
lsof -i :8000 | grep LISTEN | awk '{print $2}' | xargs kill -9

# Or use different port in compose
BACKEND_PORT=8001 docker compose up
```

### Issue: Database won't start
```bash
# Remove volume and restart
docker compose down -v
docker compose up
```

### Issue: Agent logs not appearing
```bash
# Ensure log level
docker compose logs -f backend | head -20

# Check environment
docker compose exec backend env | grep LOG_LEVEL
```

---

## Production Considerations

- Use environment-specific compose files (`docker-compose.prod.yml`)
- Store secrets in `.env.prod` (never in git)
- Use multi-stage builds for smaller images
- Implement health checks for all services
- Enable logging drivers (e.g., awslogs for ECS)
- Use separate DB credentials for prod
- Pin base image versions (no `latest`)

---

## Resources

- [Docker Compose Reference](https://docs.docker.com/compose/compose-file/)
- [FastAPI + Docker](https://fastapi.tiangolo.com/deployment/docker/)
- [PostgreSQL + Docker Best Practices](https://hub.docker.com/_/postgres)
