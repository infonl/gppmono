# FLEX+ Migration Project Context

## Current Focus

**LOCAL FIRST Development** - Build fully working docker-compose system before ANY AWS deployment.

## Project Overview

Migrating legacy FLEX+ energy simulation platform (R/Shiny) to modern SaaS using this monorepo.

## Key Files

- `docs/FLEX_PLUS_MIGRATION_PLAN.md` - Full migration specification
- `AGENTS.md` - Coding standards and conventions
- `.claude/scripts/orchestrator.py` - Task definitions (18 tasks, 5 phases)

## Skills (Slash Commands)

| Skill | Model | Purpose |
|-------|-------|---------|
| `/implement` | opus | Autonomous task implementation |
| `/status` | haiku | Progress, graph, checkpoints |
| `/validate` | sonnet | Standards, security, tests |

Each skill has supporting files in `.claude/skills/<name>/`:
- `SKILL.md` - Main skill definition
- `examples.md` - Code examples (implement)
- `checklist.md` - Validation checklist (validate)
- `task-template.md` - Task template (implement)

## Architecture

- **Frontend**: Next.js 16, React 19, TailwindCSS 4, shadcn/ui
- **Backend**: tRPC, Better Auth, Drizzle ORM, PostgreSQL
- **Energy API**: FastAPI with R subprocess for simulations
- **Local**: docker-compose with PostgreSQL, web, energy-api
- **AWS (later)**: EKS with Kubernetes Jobs for simulations

## Orchestrator

```bash
uv run python .claude/scripts/orchestrator.py next      # Get next task(s)
uv run python .claude/scripts/orchestrator.py status    # Progress
uv run python .claude/scripts/orchestrator.py graph     # Dependency graph
uv run python .claude/scripts/orchestrator.py details X # Task info
uv run python .claude/scripts/orchestrator.py complete X
uv run python .claude/scripts/orchestrator.py fail X "msg"
uv run python .claude/scripts/orchestrator.py checkpoint phase-X "msg"
uv run python .claude/scripts/orchestrator.py rollback
uv run python .claude/scripts/orchestrator.py reset
```

## Task Phases

1. **Database Schema** (1.1-1.4) - Drizzle tables for simulations, usage
2. **Energy API** (2.1-2.4) - Pydantic models, R runner, router
3. **Docker R** (3.1-3.3) - R script, Dockerfile, compose
4. **Frontend** (4.1-4.4) - LABELS, UNITS, DEFAULTS constants
5. **Integration** (5.1-5.3) - Full stack test

## Important Patterns

1. **Frontend**: Use LABELS, UNITS, DEFAULTS constants - never hardcode strings
2. **Python**: Type hints, dataclasses, list comprehensions, 120 char lines
3. **TypeScript**: Tabs, double quotes, const arrow functions, `import type`
4. **Files**: Store in PostgreSQL (bytea/jsonb), not S3 for local dev
5. **Simulations**: BackgroundTasks locally, K8s Jobs on AWS
