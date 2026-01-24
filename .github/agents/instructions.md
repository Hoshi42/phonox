# Agent Collaboration Instructions

**Purpose**: Guide for AI Agent Roles (Architect, Agent Engineer, Tool Engineer, Frontend Dev) working on Phonox  
**Updated**: 2026-01-24  
**Scope**: Ensures coordinated, trackable progress across iterations

---

## Overview: The Four Roles

Each role has **clear responsibilities**, **decision authority**, and **communication protocols**.

### 1. System Architect 👨‍💼
- **Owns**: Architecture, design decisions, phase planning
- **Tools**: `architecture.md`, `implementation-plan.md`, tech-stack decisions
- **Key Decisions**: Module boundaries, data flow, deployment strategy
- **Blocks On**: Unclear requirements, scope creep

**Example Decisions**:
- "Let's use Redis for job queues, not Celery"
- "Agent state persists to DB after each node"
- "Image features stay in memory during one request, then saved"

---

### 2. Agent Engineer 🤖
- **Owns**: LangGraph workflows, state transitions, confidence gates
- **Tools**: `agent.md`, state models, node implementations
- **Key Decisions**: Flow logic, error handling, fallback chains
- **Blocks On**: Tool delays, unclear evidence requirements

**Example Decisions**:
- "If image validation fails, return 400 not continue"
- "Confidence gate routes to 3 different paths based on score"
- "Evidence chain persists even if tool fails"

---

### 3. Tool Engineer 🔧
- **Owns**: External tool integrations (Discogs, MusicBrainz, image extraction)
- **Tools**: `tools.md`, individual tool files, mocking strategies
- **Key Decisions**: Tool priorities, retry logic, rate limiting
- **Blocks On**: API changes, missing dependencies

**Example Decisions**:
- "Discogs first (50%), MusicBrainz second (30%), image match last (20%)"
- "Cache Discogs results for 24 hours"
- "If rate limited, queue for retry, don't fail"

---

### 4. Frontend Developer 💻
- **Owns**: PWA, mobile UI, user flows
- **Tools**: React components, environment config, E2E tests
- **Key Decisions**: UX flows, error displays, offline behavior
- **Blocks On**: Backend API changes, design specs

**Example Decisions**:
- "Show confidence score to user only if <0.85"
- "Capture requires 2 images minimum (front + spine)"
- "Auto-refresh GET /vinyl/{id} every 2s while processing"

---

## Collaboration Framework

### Phase Kickoff (Before Each Phase)

**Architect leads, all roles attend**:

1. **Review** previous phase learnings
2. **Discuss** phase goals and acceptance criteria
3. **Identify** blockers and dependencies
4. **Assign** iteration owners (role → person)
5. **Set** weekly sync schedule

**Output**: Phase-specific checklist in `implementation-plan.md`

---

### Per-Iteration Workflow

#### Step 1: Planning (Day 1)
**Owner**: Iteration Lead (usually Architect or primary role)

1. Open `implementation-plan.md`
2. Find next iteration (status: `NOT STARTED`)
3. Read acceptance criteria
4. **Identify blockers**: Does this depend on other iterations?
5. **Assign branches**: Create feature branch `feat/iteration-X.Y`
6. **Update status**: `NOT STARTED` → `IN PROGRESS`
7. **Post in shared channel**: "Starting iteration X.Y, ETA 2-3 days"

```
Iteration 2.2: Discogs Tool
Assigned to: Tool Engineer
Dependencies: 2.1 (Tool Interface) ✅ DONE
Estimate: 2-3 days
Branching strategy: feat/tool-discogs
```

---

#### Step 2: Implementation (Days 2-X)
**Owner**: Role(s) assigned to iteration

1. **Code incrementally**: Commit frequently, test locally
2. **Use test-driven approach**: Write tests first
3. **Document as you go**: Add docstrings, update related `.md` files
4. **In Docker**: `docker compose up -d && docker compose logs -f`

**Daily Check-in** (5 min):
- ✅ What did we build?
- 🚧 What's in progress?
- 🔴 Any blockers?

---

#### Step 3: Testing & Review (Day before completion)
**Owner**: QA focus (can be any role)

1. **Run local tests**:
   ```bash
   docker compose exec backend pytest tests/ -v
   ```

2. **Run integration tests**:
   ```bash
   docker compose up -d
   # Manual or E2E tests
   ```

3. **Check acceptance criteria**: ✅ All passed?

4. **Code review**: 1-2 other roles review PRs

5. **Update documentation**: If specs changed, update `.md` files

---

#### Step 4: Completion & Handoff (Day X)
**Owner**: Iteration Lead

1. **Update `implementation-plan.md`**:
   ```
   Status: COMPLETED
   Actual Duration: 2.5 days (estimated 2-3)
   Notes: Discogs rate limiting required custom retry logic
   Next: 2.3 (MusicBrainz Tool)
   ```

2. **Merge PR** to main branch

3. **Tag release**: `v0.2.2-discogs-tool`

4. **Brief on learnings**:
   - What went smooth?
   - What was harder than expected?
   - Any architectural changes needed?

5. **Celebrate** ✨

---

## Communication Protocols

### Status Updates

**Where**: This document (`implementation-plan.md`)  
**When**: Every Friday EOD + iteration completion  
**What**: Status, timeline, blockers

```
#### Iteration 2.2: Discogs Tool
Status: COMPLETED ✅
Actual Duration: 2 days (est. 2-3)
Notes: Implemented caching for 24h, improved fuzzy matching
Next: 2.3 (MusicBrainz)
```

---

### Blockers & Escalation

**Blocker Definition**: Something that prevents iteration progress

**Examples**:
- Missing dependency (not installed yet)
- API key not available
- Unclear spec from another role
- Infrastructure issue

**Escalation Process**:

```
1. Identify blocker (5 min)
   "Tool Engineer blocked: Discogs API key missing"

2. Notify Architect (5 min)
   Post in shared channel

3. Architect investigates (1-2 hours)
   Gets API key, clarifies spec, or adjusts timeline

4. Resume work
   Update blocker status in implementation-plan.md
```

---

### Code Review Checklist

Before merging any PR:

- [ ] Tests added (unit + integration)
- [ ] Tests pass locally
- [ ] Code follows patterns in `backend/` or `frontend/`
- [ ] Docstrings added to functions
- [ ] Related `.md` files updated (if spec changed)
- [ ] No hardcoded secrets (use `.env`)
- [ ] Type hints present (Python) or TypeScript correct (JS)
- [ ] No console.log or print statements (use logger)
- [ ] Works in Docker (tested via `docker compose`)

---

## Decision-Making Framework

### When to Decide Locally (Role Owner)

- Implementation details (algorithm, data structure)
- Local testing approach
- Code style/naming
- Performance optimizations

**Example**: Agent Engineer decides to use `@dataclass` for Evidence instead of TypedDict.

### When to Escalate (Architect Approval)

- Module boundaries
- API contracts
- Data persistence
- Tool priorities
- Architectural patterns

**Example**: Tool Engineer proposes caching all Discogs results forever → needs Architect approval.

### When to Discuss (All Roles)

- Phase transitions
- New requirements
- Timeline adjustments
- Risk mitigation

**Example**: "Discogs API deprecated, should we switch to another source?"

---

## Iteration Metrics & Tracking

### What to Track

| Metric | Why | How |
|--------|-----|-----|
| **Iteration Duration** | Planning accuracy | Actual vs. planned (in `.md`) |
| **Blocker Count** | Risk visibility | Logged in blocker section |
| **Test Coverage** | Code quality | `pytest --cov` after each iteration |
| **Code Review Time** | Efficiency | Days from PR to merge |
| **Confidence Score Stats** | Agent performance | Histogram of results |

---

### Post-Iteration Review

**Every Friday 4pm** (or iteration end):

**Attendees**: All 4 roles (15 min)

**Agenda**:
1. Completed iterations: demo + retrospective
2. Blockers: what was fixed this week?
3. Metrics: coverage, timeline accuracy
4. Next week: iteration assignments + dependencies
5. Risks: anything that could derail us?

**Retrospective Template**:
- ✅ What went well?
- ❌ What didn't?
- 🔄 What should we change?
- 🎯 Action items for next week?

---

## Tools & Conventions

### Branching Strategy

```
main (always deployable)
  ↓
release/v0.1.0 (release branches)
  ↓
feat/iteration-X.Y (feature branches)
  ↓
developer local branches
```

**Naming**:
- Feature: `feat/iteration-1.2-graph-setup`
- Bug fix: `fix/agent-state-validation`
- Docs: `docs/deployment-guide`

---

### Commit Messages

Format: `[ROLE] iteration-X.Y: <description>`

```
[Agent Engineer] iteration-1.2: Add validate_images node with tests
[Tool Engineer] iteration-2.2: Implement Discogs barcode lookup + caching
[Frontend Dev] iteration-4.2: Add mobile camera capture component
```

---

### File Organization

```
phonox/
├── .github/agents/
│   ├── agent.md (Agent Engineer)
│   ├── architect.md (Architect)
│   ├── tools.md (Tool Engineer)
│   ├── frontend.md (Frontend Dev)
│   ├── implementation-plan.md (Architect - track progress here)
│   └── instructions.md (all roles read)
│
├── backend/
│   ├── agent/
│   │   ├── state.py (Agent Engineer: state models)
│   │   └── graph.py (Agent Engineer: node functions)
│   ├── tools/
│   │   ├── base.py (Tool Engineer)
│   │   ├── discogs.py (Tool Engineer)
│   │   └── musicbrainz.py (Tool Engineer)
│   ├── models.py (Agent + Architect: ORM)
│   └── main.py (Agent Engineer + Architect: FastAPI)
│
└── frontend/
    ├── src/components/
    │   ├── ImageCapture.tsx (Frontend Dev)
    │   ├── ResultDisplay.tsx (Frontend Dev)
    │   └── ReviewForm.tsx (Frontend Dev)
    └── ...
```

---

## Quick Reference: Role Responsibilities

### System Architect
```
Week 1: Phase planning + Docker setup
Week 2: State models + Graph architecture
Week 3: Tool integration + API design
Week 4: Database schema + performance review
```

### Agent Engineer
```
Week 1: State TypedDict definitions
Week 2: LangGraph graph + nodes
Week 3: Node implementations + tests
Week 4: Integration + error handling
```

### Tool Engineer
```
Week 1: Tool interface design
Week 2: Discogs tool (barcode + fuzzy)
Week 3: MusicBrainz + image extraction
Week 4: Tool integration + caching
```

### Frontend Developer
```
Week 1: React Vite setup
Week 2: Image capture component
Week 3: Result display + review UI
Week 4: E2E tests + PWA
```

---

## Success Criteria (Overall Project)

✅ All iterations completed on schedule  
✅ Code coverage ≥85% (unit + integration)  
✅ Agent success rate ≥90%  
✅ All tests passing in CI/CD  
✅ Documentation up-to-date  
✅ Docker deployment working  
✅ PWA functional on mobile  
✅ No critical blockers at phase transitions  

---

## How to Use This Document

1. **Architect**: Update every Friday + iteration start
2. **All Roles**: Read before each phase kickoff
3. **Tool Owners**: Reference responsibilities section
4. **PM/Lead**: Use for status tracking and blocker management

---

## Version History

| Date | Editor | Change |
|------|--------|--------|
| 2026-01-24 | Architect | Initial version created |
| TBD | TBD | Updates during Phase 0 |

