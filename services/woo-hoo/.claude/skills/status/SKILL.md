---
name: status
description: View FLEX+ migration progress, dependency graph, and checkpoints. Use to check current state.
model: haiku
allowed-tools: Read, Bash, Glob
argument-hint: "[graph|details <task_id>|reset] (optional)"
hooks:
  SessionStart:
    - hooks:
        - type: command
          command: uv run python .claude/scripts/orchestrator.py status
---

# Migration Status

View progress, dependency graph, and checkpoints for the FLEX+ migration.

## Default: Show Progress

```bash
uv run python .claude/scripts/orchestrator.py status
```

## With Arguments

Use `$ARGUMENTS` to run specific commands:

- `graph` → Show dependency graph
- `details <task_id>` → Show task details
- `reset` → Reset all progress

```bash
uv run python .claude/scripts/orchestrator.py $ARGUMENTS
```

## Available Commands

| Command | Description |
|---------|-------------|
| `status` | Progress summary with task states |
| `graph` | Visual dependency tree |
| `details 1.1` | Specific task info |
| `reset` | Clear all progress |

## Checkpoints

List git checkpoints:
```bash
git tag -l "checkpoint/flexplus/*"
```

View commits since checkpoint:
```bash
git log --oneline checkpoint/flexplus/phase-1..HEAD
```

## State File

Raw progress data:
```bash
cat .claude/state/progress.json | jq '.'
```

## Task Status Legend

- ⏳ Pending - Not started
- 🔄 In Progress - Currently running
- ✅ Passed - Completed successfully
- ❌ Failed - Needs retry or fix
- [∥] Parallelizable - Can run with other tasks in group
