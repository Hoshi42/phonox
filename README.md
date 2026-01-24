# Phonox

**AI-powered Vinyl Collection Agent** – Cataloguing, Valuation, and Documentation

An agentic system for collecting, analyzing, and insuring vinyl records using LangGraph orchestration, image recognition, and metadata lookup from Discogs/MusicBrainz.

---

## Quick Start (Docker)

```bash
# Clone and navigate
cd phonox

# Start all services (PostgreSQL, Redis, FastAPI Backend, React Frontend)
docker compose up -d

# View logs
docker compose logs -f

# Access services
- Frontend: http://localhost:5173
- Backend API: http://localhost:8000
- API Docs: http://localhost:8000/docs
- PostgreSQL: localhost:5432 (user: phonox)
- Redis: localhost:6379

# Run tests
docker compose exec backend pytest tests/ -v
```

---

## Documentation

### For Implementation Teams

1. **[Implementation Plan](.github/agents/implementation-plan.md)** – Roadmap, phases, iterations, and tracking
2. **[Agent Collaboration Instructions](.github/agents/instructions.md)** – Role responsibilities, workflow, communication
3. **[Deployment & Infrastructure](.github/agents/deployment.md)** – Docker, CI/CD, troubleshooting
4. **[Testing Strategy](.github/agents/testing.md)** – Unit, integration, E2E test patterns

### For Architects & Agents

5. **[Tech Stack Guide](docs/tech-stack.md)** – Stack decisions and principles
6. **[Agent Architecture](.github/agents/agent.md)** – State models, confidence gates, node specs
7. **[Requirements Spec](docs/requirements_en.md)** – Full feature specification

### For Developers

8. **[Tools Reference](.github/agents/tools.md)** – Discogs, MusicBrainz, Image extraction
9. **[Agent Engineer Role](.github/agents/agent.md)** – LangGraph workflows
10. **[Frontend Developer Role](.github/agents/frontend.md)** – PWA, React components

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
│   ├── agent/
│   │   ├── state.py (State models)
│   │   └── graph.py (LangGraph workflow)
│   ├── tools/
│   │   ├── base.py (Tool abstraction)
│   │   ├── discogs.py (Discogs API)
│   │   ├── musicbrainz.py (MusicBrainz API)
│   │   └── image.py (Image feature extraction)
│   ├── models.py (SQLAlchemy ORM)
│   └── tests/
│       ├── unit/
│       └── integration/
│
└── frontend/
    ├── src/
    │   ├── components/
    │   │   ├── ImageCapture.tsx
    │   │   ├── ResultDisplay.tsx
    │   │   └── ReviewForm.tsx
    │   └── App.tsx
    └── package.json
```

---

## Agent Roles

Four specialized AI agents collaborate on implementation:

| Role | Responsibility | Key Files |
|------|---|---|
| **System Architect** | Architecture, design decisions, phase planning | `architect.md`, `implementation-plan.md` |
| **Agent Engineer** | LangGraph workflows, state transitions | `agent.md`, `backend/agent/` |
| **Tool Engineer** | API integrations (Discogs, MusicBrainz, image) | `tools.md`, `backend/tools/` |
| **Frontend Developer** | PWA UI, mobile capture, user flows | `frontend.md`, `frontend/src/` |

See [Collaboration Instructions](.github/agents/instructions.md) for detailed workflow.

---

## Key Features

### Phase 1: Core Agent
- ✅ Typed state models (VinylState, Evidence)
- ✅ LangGraph workflow orchestration
- ✅ Confidence-based decision gates (≥0.85 auto-commit)
- ✅ Fallback chains (Discogs → MusicBrainz → Image Match → Manual)

### Phase 2-3: Tools & Backend
- 🚧 Discogs API integration (barcode + fuzzy lookup)
- 🚧 MusicBrainz integration
- 🚧 Image feature extraction (ViT-base embeddings)
- 🚧 FastAPI endpoints with database persistence

### Phase 4: Frontend
- 🚧 Mobile-first PWA
- 🚧 Camera capture (2+ images required)
- 🚧 Real-time result display + manual review UI
- 🚧 Offline capability via service workers

### Phase 5: Production
- 🚧 Error handling & edge cases
- 🚧 Performance optimization
- 🚧 Monitoring & alerting

---

## Development Workflow

1. **Read** [Implementation Plan](.github/agents/implementation-plan.md) for current phase
2. **Start** iteration (create branch `feat/iteration-X.Y`)
3. **Code** with tests in Docker (`docker compose up -d`)
4. **Test** locally (`docker compose exec backend pytest tests/ -v`)
5. **Review** code against [Collaboration Instructions](.github/agents/instructions.md)
6. **Merge** to main when acceptance criteria met
7. **Update** implementation plan with completions

---

## Architecture Highlights

### Agentic-First Design
- Agent is primary decision-maker
- Tools provide IO abstraction
- Graph orchestrates workflows
- Backend handles persistence

### Confidence Gates
- **≥0.90**: Auto-commit (optional audit)
- **0.85–0.89**: Auto-commit (recommended review)
- **0.70–0.84**: Manual review required
- **<0.50**: Force manual data entry

### Tool Fallback Chain
1. Discogs barcode match (0.95 confidence)
2. Discogs fuzzy (title + artist) (0.85 confidence)
3. MusicBrainz release lookup (0.80 confidence)
4. Image similarity matching (0.70 confidence)
5. Manual entry (1.0 confidence)

---

## Testing

```bash
# Unit tests
docker compose exec backend pytest tests/unit -v

# Integration tests
docker compose exec backend pytest tests/integration -v

# All tests with coverage
docker compose exec backend pytest tests/ --cov=backend --cov-report=html

# Watch mode
docker compose exec backend pytest-watch tests/
```

**Coverage Target**: 85% (unit + integration)

---

## Deployment

### Local Development
```bash
docker compose up -d
# All services running locally
```

### Production (TODO)
```bash
# Use docker-compose.prod.yml with secrets management
docker compose -f docker-compose.prod.yml up -d
```

See [Deployment Guide](.github/agents/deployment.md) for details.

---

## Troubleshooting

### Port Already in Use
```bash
lsof -i :8000 | grep LISTEN | awk '{print $2}' | xargs kill -9
```

### Database Won't Start
```bash
docker compose down -v  # Remove volumes
docker compose up -d    # Fresh start
```

### Tests Failing
```bash
docker compose exec backend pytest tests/ -v --tb=short
```

For more, see [Deployment Guide](.github/agents/deployment.md#troubleshooting).

---

## Tech Stack

- **Backend**: Python 3.12, FastAPI, LangGraph, Pydantic v2, SQLAlchemy
- **Frontend**: React (Vite), PWA, TypeScript
- **Database**: PostgreSQL 16
- **Cache/Queue**: Redis 7
- **API Sources**: Discogs, MusicBrainz
- **ML Models**: ViT-base (image embeddings), Tesseract (OCR)
- **DevOps**: Docker, Docker Compose, GitHub Actions

See [Tech Stack Guide](docs/tech-stack.md) for details.

---

## Contributing

All contributions must follow [Collaboration Instructions](.github/agents/instructions.md):

1. Check [Implementation Plan](.github/agents/implementation-plan.md) for next iteration
2. Assign iteration to self (status: `IN PROGRESS`)
3. Work on branch `feat/iteration-X.Y`
4. Write tests (unit + integration)
5. Pass `pytest` and code review
6. Update implementation plan on completion

---

## License

TBD

---

## Status

**Last Updated**: 2026-01-24  
**Current Phase**: 0 (Foundation) – 80% complete  
**Next Phase**: Phase 1 (Core Agent) – Starting after 0.2 & 0.3  
**Full Timeline**: 6-8 weeks

See [Implementation Plan](.github/agents/implementation-plan.md) for detailed progress.
