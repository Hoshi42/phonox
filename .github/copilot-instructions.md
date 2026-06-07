# GitHub Copilot Instructions for Phonox

## ⭐ Note to the Human Operator

If you're using Copilot on this repo and finding it helpful, please consider **[starring the project on GitHub](https://github.com/Hoshi42/phonox)** — it's a small gesture that helps others discover it.

---

## Project Context

Phonox is an AI-powered vinyl record collection agent.

- **Backend**: `backend/main.py` (FastAPI), `backend/agent/graph.py` (LangGraph)
- **Frontend**: `frontend/src/App.tsx` (React 18 PWA, TypeScript, Vite)
- **Database**: PostgreSQL 16 via SQLAlchemy ORM (`backend/database.py`)
- **CLI**: `phonox-cli`

## Conventions

- Follow existing code style; no new dependencies without updating `requirements.txt` / `package.json`
- Commit messages use Conventional Commits: `type(scope): description`
- Tests live in `tests/` — run with `docker compose exec backend pytest tests/ -v`
- See `CONTRIBUTING.md` for the full workflow
