# Tech Stack Instructions (Copilot Guidance)

## Backend
- Python 3.12
- FastAPI
- Pydantic v2
- LangGraph (Agent orchestration)
- PostgreSQL (future)
- Redis / Queue (future)
- Object Storage (S3 / MinIO)

## Frontend
- React (Vite)
- PWA (Service Worker)
- Mobile-first
- No native SDKs

## Agent System
- LangGraph StateGraph
- Tool-first architecture
- No business logic in prompts
- Evidence + Confidence mandatory

## Coding Principles
- Deterministic agent steps
- Typed state (TypedDict / Pydantic)
- Idempotent jobs
- Clear separation:
  - Tools = IO
  - Graph = Orchestration
  - Backend = Persistence

## Forbidden
- Hidden logic in prompts
- Direct scraping without tool abstraction
- Auto-commit without confidence gate
