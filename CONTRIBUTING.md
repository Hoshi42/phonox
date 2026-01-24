# Contributing to Phonox

Welcome! This document explains how to contribute to Phonox using our Git-based workflow.

---

## Git Workflow Overview

```
main branch (always deployable)
    ↓ (from PR)
feature branches: feat/iteration-X.Y
    ↓ (local work)
developer's local machine
```

**Key Principle**: Every commit should leave the code in a working state. Use meaningful commit messages.

---

## Setting Up Your Local Repository

```bash
# Clone the repository
git clone <repo-url>
cd phonox

# Verify git config
git config user.name "Your Name"
git config user.email "your.email@example.com"

# Start Docker for local testing
docker compose up -d

# Verify setup
docker compose logs -f
```

---

## Workflow: From Iteration to Merge

### Step 1: Prepare for Your Iteration

```bash
# Update main branch
git checkout main (or master)
git pull origin main

# Read the implementation plan
cat .github/agents/implementation-plan.md
```

**Check**:
- Which iteration is `NOT STARTED`?
- What are dependencies?
- Any blockers?

### Step 2: Create Feature Branch

```bash
# Branch naming: feat/iteration-X.Y-description
git checkout -b feat/iteration-1.2-core-agent-setup

# Verify branch
git branch
```

**Pattern**:
- `feat/iteration-X.Y-<short-description>`
- `fix/iteration-X.Y-<issue>`
- `docs/iteration-X.Y-<topic>`

### Step 3: Make Changes

Work incrementally:

```bash
# Edit files, test locally
docker compose up -d
docker compose exec backend pytest tests/ -v

# Add changes
git add <file>
git status  # Verify

# Commit frequently (not just at the end!)
git commit -m "[Agent Engineer] iteration-1.2: Add VinylState TypedDict"
```

**Commit Message Format**:
```
[ROLE] iteration-X.Y: <description>

- Detailed explanation if needed
- Links to related docs/issues
```

**Examples**:
```
[Agent Engineer] iteration-1.2: Add VinylState and Evidence TypedDict definitions
[Tool Engineer] iteration-2.2: Implement Discogs barcode lookup with rate limiting
[Frontend Dev] iteration-4.2: Add mobile camera capture component
```

### Step 4: Sync with Main (Regular)

Stay up-to-date during development:

```bash
# Fetch latest
git fetch origin

# Rebase on main (keep history clean)
git rebase origin/main

# If conflicts: resolve them, then
git add .
git rebase --continue
```

### Step 5: Push and Create PR

```bash
# Push branch
git push -u origin feat/iteration-1.2-core-agent-setup

# Create PR on GitHub/GitLab
# - Title: [Iteration 1.2] Core Agent Setup
# - Description: See implementation-plan.md → Iteration 1.2
# - Link acceptance criteria
```

**PR Checklist**:
- [ ] Branch updated with main
- [ ] Tests pass locally (`docker compose exec backend pytest tests/ -v`)
- [ ] All acceptance criteria met
- [ ] Commit messages are clear and follow format
- [ ] No secrets or hardcoded values
- [ ] Documentation updated

### Step 6: Code Review

Others review your PR:

```
Reviewer checks:
✅ Acceptance criteria met
✅ Tests passing
✅ No hardcoded secrets
✅ Code follows patterns
✅ Documentation updated
✅ No debugging logs left
```

**Address feedback**:

```bash
# Make changes based on review
git add .
git commit -m "[Agent Engineer] iteration-1.2: Address code review feedback"
git push origin feat/iteration-1.2-core-agent-setup
```

### Step 7: Merge to Main

After approval:

```bash
# Merge via GitHub/GitLab UI (prefer "Squash and merge" for cleaner history)
# Or locally:
git checkout main
git pull origin main
git merge feat/iteration-1.2-core-agent-setup
git push origin main
```

**Clean up**:

```bash
# Delete local branch
git branch -d feat/iteration-1.2-core-agent-setup

# Delete remote branch
git push origin --delete feat/iteration-1.2-core-agent-setup
```

### Step 8: Update Implementation Plan

```bash
# Now update .github/agents/implementation-plan.md
# Set iteration status to COMPLETED
# Log actual duration + learnings
# Push to main

git checkout main
git pull origin main
git checkout -b docs/update-implementation-plan
# Edit .github/agents/implementation-plan.md
git add .
git commit -m "[Architect] update implementation-plan: Mark iteration 1.2 complete"
git push origin docs/update-implementation-plan
# Create PR and merge
```

---

## Commit Message Best Practices

### Format
```
[ROLE] iteration-X.Y: <imperative action> <what>

<optional detailed explanation>

Co-authored-by: Agent Name <agent@phonox.local>
```

### Role Tags
- `[Agent Engineer]` – LangGraph, state, nodes
- `[Tool Engineer]` – API integration, tools
- `[System Architect]` – Architecture, design
- `[Frontend Dev]` – UI, React components

### Examples

✅ **Good**:
```
[Agent Engineer] iteration-1.2: Implement confidence_gate node with tests

- Weighted confidence calculation per agent.md specs
- Routes to auto_commit (≥0.85) or needs_review (<0.85)
- All edge cases tested in test_confidence_gate.py
- Evidence chain persisted through state
```

❌ **Bad**:
```
fix stuff
updated code
work in progress
```

---

## Testing Before Push

**Always test before pushing**:

```bash
# Local testing
docker compose up -d

# Unit tests
docker compose exec backend pytest tests/unit -v

# Integration tests
docker compose exec backend pytest tests/integration -v

# All tests with coverage
docker compose exec backend pytest tests/ --cov=backend --cov-report=term

# Type checking
docker compose exec backend mypy backend/ --ignore-missing-imports
```

**Frontend** (if applicable):
```bash
cd frontend
npm install
npm run dev  # Check HMR works
npm run lint
npm run test  # if tests exist
```

---

## Fixing Mistakes

### Undo Last Commit (Not Pushed)
```bash
git revert HEAD
# or
git reset --soft HEAD~1  # Keep changes
git reset --hard HEAD~1  # Discard changes
```

### Undo Pushed Commit
```bash
# Create new commit that undoes the previous
git revert <commit-hash>
git push origin <branch>
```

### Fix Last Commit Message
```bash
git commit --amend -m "New message"
git push origin <branch> --force-with-lease  # Use with caution!
```

### Fix Merge Conflicts
```bash
# During rebase:
# 1. Resolve conflicts in files
# 2. Mark resolved
git add <resolved-file>
git rebase --continue

# Or abort and try again
git rebase --abort
```

---

## Branching Strategy

### Branches We Use

| Branch | Purpose | Creates PR to |
|--------|---------|---------------|
| `main` | Production-ready | Never (integration point) |
| `develop` | Development base | `main` (when ready to release) |
| `feat/*` | Feature work | `develop` (or `main` if hotfix) |
| `fix/*` | Bug fixes | `develop` |
| `docs/*` | Documentation | `main` |

### Example Workflow

```
main (v1.0.0)
  ↓
develop (integration branch)
  ↓
feat/iteration-1.1-state-setup (your work)
feat/iteration-1.2-graph-implementation (colleague's work)
feat/iteration-2.1-tool-interface (other colleague)
  ↓
All merged to develop → create PR to main for release
```

---

## Handling Multiple Agents

### Scenario: Two Agents Working on Related Iterations

**Agent 1** (Agent Engineer) working on iteration 1.2 (Graph Implementation)  
**Agent 2** (Tool Engineer) working on iteration 2.1 (Tool Interface)

**Solution**: Use separate branches, coordinate in implementation-plan.md

```
Agent 1: git checkout -b feat/iteration-1.2-graph
Agent 2: git checkout -b feat/iteration-2.1-tool-interface

# Both push independently
# Review and merge in order of dependencies
```

### Scenario: Dependency Blocker

**Agent 2 blocked**: iteration 2.1 depends on 1.2 (not done yet)

```
# Agent 2 options:
# 1. Branch from Agent 1's branch (rebase on main later)
git checkout feat/iteration-1.2-graph
git checkout -b feat/iteration-2.1-tool-interface

# 2. Wait for Agent 1 to merge, then start
# (Check implementation-plan.md for dependencies)

# 3. Flag blocker in implementation-plan.md:
# Blockers/Risks: "Awaiting iteration 1.2 merge"
```

---

## Emergency: Rolling Back a Merge

If something breaks in main after merge:

```bash
# Option 1: Revert the commit
git revert <merge-commit-hash>
git push origin main

# Option 2: Reset (only if not pushed to remote yet)
git reset --hard HEAD~1
```

**Always inform the team!** Update implementation-plan.md with incident notes.

---

## Tips & Tricks

### View Uncommitted Changes
```bash
git diff                    # Unstaged changes
git diff --staged           # Staged changes
git status                  # Overview
```

### See Who Changed What
```bash
git blame backend/agent/state.py  # Shows commit per line
git log -p backend/agent/state.py # Full history with diffs
```

### Find a Bug (Git Bisect)
```bash
git bisect start
git bisect bad HEAD       # Current is broken
git bisect good <commit>  # Known good commit
# Git will check out commits in between
# Test each: git bisect good/bad
# When found: git bisect reset
```

### Stash Work in Progress
```bash
git stash                  # Save work temporarily
git checkout main
# do something else
git checkout feat/iteration-1.2
git stash pop              # Restore work
```

---

## Continuous Integration

After every push, GitHub Actions runs:

1. ✅ Tests (pytest with coverage)
2. ✅ Type checks (mypy)
3. ✅ Linting (ruff)
4. ✅ Security scan (bandit)
5. ✅ Docker build check

**View results**: GitHub PR page → Checks tab

If CI fails:
```bash
# Download logs, fix locally, push again
git add .
git commit -m "[Agent Engineer] iteration-1.2: Fix CI failures"
git push origin feat/iteration-1.2-core-agent-setup
```

---

## Questions?

1. **Git syntax**: `git --help <command>`
2. **Workflow unclear**: Read this document again + implementation-plan.md
3. **Blocked**: Post blocker in implementation-plan.md, assign to Architect
4. **Merge conflict**: Ask for help in team chat

---

## Summary

```bash
# Typical iteration workflow:
git checkout main && git pull                          # Start fresh
git checkout -b feat/iteration-1.2-my-task            # Create branch
# Edit files, test locally in Docker
docker compose exec backend pytest tests/ -v           # Test
git add . && git commit -m "[Role] iteration-1.2: msg" # Commit
git push -u origin feat/iteration-1.2-my-task         # Push
# Create PR on GitHub/GitLab
# Code review & feedback
git add . && git commit -m "Address review feedback"   # Iterate
# PR approved & merged
git checkout main && git pull                          # Back to main
# Update implementation-plan.md and commit
```

**Key Takeaway**: Commit often, test locally, push clean code, merge after review.
