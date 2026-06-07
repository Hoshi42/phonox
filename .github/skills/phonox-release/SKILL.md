---
name: phonox-release
description: "Update Phonox project docs and cut a release commit. Use when: finishing a feature or fix in phonox; user says 'update docs', 'update changelog', 'commit and push'; after code changes need CHANGELOG, README, or docs updated before pushing. Handles CHANGELOG.md, backend/README.md, docs/ user-guide and API docs, then stages all changed files, commits with a conventional-commit message, and pushes to remote."
argument-hint: "Optional: short description of what changed (used as commit message body)"
---

# Phonox Release Skill

Keeps `CHANGELOG.md`, `backend/README.md`, and `docs/` in sync with code changes, then commits and pushes to remote.

## When to Use

- After any feature, fix, or refactor in the phonox workspace
- When the user says "update docs / changelog / README"
- Before or after a PR — to keep history clean and readable
- Any time a commit + push is requested without explicit commit message

## Files to Update

| File | What to update |
|------|----------------|
| `CHANGELOG.md` | Prepend new `## [x.y.z] - YYYY-MM-DD - <title>` block under `### Added / Changed / Fixed` |
| `backend/README.md` | Update API endpoint schemas, tool tables, environment variables |
| `docs/user-guide/chat.md` | Update chat feature descriptions, example tables |
| `docs/api/endpoints.md` | Update request/response examples if API shape changed |
| `docs/architecture/` | Update if agent graph, tool list, or data flow changed |

## Versioning Convention

Phonox uses `MAJOR.MINOR.PATCH`:
- **PATCH** — bug fixes, prompt/copy tweaks, badge fixes
- **MINOR** — new tools, new API fields, new UI features
- **MAJOR** — breaking API changes, DB migrations, full rewrites

Determine the current version from the top entry in `CHANGELOG.md`.

## Procedure

### 1. Identify changes

Read `git diff --stat` (or `git status`) to see which files changed since the last commit.

### 2. Determine new version

Read the current top version from `CHANGELOG.md` and increment appropriately.

### 3. Update CHANGELOG.md

Prepend a new entry **above** the previous top entry:

```markdown
## [x.y.z] - YYYY-MM-DD - <one-line title>

### Added / Changed / Fixed
- **`symbol`** (`path/to/file`) — description of change
```

Use today's date (`_now_str()` format: `YYYY-MM-DD`). Keep entries factual and concise.

### 4. Update backend/README.md

- API endpoint response schemas (especially new fields)
- Chat agent tool table if tools were added/renamed
- Environment variable table if new env vars were introduced

### 5. Update docs/ (only if user-facing behavior changed)

- `docs/user-guide/chat.md` — new chat capabilities, example queries
- `docs/api/endpoints.md` — request/response examples
- Skip docs updates for internal refactors or prompt-only changes

### 6. Stage, commit, push

```bash
git add CHANGELOG.md backend/README.md docs/<changed-files>
git add <code-files-if-not-already-staged>
git commit -m "<type>(<scope>): <short summary>

<bullet list of what changed>"
git push
```

**Conventional commit types:** `feat` | `fix` | `docs` | `refactor` | `chore`

**Scopes for phonox:** `chat` | `agent` | `api` | `frontend` | `db` | `docker` | `scripts`

### 7. Verify

After push, confirm exit code 0 and show the commit hash + summary to the user.

## Commit Message Template

```
<type>(<scope>): <imperative summary, max 72 chars>

- <what changed and why, bullet per logical change>
- <file: specific change>
- <file: specific change>
```

## What NOT to change

- Do **not** edit `docs/changelog.md` (that is a mkdocs mirror, auto-generated)
- Do **not** bump version in `package.json` or `pyproject.toml` unless explicitly asked
- Do **not** force-push or amend published commits
- Do **not** commit secrets, `.env` files, or build artifacts
