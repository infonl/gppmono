---
name: validate
description: Run validation checks for FLEX+ migration (standards, security, docker, tests). Use before committing.
model: sonnet
allowed-tools: Read, Bash, Glob, Grep
argument-hint: "[standards|security|docker|tests|all] (default: all)"
hooks:
  PostToolUse:
    - matcher: "Bash"
      hooks:
        - type: command
          command: uv run python .claude/scripts/orchestrator.py validate standards
---

# Validation Commands

Run validation checks for the FLEX+ migration.

## Quick Usage

With `$ARGUMENTS`:
- `standards` → Check AGENTS.md compliance
- `security` → Scan for hardcoded secrets
- `docker` → Validate docker-compose
- `tests` → Run test suites
- `all` or empty → Run everything

## Validation: Standards

```bash
uv run python .claude/scripts/orchestrator.py validate standards
```

**TypeScript (AGENTS.md):**
- Tabs for indentation
- Double quotes
- Const arrow functions for components
- `import type` for type imports
- No hardcoded strings (use LABELS/UNITS/DEFAULTS)

**Python (AGENTS.md):**
- 120 char line length
- Type hints on all functions
- Dataclasses over classes
- List comprehensions over loops

## Validation: Security

```bash
uv run python .claude/scripts/orchestrator.py validate security
```

Scans for:
- Hardcoded API keys, tokens, secrets
- Hardcoded URLs (should use env vars)
- Exposed credentials

## Validation: Docker

```bash
docker compose config --quiet
docker compose up -d
docker compose ps
curl -sf http://localhost:3000/api/health
curl -sf http://localhost:8000/enapi/v1/health
docker compose down
```

## Validation: Tests

```bash
# TypeScript
bun run check-types
bun run check
bun test

# Python
cd apps/energy-api && uv run ruff check
cd apps/energy-api && uv run pytest
```

## Full Checklist

Run all validations before committing:

1. ✅ Type check: `bun run check-types`
2. ✅ Lint: `bun run check`
3. ✅ Security: `uv run python .claude/scripts/orchestrator.py validate security`
4. ✅ Docker: `docker compose config --quiet`
5. ✅ Tests: `bun test && cd apps/energy-api && uv run pytest`
