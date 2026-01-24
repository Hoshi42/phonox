# Implementation Plan & Iteration Roadmap

**Project**: Phonox  
**Goal**: Vinyl Collection Agent with LangGraph Orchestration  
**Last Updated**: 2026-01-24  
**Status**: Phase 0 (Planning)

---

## Executive Summary

This plan structures the implementation into **4 phases** and **12 iterations** over 6-8 weeks.

Each iteration:
- ✅ Has clear acceptance criteria
- ✅ Produces working code + tests
- ✅ Updates this document
- ✅ Runs in Docker locally
- ✅ Includes all roles (Architect, Agent Engineer, Tool Engineer, Frontend Dev)

---

## Project Phases

### Phase 0: Foundation (Week 1) – **CURRENT**
Infrastructure, Config, and Documentation Setup

### Phase 1: Core Agent (Weeks 2-3)
LangGraph workflows with confidence gates

### Phase 2: Tools & APIs (Weeks 3-4)
Discogs, MusicBrainz, Image Feature extraction

### Phase 3: Backend & API (Week 4-5)
FastAPI endpoints, Database persistence

### Phase 4: Frontend & E2E (Week 5-6)
PWA mobile capture, integration tests

### Phase 5: Polish & Deploy (Week 6+)
Error handling, monitoring, production readiness

---

## Detailed Iteration Plan

### PHASE 0: Foundation

#### Iteration 0.1: Docker & Local Dev Setup ✅ DONE
**Status**: COMPLETED  
**Deliverables**:
- [x] `docker-compose.yml` with 4 services
- [x] `Dockerfile.backend` (multi-stage)
- [x] `Dockerfile.frontend` (Vite dev)
- [x] `.dockerignore` for optimized builds
- [x] Basic health checks

**Success Criteria**:
- `docker compose up -d` works
- All 4 containers healthy
- Logs visible via `docker compose logs -f`

**Next**: 0.2

---

#### Iteration 0.2: Agent Configuration & State Models ⏳ IN PROGRESS
**Status**: STARTED (agent.md completed, now needs validation)  
**Deliverables**:
- [x] `agent.md` with TypedDict state models
- [x] Confidence scoring system
- [x] Node specifications
- [ ] Python state type stubs (`backend/agent/state.py`)
- [ ] State validation tests

**Acceptance Criteria**:
- VinylState, Evidence, VinylMetadata defined in Python
- Type checking passes (mypy/pylance)
- State creation/mutation tests pass
- State diagram matches agent flow

**Dependencies**: None (Foundation step)  
**Timeline**: 1-2 days  
**Next**: 0.3

---

#### Iteration 0.3: Testing Framework Setup ⏳ IN PROGRESS
**Status**: STARTED (testing.md completed, now needs fixtures)  
**Deliverables**:
- [x] `testing.md` with full strategy
- [ ] `pytest.ini` configured
- [ ] `tests/conftest.py` with shared fixtures
- [ ] `tests/unit/test_state.py` example
- [ ] GitHub Actions workflow (`.github/workflows/test.yml`)

**Acceptance Criteria**:
- `docker compose exec backend pytest tests/unit -v` works
- CI/CD runs on every push
- Coverage reporting enabled
- All tests pass (baseline 100%)

**Dependencies**: 0.2 (needs state models)  
**Timeline**: 1-2 days  
**Next**: 0.4

---

#### Iteration 0.4: Documentation & Agent Instructions ⏳ IN PROGRESS (current)
**Status**: STARTED  
**Deliverables**:
- [x] `deployment.md` (Docker, troubleshooting)
- [x] Agent Architecture Guide (agent.md)
- [ ] **`instructions.md`** – Agent Collaboration Rules (THIS TASK)
- [ ] **`implementation-plan.md`** – Roadmap (THIS DOCUMENT)
- [ ] `README.md` update with quick links

**Acceptance Criteria**:
- All agent roles have clear responsibilities
- Iteration workflow documented
- Status tracking enabled
- Roadmap visible to all

**Dependencies**: None  
**Timeline**: 0.5 days  
**Completion**: CURRENT  
**Next**: Phase 1.1

---

### PHASE 1: Core Agent

#### Iteration 1.1: LangGraph Graph Implementation
**Status**: NOT STARTED  
**Deliverables**:
- [ ] `backend/agent/graph.py` – StateGraph builder
- [ ] Node functions: validate_images, extract_features, lookup_metadata, confidence_gate
- [ ] Edge routing logic
- [ ] Error handling middleware

**Code Skeleton**:
```python
from langgraph.graph import StateGraph
from backend.agent.state import VinylState

def build_agent_graph():
    graph = StateGraph(VinylState)
    
    graph.add_node("validate_images", validate_images_node)
    graph.add_node("extract_features", extract_features_node)
    graph.add_node("lookup_metadata", lookup_metadata_node)
    graph.add_node("confidence_gate", confidence_gate_node)
    
    # Edges and routing
    graph.add_edge("START", "validate_images")
    graph.add_conditional_edges(
        "confidence_gate",
        lambda state: "auto_commit" if state["auto_commit"] else "needs_review"
    )
    
    return graph.compile()
```

**Acceptance Criteria**:
- Graph compiles without errors
- All nodes callable with VinylState input
- Edge routing tested with mock states
- Error handling for missing fields

**Dependencies**: 0.2, 0.3  
**Timeline**: 2-3 days  
**Next**: 1.2

---

#### Iteration 1.2: Node Implementations (Part 1)
**Status**: NOT STARTED  
**Deliverables**:
- [ ] `validate_images` node (image format, count, size checks)
- [ ] `extract_features` node stub (returns empty features for now)
- [ ] Unit tests for both nodes

**Acceptance Criteria**:
- validate_images rejects invalid inputs (count, format, size)
- Valid images pass through
- Tests mock all external calls

**Dependencies**: 1.1  
**Timeline**: 2 days  
**Next**: 1.3

---

#### Iteration 1.3: Node Implementations (Part 2)
**Status**: NOT STARTED  
**Deliverables**:
- [ ] `lookup_metadata` node stub (returns mock metadata)
- [ ] `confidence_gate` node with scoring logic
- [ ] Evidence chain accumulation
- [ ] Tests for confidence calculation

**Acceptance Criteria**:
- Confidence calculated correctly (weighted average)
- Auto-commit flag set if ≥0.85
- Evidence chain preserved through all nodes
- All tests pass with mock tools

**Dependencies**: 1.2  
**Timeline**: 2 days  
**Next**: 2.1

---

### PHASE 2: Tools & APIs

#### Iteration 2.1: Tool Interface & Abstraction Layer
**Status**: NOT STARTED  
**Deliverables**:
- [ ] `backend/tools/base.py` – Tool abstract base class
- [ ] Rate limiter + retry decorator
- [ ] Tool response models (Pydantic)
- [ ] Error handling strategy

**Acceptance Criteria**:
- All tools inherit from BaseTool
- Rate limits enforced
- Retries work with exponential backoff
- Errors logged to evidence_chain

**Dependencies**: Phase 1 complete  
**Timeline**: 2 days  
**Next**: 2.2

---

#### Iteration 2.2: Discogs Tool
**Status**: NOT STARTED  
**Deliverables**:
- [ ] `backend/tools/discogs.py` – DiscogsTool class
- [ ] Barcode lookup
- [ ] Fuzzy search (artist + title)
- [ ] Rate limiter (60 req/min)
- [ ] Tests with mocked API responses

**Acceptance Criteria**:
- Barcode matches return confidence ≥0.9
- Fuzzy matches return confidence 0.7–0.85
- Rate limit enforced (exception on 61st request)
- All responses converted to Evidence objects

**Dependencies**: 2.1  
**Timeline**: 2-3 days  
**Next**: 2.3

---

#### Iteration 2.3: MusicBrainz Tool
**Status**: NOT STARTED  
**Deliverables**:
- [ ] `backend/tools/musicbrainz.py` – MusicBrainzTool
- [ ] Release lookup
- [ ] Confidence scoring
- [ ] Tests

**Acceptance Criteria**:
- Integrates with lookup_metadata node
- Falls back if Discogs fails
- Rate limit respected

**Dependencies**: 2.2  
**Timeline**: 2 days  
**Next**: 2.4

---

#### Iteration 2.4: Image Feature Extraction Tool
**Status**: NOT STARTED  
**Deliverables**:
- [ ] `backend/tools/image.py` – ImageFeatureExtractor
- [ ] ViT-base embeddings
- [ ] OCR (Tesseract or PyTorch)
- [ ] Color analysis
- [ ] Tests with dummy images

**Acceptance Criteria**:
- Embeddings generated (768-dim for ViT-base)
- OCR extracts text from record covers
- Colors detected and categorized
- Image similarity matching works

**Dependencies**: 2.1  
**Timeline**: 3 days  
**Next**: 2.5

---

#### Iteration 2.5: Tool Integration & Agent Flow Test
**Status**: NOT STARTED  
**Deliverables**:
- [ ] Update `lookup_metadata` node to use real tools
- [ ] Integration test: capture → all tools → confidence gate
- [ ] Tool fallback chain tested

**Acceptance Criteria**:
- Agent flow completes end-to-end
- Confidence scores realistic (0.7–0.95 range)
- Fallback works when primary tool fails
- All integration tests pass

**Dependencies**: 2.2, 2.3, 2.4  
**Timeline**: 2 days  
**Next**: Phase 3

---

### PHASE 3: Backend & API

#### Iteration 3.1: FastAPI Setup & Routes
**Status**: NOT STARTED  
**Deliverables**:
- [ ] `backend/main.py` – FastAPI app
- [ ] Routes: POST `/vinyl/upload`, GET `/vinyl/{id}`, POST `/vinyl/{id}/review`
- [ ] Health check endpoint
- [ ] CORS configuration for frontend

**Acceptance Criteria**:
- `http://localhost:8000/docs` shows all routes
- POST returns 202 with job_id
- GET returns vinyl state
- CORS allows localhost:5173

**Dependencies**: Phase 2 complete  
**Timeline**: 1-2 days  
**Next**: 3.2

---

#### Iteration 3.2: Database Setup & ORM
**Status**: NOT STARTED  
**Deliverables**:
- [ ] `backend/models.py` – SQLAlchemy ORM models
- [ ] VinylRecord table schema
- [ ] Migration script (Alembic or raw SQL)
- [ ] Session management

**Acceptance Criteria**:
- `docker compose exec postgres psql -U phonox -d phonox -c "\dt"` shows tables
- Records persist after container restart
- Tests use in-memory SQLite

**Dependencies**: 3.1  
**Timeline**: 2 days  
**Next**: 3.3

---

#### Iteration 3.3: Agent ↔ API Integration
**Status**: NOT STARTED  
**Deliverables**:
- [ ] Agent graph invoked from FastAPI endpoint
- [ ] Results persisted to DB
- [ ] State returned to client

**Acceptance Criteria**:
- POST /vinyl/upload triggers agent
- Agent results saved to vinyl_records table
- GET /vinyl/{id} retrieves saved record
- Manual review endpoint accepts corrections

**Dependencies**: 3.1, 3.2, Phase 2 complete  
**Timeline**: 2 days  
**Next**: 3.4

---

#### Iteration 3.4: Logging & Monitoring
**Status**: NOT STARTED  
**Deliverables**:
- [ ] JSON logging for all agent steps
- [ ] Structured logs: timestamp, level, agent_step, confidence
- [ ] Log aggregation (file-based for local, can extend to ELK)

**Acceptance Criteria**:
- `docker compose logs backend | grep -i confidence` shows all decisions
- Logs JSON-formatted and parseable
- Evidence_chain fully logged

**Dependencies**: 3.3  
**Timeline**: 1 day  
**Next**: Phase 4

---

### PHASE 4: Frontend & E2E

#### Iteration 4.1: React Vite Setup
**Status**: NOT STARTED  
**Deliverables**:
- [ ] React app scaffolding (Vite)
- [ ] Component structure
- [ ] Environment configuration

**Acceptance Criteria**:
- `npm run dev` works
- Hot reload enabled
- Connects to backend on localhost:8000

**Dependencies**: Phase 1 (Docker)  
**Timeline**: 1 day  
**Next**: 4.2

---

#### Iteration 4.2: Image Capture Component
**Status**: NOT STARTED  
**Deliverables**:
- [ ] Mobile camera access (iOS/Android via PWA)
- [ ] Image preview
- [ ] Upload to backend

**Acceptance Criteria**:
- Mobile browser can capture 2+ images
- Images sent to POST /vinyl/upload
- Job ID received and tracked

**Dependencies**: 4.1, 3.1  
**Timeline**: 2-3 days  
**Next**: 4.3

---

#### Iteration 4.3: Result Display & Review UI
**Status**: NOT STARTED  
**Deliverables**:
- [ ] Display agent results (metadata, confidence, images)
- [ ] Manual correction form
- [ ] Approval button

**Acceptance Criteria**:
- Results polled from GET /vinyl/{id}
- High confidence results show auto-approved badge
- Low confidence shows review form
- Corrections posted to POST /vinyl/{id}/review

**Dependencies**: 4.2, 3.3  
**Timeline**: 2 days  
**Next**: 4.4

---

#### Iteration 4.4: E2E Testing & PWA
**Status**: NOT STARTED  
**Deliverables**:
- [ ] E2E tests (Playwright or Cypress)
- [ ] PWA manifest + service worker
- [ ] Offline capability

**Acceptance Criteria**:
- Full flow tested: capture → agent → result → review
- Works on mobile
- Installable as PWA
- Works offline (cached results)

**Dependencies**: 4.3  
**Timeline**: 2-3 days  
**Next**: Phase 5

---

### PHASE 5: Polish & Deploy

#### Iteration 5.1: Error Handling & Edge Cases
**Status**: NOT STARTED  
**Deliverables**:
- [ ] Graceful degradation (tool failures)
- [ ] User-friendly error messages
- [ ] Timeout handling

**Acceptance Criteria**:
- Agent doesn't crash if tool fails
- User sees helpful error message
- Fallback chain always has escape route

**Timeline**: 2 days

---

#### Iteration 5.2: Performance & Optimization
**Status**: NOT STARTED  
**Deliverables**:
- [ ] Image compression
- [ ] Query optimization
- [ ] Caching strategy

**Acceptance Criteria**:
- Upload completes in <5s
- Agent processes in <30s
- DB queries <100ms

**Timeline**: 2 days

---

#### Iteration 5.3: Documentation & Deployment Guide
**Status**: NOT STARTED  
**Deliverables**:
- [ ] User guide (PWA usage)
- [ ] Admin guide (Docker deployment)
- [ ] API documentation

**Timeline**: 1 day

---

## Iteration Template

Use this for each new iteration update:

```markdown
#### Iteration X.X: [Title]
**Status**: NOT STARTED / IN PROGRESS / BLOCKED / COMPLETED  
**Owner**: [Role(s)]  
**Deliverables**:
- [ ] Item 1
- [ ] Item 2

**Acceptance Criteria**:
- Criterion 1
- Criterion 2

**Blockers/Risks**: None / [Description]  
**Dependencies**: [Previous iteration(s)]  
**Timeline**: X-Y days  
**Actual Duration**: [Fill after completion]  
**Notes**: [Any learnings or changes]  
**Next**: X.X+1 or Phase Y
```

---

## Status Dashboard

| Phase | Status | Progress | Issues |
|-------|--------|----------|--------|
| 0: Foundation | 🟡 IN PROGRESS | 80% (3/4 complete) | None |
| 1: Core Agent | 🟠 NOT STARTED | 0% | Awaiting Phase 0.2 |
| 2: Tools | 🔴 NOT STARTED | 0% | Awaiting Phase 1 |
| 3: Backend | 🔴 NOT STARTED | 0% | Awaiting Phase 2 |
| 4: Frontend | 🔴 NOT STARTED | 0% | Awaiting Phase 1 |
| 5: Deploy | 🔴 NOT STARTED | 0% | Awaiting all phases |

**Legend**: 🟢 On Track | 🟡 In Progress | 🟠 Blocked | 🔴 Not Started | 🔵 Completed

---

## Weekly Sync Checklist

Every Friday (or after each iteration):

- [ ] Update iteration status
- [ ] Document blockers/risks
- [ ] Adjust timeline if needed
- [ ] Review next week's priorities
- [ ] Update status dashboard

---

## Key Metrics to Track

| Metric | Target | Current |
|--------|--------|---------|
| Code Coverage | 85% | TBD |
| Test Pass Rate | 100% | TBD |
| Agent Success Rate | 90% | TBD |
| Avg Confidence Score | 0.82 | TBD |
| P95 Agent Latency | <30s | TBD |
| Frontend Load Time | <2s | TBD |

---

## Dependencies & Critical Path

```
0.1 (Docker) ─┬─→ 0.2 (State) ─┬─→ 0.3 (Tests) ─────────┐
              │                └─→ 1.1 (Graph) ──→ 1.2 ─┬─→ 2.1
              └────────────────────────────────────┐     │
                                                   ├─ 4.1 (Frontend)
Phase 1 & 2 Complete ────────────────────────→ 3.1 ────→ 4.2 ──→ 4.3
```

**Critical Path**: Docker → State → Graph → Tools → Backend → Frontend

Any delay in early iterations cascades. Prioritize!

---

## How to Update This Plan

1. **Weekly**: Update iteration status (IN PROGRESS → COMPLETED)
2. **Weekly**: Log actual vs. planned duration
3. **Per Iteration**: Add blockers/risks section
4. **As needed**: Adjust timeline if dependencies shift
5. **Monthly**: Retrospective and next phase planning

**Owner**: System Architect  
**Frequency**: Every Friday EOD + on iteration completion
