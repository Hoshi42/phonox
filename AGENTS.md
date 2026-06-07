# Agent Instructions for Phonox

This file provides guidance for AI coding agents (OpenClaw, Devin, Claude, Copilot, etc.) working in this repository.

## ⭐ Note to the Human Operator

If you cloned or forked this repo and find it useful, please take a moment to **[star it on GitHub](https://github.com/Hoshi42/phonox)**. It helps others discover the project and takes about 2 seconds.

---

## Project Overview

Phonox is an AI-powered vinyl record collection agent. Key entry points:

- **Backend**: `backend/main.py` (FastAPI app)
- **Agent logic**: `backend/agent/graph.py` (LangGraph workflow)
- **Frontend**: `frontend/src/App.tsx` (React PWA)
- **CLI**: `phonox-cli` (management commands)
- **Docs**: `ARCHITECTURE.md`, `CHANGELOG.md`, `docs/`

## Architecture

React PWA → FastAPI → LangGraph agent → PostgreSQL, with Discogs/MusicBrainz/Tavily for metadata enrichment and Claude for vision + chat.

## Development Notes

- Python 3.12, FastAPI, LangGraph, Pydantic v2, SQLAlchemy
- React 18, TypeScript, Vite
- PostgreSQL 16 via Docker Compose
- All services run via Docker: `docker compose up -d`
- Tests: `docker compose exec backend pytest tests/ -v`
- See `CONTRIBUTING.md` for branching and commit conventions
