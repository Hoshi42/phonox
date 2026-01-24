# Integration Plan & Increment Completion Strategy

**Project**: Phonox  
**Purpose**: Define how iterations integrate into working increments  
**Created**: 2026-01-24  
**Version**: 1.0

---

## Philosophy: Incremental Development with Working Software

Every iteration delivers **working, testable, integrated software**, not just documentation.

**Key Principle**: 
> "At the end of each iteration, the codebase is in a working state that can be (a) tested locally, (b) reviewed, and (c) deployed or merged without breaking existing functionality."

---

## What Makes an Iteration "Complete"?

### ✅ Checklist for Iteration Completion

**Code**:
- [ ] All code committed to feature branch
- [ ] Follows Python/JS style guide (enforced by linter)
- [ ] No hardcoded values or secrets
- [ ] Type hints present (Python) or TypeScript correct (JS)
- [ ] At least 80% test coverage for new code

**Tests**:
- [ ] Unit tests written (minimum 2 per function)
- [ ] Integration tests pass (if applicable)
- [ ] All tests pass locally: `docker compose exec backend pytest tests/ -v`
- [ ] Coverage report shows >80% for new code

**Documentation**:
- [ ] Function/class docstrings added
- [ ] README updated if public API changed
- [ ] Implementation-plan.md marked COMPLETED with notes
- [ ] Agent role files (.md) updated if patterns changed

**Integration**:
- [ ] Docker build succeeds locally
- [ ] All services start: `docker compose up -d`
- [ ] Logs show no errors/warnings
- [ ] Rollback to previous version works

**Review & Merge**:
- [ ] Code review passed (1+ peer)
- [ ] CI/CD pipeline green (tests, linting, security)
- [ ] PR description links to acceptance criteria
- [ ] Merged to main with clean commit message

---

## Iteration Grouping: "Increments" (Delivery Milestones)

We group iterations into **increments** that are deployable units.

### Increment 0: Foundation (Week 1) – **CURRENT**
**Iterations**: 0.1, 0.2, 0.3, 0.4  
**Deliverable**: Project infrastructure + state models + testing framework  
**What Works**: 
- Docker local development  
- Python type system validated  
- Tests can run automatically  
- Git workflow proven  

**Integration Gate**:
- [ ] `docker compose up -d` starts all services
- [ ] `docker compose exec backend pytest tests/ -v` passes
- [ ] `docker compose exec backend mypy backend/ --ignore-missing-imports` passes
- [ ] All 4 iterations marked COMPLETED
- [ ] No TODOs in code (all WIP done or deferred)

**Deploy Check**: Merge to main, tag as v0.0.0-alpha

---

### Increment 1: Core Agent with Multimodal Vision/Websearch (Weeks 2-3)
**Iterations**: 1.1, 1.2, 1.3  
**Deliverable**: LangGraph workflows with 6-node architecture including multimodal vision and websearch fallback  
**What Works**:
- Agent graph compiles with 6 nodes (validate_images, extract_features, vision_extraction, lookup_metadata, websearch_fallback, confidence_gate)
- All nodes callable with valid state
- State transitions tested
- 4-way confidence calculation verified (discogs 0.45, musicbrainz 0.25, vision 0.20, websearch 0.10)
- Vision extraction (Claude 3 Sonnet) tested with mock API
- Websearch fallback (Tavily API) tested with mock API
- Fallback logic proven (websearch triggers when confidence < 0.75)

**Integration Gate**:
- [ ] Agent graph loads: `from backend.agent.graph import build_agent_graph; g = build_agent_graph()`
- [ ] All 6 nodes pass signature tests (validate_images, extract_features, vision_extraction, lookup_metadata, websearch_fallback, confidence_gate)
- [ ] Integration test: mock end-to-end flow works with all 6 nodes
- [ ] Vision extraction node returns proper metadata dict with 0.20 confidence weight
- [ ] Websearch fallback node triggers correctly (confidence < 0.75)
- [ ] Confidence ranges verified:
  - Minimum (websearch alone): 0.10
  - Single source (vision): 0.20
  - Two sources (vision + musicbrainz): 0.45
  - Three sources (all primary): 0.90
  - Fallback scenario (websearch after failure): 0.75+
  - Perfect match (all sources): 0.95+
- [ ] Evidence sources include all four: "discogs", "musicbrainz", "vision", "websearch"
- [ ] All 3 iterations marked COMPLETED

**Deploy Check**: Merge to main, tag as v0.1.0-alpha

---

### Increment 2: Tools & APIs (Weeks 3-4)
**Iterations**: 2.1, 2.2, 2.3, 2.4, 2.5  
**Deliverable**: Tool integrations (Discogs, MusicBrainz, Image extraction)  
**What Works**:
- Each tool has deterministic mocked tests
- Rate limiting enforced
- Retry logic proven
- Tools integrate with agent graph
- Evidence chain captures all tool responses

**Integration Gate**:
- [ ] Each tool can be imported and tested with mocks
- [ ] Tool suite test: `docker compose exec backend pytest tests/tools/ -v` passes
- [ ] Agent flow test includes all 4 tools
- [ ] Fallback chain tested (primary → secondary → fallback)
- [ ] All 5 iterations marked COMPLETED

**Deploy Check**: Merge to main, tag as v0.2.0-alpha

---

### Increment 3: Backend & API (Weeks 4-5)
**Iterations**: 3.1, 3.2, 3.3, 3.4  
**Deliverable**: FastAPI + Database persistence + Logging  
**What Works**:
- All endpoints callable (return 200/201/202)
- Database persists records across restarts
- Agent integration works end-to-end (upload → process → save)
- JSON logging captures all decisions
- Manual review endpoint accepts corrections

**Integration Gate**:
- [ ] `docker compose up -d` includes PostgreSQL + Redis
- [ ] `curl http://localhost:8000/health` returns 200
- [ ] POST /vinyl/upload returns 202 with job_id
- [ ] GET /vinyl/{id} returns stored record
- [ ] All 4 iterations marked COMPLETED

**Deploy Check**: Merge to main, tag as v0.3.0-alpha

---

### Increment 4: Frontend & E2E (Weeks 5-6)
**Iterations**: 4.1, 4.2, 4.3, 4.4  
**Deliverable**: PWA mobile UI + Integration tests  
**What Works**:
- React app starts in dev mode
- Mobile camera access granted
- Image capture works
- Results displayed with confidence
- Manual review form functional
- E2E flow tested

**Integration Gate**:
- [ ] `npm run dev` works on port 5173
- [ ] Mobile browser can capture images
- [ ] Captured images sent to backend
- [ ] Results poll every 2 seconds
- [ ] High confidence shows "auto-approved" badge
- [ ] All 4 iterations marked COMPLETED

**Deploy Check**: Merge to main, tag as v0.4.0-alpha

---

### Increment 5: Polish & Production (Week 6+)
**Iterations**: 5.1, 5.2, 5.3  
**Deliverable**: Error handling, monitoring, deployment guide  
**What Works**:
- Graceful degradation when tools fail
- User-friendly error messages
- Performance optimized (<30s agent latency)
- Monitoring dashboards
- Production deployment documented

**Integration Gate**:
- [ ] Agent doesn't crash if tool fails
- [ ] Fallback chain always has escape route
- [ ] User sees helpful error messages
- [ ] All 3 iterations marked COMPLETED

**Deploy Check**: Merge to main, tag as v1.0.0-release

---

## Integration Testing: Between Increments

After each increment is complete, run **full integration test**:

```bash
# Start everything
docker compose down -v
docker compose up -d

# Wait for startup
sleep 10

# Verify services
docker compose ps
docker compose logs | grep -i "error"

# Run all tests
docker compose exec backend pytest tests/ -v --cov=backend

# Manual smoke test (if applicable)
curl http://localhost:8000/health
npm test  # if frontend tests exist

# Verify no secrets in commit
git log --all --full-history --oneline

# Tag release
git tag -a v0.X.0-alpha -m "Increment X complete"
git push origin v0.X.0-alpha
```

---

## Dependency Graph: Iterations to Increments

```
Increment 0 (Foundation):
  0.1: Docker Setup ──┐
  0.2: State Models ├─→ Type System Ready
  0.3: Testing ─────┤
  0.4: Git + Docs ──┘
        ↓ (merges to main)
        
Increment 1 (Core Agent):
  1.1: Graph Builder ──┐
  1.2: Nodes Part 1 ──┼─→ Agent Workflows
  1.3: Nodes Part 2 ──┘
        ↓ (merges to main)
        
Increment 2 (Tools):
  2.1: Tool Interface ──┐
  2.2: Discogs ────────┼─→ Tool Suite
  2.3: MusicBrainz ────┤
  2.4: Image Extraction┤
  2.5: Integration ────┘
        ↓ (merges to main)
        
Increment 3 (Backend):
  3.1: FastAPI Setup ──┐
  3.2: Database ──────┼─→ API + Persistence
  3.3: Agent ↔ API ───┤
  3.4: Logging ───────┘
        ↓ (merges to main)
        
Increment 4 (Frontend):
  4.1: React Setup ────┐
  4.2: Capture UI ─────┼─→ PWA Complete
  4.3: Results UI ─────┤
  4.4: E2E Tests ──────┘
        ↓ (merges to main)
        
Increment 5 (Production):
  5.1: Error Handling ─┐
  5.2: Performance ───┼─→ Production Ready
  5.3: Monitoring ────┘
        ↓ (merges to main, tagged as v1.0.0)
```

---

## "Runnable Increment" Definition

### For Backend (Increment 0, 1, 2, 3):

A backend increment is **runnable** if:

```bash
# Setup
docker compose down -v
docker compose up -d

# All services healthy
docker compose ps | grep "healthy"

# All tests pass
docker compose exec backend pytest tests/ -v

# Code quality gates pass
docker compose exec backend mypy backend/ --ignore-missing-imports
docker compose exec backend ruff check backend/

# Critical paths work (no 500 errors)
curl http://localhost:8000/health -w "\nStatus: %{http_code}\n"

# Logging works
docker compose logs backend | grep -i "started"
```

### For Frontend (Increment 4):

A frontend increment is **runnable** if:

```bash
# Setup
cd frontend
npm install
npm run build  # Check production build works

# Dev mode works
npm run dev &
sleep 5

# Can access in browser
curl http://localhost:5173 -I

# No console errors during load
npm run lint
npm test 2>/dev/null || echo "No tests yet (OK for early increments)"

# PWA manifest valid (later)
# Service worker loads (later)
```

### For Full System (Increment 3, 4):

An **end-to-end runnable** system:

```bash
# All containers running
docker compose up -d
docker compose ps | wc -l  # Should be ≥4 healthy services

# Backend health
curl http://localhost:8000/health

# Frontend loads
curl http://localhost:5173 | grep -q "<!DOCTYPE" && echo "OK"

# Database works
docker compose exec postgres psql -U phonox -d phonox -c "SELECT 1"

# No critical errors in logs
docker compose logs | grep -i "error" | wc -l  # Should be <5

# Optional: Run E2E test flow
docker compose exec backend pytest tests/integration/test_full_flow.py -v
```

---

## Version Tagging Strategy

After each increment, tag the main branch:

```
v0.0.0-alpha  (Increment 0: Foundation complete)
v0.1.0-alpha  (Increment 1: Core Agent complete)
v0.2.0-alpha  (Increment 2: Tools complete)
v0.3.0-alpha  (Increment 3: Backend complete)
v0.4.0-alpha  (Increment 4: Frontend complete)
v1.0.0-rc1    (Increment 5: Production polish)
v1.0.0        (Release ready)
```

Each tag marks a point where:
- All increment tests pass
- All code reviewed and merged
- Integration gate cleared
- Rollback possible if needed

---

## Handling Integration Failures

If an integration test fails **after iteration completion**:

1. **Identify the blocker**: Which test failed?
2. **Quick fix** (if <1 hour):
   ```bash
   git checkout -b fix/integration-blocker-X
   # Fix the issue
   git commit -m "[Role] fix: Address integration blocker in iteration X.Y"
   git push origin fix/integration-blocker-X
   # Create PR, review, merge
   ```
3. **If >1 hour**: Mark iteration as "BLOCKED", escalate to Architect

4. **Re-run integration gate**:
   ```bash
   docker compose down -v
   docker compose up -d
   docker compose exec backend pytest tests/ -v
   ```

5. **Retry merge** if fixed

---

## Release Criteria (Each Increment)

Before tagging a release, verify:

| Item | Check | Status |
|------|-------|--------|
| Code | All iterations merged to main | ✅ |
| Tests | 100% passing | ✅ |
| Coverage | ≥80% for new code | ✅ |
| Docs | Updated + linked | ✅ |
| Security | No secrets leaked | ✅ |
| Performance | P95 <100ms (API) or <2s (UI) | ✅ |
| Rollback | Previous version still works | ✅ |

---

## Timeline Summary

| Week | Increment | Iterations | Milestone |
|------|-----------|-----------|-----------|
| 1 | 0 (Foundation) | 0.1–0.4 | Docker + Types + Tests ✅ CURRENT |
| 2 | 1 (Core Agent) | 1.1–1.3 | LangGraph workflows |
| 3 | 2 (Tools) | 2.1–2.5 | API integrations |
| 4 | 3 (Backend) | 3.1–3.4 | FastAPI + Database |
| 5 | 4 (Frontend) | 4.1–4.4 | PWA mobile |
| 6+ | 5 (Production) | 5.1–5.3 | Error handling + monitoring |

---

## What Happens if We're Behind Schedule?

**If Increment N slips**:

1. **Do not skip iterations** – stick to the plan
2. **Reduce scope of next iteration** – drop nice-to-haves
3. **Extend timeline** – honest estimates > crunch mode
4. **Escalate to Architect** – adjust roadmap if needed
5. **Keep main branch green** – never commit broken code

**Example**: If Increment 1 takes 3 weeks instead of 2:
- Don't skip Increment 2
- Instead: Reduce scope of 2.5 (Tool integration)
- Or: Move some of Increment 3 to Week 5

---

## How to Know When We're Ready

✅ **Increment Complete** when:
- All iterations marked DONE in implementation-plan.md
- All PRs merged to main
- Integration gate passed
- Tests 100% passing
- No TODOs left in code
- Release tagged in git

❌ **Increment NOT Complete** if:
- Any iteration still "IN PROGRESS"
- Integration test fails
- Coverage <80%
- Unresolved code review feedback
- Any TODO or FIXME in code (unless next iteration)

---

## Starting Increment 0 Now

**Current Status**: Phase 0.1 DONE, ready for 0.2 & 0.3

**Action Items**:

1. **Agent Engineer** → Start Iteration 0.2:
   ```bash
   git checkout -b feat/iteration-0.2-state-models
   # Implement backend/agent/state.py
   # Add tests/unit/test_state.py
   ```

2. **Someone else** → Start Iteration 0.3 (parallel):
   ```bash
   git checkout -b feat/iteration-0.3-testing-setup
   # Add pytest.ini
   # Add tests/conftest.py
   ```

3. **When both done** → Merge separately, run integration gate

4. **After integration gate passes** → Mark Increment 0 COMPLETE

5. **Tag release**: `git tag -a v0.0.0-alpha -m "Foundation complete"`

---

**Let's go!** 🚀
