# Pre-Commit Validation Checklist

Use this checklist before committing changes.

## Code Quality

- [ ] `bun run check-types` passes
- [ ] `bun run check` passes (Biome lint)
- [ ] `cd apps/energy-api && uv run ruff check` passes

## Security

- [ ] No hardcoded API keys or secrets
- [ ] No hardcoded URLs (use environment variables)
- [ ] No exposed credentials in code
- [ ] Sensitive files not committed (.env, credentials.json)

## Frontend Standards

- [ ] UI strings use LABELS constant
- [ ] Units use UNITS constant
- [ ] Default values use DEFAULTS constant
- [ ] No inline hardcoded text in components

## Python Standards

- [ ] All functions have type hints
- [ ] Using dataclasses where appropriate
- [ ] List comprehensions instead of loops where possible
- [ ] Line length ≤ 120 characters

## TypeScript Standards

- [ ] Tabs for indentation
- [ ] Double quotes for strings
- [ ] Const arrow functions for components
- [ ] Type imports use `import type`

## Docker

- [ ] `docker compose config --quiet` validates
- [ ] Services start: `docker compose up -d`
- [ ] Health checks pass

## Tests

- [ ] `bun test` passes
- [ ] `cd apps/energy-api && uv run pytest` passes

## Final

- [ ] All orchestrator tasks verified
- [ ] Checkpoint created if phase complete
