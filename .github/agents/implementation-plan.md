# Implementation Plan & Iteration Roadmap

**Project**: Phonox  
**Goal**: Vinyl Collection Agent with LangGraph Orchestration  
**Last Updated**: 2026-01-24  
**Status**: Phase 0 – Ready for Implementation  
**Integration Strategy**: See [`.github/agents/integration-plan.md`](.github/agents/integration-plan.md)

---

## Executive Summary

This plan structures the implementation into **5 increments** and **12 iterations** over 6 weeks.

Each iteration:
- ✅ Has clear acceptance criteria
- ✅ Produces working, testable code
- ✅ Updates this document when COMPLETED
- ✅ Passes Docker integration test locally
- ✅ Has test coverage ≥80%
- ✅ Can be merged to main without breaking builds

**What is a "Working Increment"?** See [integration-plan.md](integration-plan.md#what-makes-an-iteration-complete)

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

#### Iteration 0.2: Agent Configuration & State Models ✅ COMPLETED
**Status**: MERGED & TESTED  
**Owner**: Agent Engineer  
**Deliverables**:
- [x] `agent.md` with TypedDict state models (reference)
- [x] `backend/agent/__init__.py` (empty module)
- [x] `backend/agent/state.py` with TypedDict definitions
- [x] `tests/unit/test_state.py` with validation tests
- [x] Type stubs pass mypy checking

**Code to Implement** (from agent.md):

```python
# backend/agent/state.py
from typing import TypedDict, Optional, List
from datetime import datetime

class Evidence(TypedDict):
    source: str  # "discogs", "musicbrainz", "image"
    confidence: float  # 0.0-1.0
    data: dict  # Tool response
    timestamp: datetime

class VinylMetadata(TypedDict):
    artist: str
    title: str
    year: Optional[int]
    label: str
    catalog_number: Optional[str]
    genres: List[str]
    evidence: List[Evidence]
    overall_confidence: float

class VinylState(TypedDict):
    images: List[str]  # Base64 or paths
    metadata: Optional[VinylMetadata]
    evidence_chain: List[Evidence]
    status: str  # "pending", "processing", "complete", "failed"
    error: Optional[str]
```

**Test Requirements** (in `tests/unit/test_state.py`):
- State creation with valid data
- Type validation (Pydantic or manual)
- State mutation (adding evidence)
- Confidence calculation (weighted average)
- Error cases (invalid state, missing fields)

**Acceptance Criteria** (Working Increment):
- ✅ `backend/agent/state.py` exists with all types
- ✅ `pytest tests/unit/test_state.py -v` passes all tests
- ✅ `mypy backend/agent/state.py --ignore-missing-imports` passes (0 errors)
- ✅ Test coverage ≥95% for state.py
- ✅ Code has docstrings for all TypedDicts
- ✅ `docker compose exec backend pytest tests/unit/test_state.py -v` passes
- ✅ No uncommitted changes, clean git status
- ✅ PR created, code reviewed, ready to merge

**Integration Test**:
```bash
✓ Tests: 21/21 PASSED
✓ Coverage: 100% (38/38 lines)
✓ Type checking: SUCCESS (0 errors)
✓ Git status: CLEAN
✓ Merged to master: DONE
```

**Timeline**: 1-2 days [COMPLETED IN <1 hour]  
**Dependencies**: None  
**Blocker**: None  
**Next**: 0.3 (can run in parallel)  
**Merge**: ✅ Merged to master on 2026-01-24  
**Commit**: fb0fe62

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
| 0: Foundation | 🟡 IN PROGRESS | 100% (4/4 complete) | 0.2 merged ✅ |
| 1: Core Agent | 🟠 NOT STARTED | 0% | Awaiting Phase 1 planning |
| 2: Tools | 🔴 NOT STARTED | 0% | Awaiting Phase 1 |
| 3: Backend | 🔴 NOT STARTED | 0% | Awaiting Phase 2 |
| 4: Frontend | 🔴 NOT STARTED | 0% | Awaiting Phase 1 |
| 5: Deploy | 🔴 NOT STARTED | 0% | Awaiting all phases |

---

## 🚀 Ready to Code: Iteration 0.2 is Open

**Current Status**: Phase 0 Foundation is ready  
**What's Ready**:
- ✅ Git repository with 3 clean commits
- ✅ Docker environment (postgres, redis, backend, frontend)
- ✅ Agent state models defined in agent.md
- ✅ Testing strategy documented
- ✅ GitHub Actions CI/CD configured

**What to Do Now**:

### Option 1: Start Iteration 0.2 (Recommended)
```bash
# Create feature branch
git checkout -b feat/iteration-0.2-state-models

# Create the required files
mkdir -p backend/agent
touch backend/agent/__init__.py
# Edit: backend/agent/state.py (copy from above)
# Edit: tests/unit/test_state.py (create test file)

# Run tests locally
docker compose exec backend pytest tests/unit/test_state.py -v

# Commit when tests pass
git add backend/agent/state.py tests/unit/test_state.py
git commit -m "[Agent Engineer] feat: Implement agent state models (iteration 0.2)"

# Create PR for review
# Merge to main after review
```

### Option 2: Start Iteration 0.3 (Parallel)
If someone else is doing 0.2, you can start 0.3 in parallel:
```bash
git checkout -b feat/iteration-0.3-testing-setup

# Create test config
touch pytest.ini
touch tests/conftest.py
# Add pytest configuration and shared fixtures

# Verify existing tests still work
docker compose exec backend pytest tests/ -v

# Commit and create PR
```

### Integration Gate: Before Merging Iteration 0.2

```bash
# 1. Ensure local state
docker compose down -v
docker compose up -d
sleep 10

# 2. Run all tests
docker compose exec backend pytest tests/ -v --cov=backend/agent

# 3. Check types
docker compose exec backend mypy backend/agent/ --ignore-missing-imports

# 4. Verify logs are clean
docker compose logs backend | grep -i error

# 5. Merge PR to main
# 6. Verify main is still green
```

---

## Notes for Agent Team

**Communication**:
- Update this document when iteration status changes
- Link PRs to iteration number (e.g., "Iteration 0.2")
- Report blockers in daily standup

**Code Quality**:
- All new code must have tests (≥80% coverage)
- All functions must have docstrings
- All types must pass mypy checking
- All commits must reference iteration

**Integration**:
- After each iteration, run the "Integration Gate" test above
- Don't merge if tests fail
- Mark iteration as "COMPLETED" only after merge

**Timeline**:
- Phase 0 (Foundation): Target 5 days, currently 3 days (on track)
- Phase 1 (Agent): Starts after 0.2 complete
- Full system: Target 6 weeks to v1.0.0 release

---

**Let's build Phonox! 🎵**
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
