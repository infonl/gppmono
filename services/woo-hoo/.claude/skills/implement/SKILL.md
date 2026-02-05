---
name: implement
description: Autonomous FLEX+ migration task implementation. Use to continue building the local docker stack.
model: opus
allowed-tools: Read, Write, Edit, Bash, Glob, Grep, Task
context: fork
agent: general-purpose
argument-hint: "[task_id] (optional - auto-detects next task)"
hooks:
  SessionStart:
    - hooks:
        - type: command
          command: uv run python .claude/scripts/orchestrator.py next
  PostToolUse:
    - matcher: "Write|Edit"
      hooks:
        - type: command
          command: uv run python .claude/scripts/orchestrator.py status
---

# FLEX+ Migration Implementation

You are implementing the FLEX+ migration. Follow this workflow:

## Step 1: Get Next Task

```bash
uv run python .claude/scripts/orchestrator.py next
```

**Responses:**
- `PARALLEL:1.1 1.2` → Implement all listed tasks (can run together)
- `SEQUENTIAL:1.1` → Implement single task
- `COMPLETE` → All done, run `/validate`
- `BLOCKED` → Check `/status` for failures
- `ROLLBACK_NEEDED:N` → Run rollback first

## Step 2: Get Task Details

If argument provided, use `$ARGUMENTS`. Otherwise use task from step 1.

```bash
uv run python .claude/scripts/orchestrator.py details <task_id>
```

## Step 3: Read Full Specification

Read `docs/FLEX_PLUS_MIGRATION_PLAN.md` for detailed requirements.
Read `AGENTS.md` for coding standards.

## Step 4: Implement

Create/modify the files specified in task details.

**Frontend Rules:**
- Use LABELS constant for UI text
- Use UNITS constant for unit display
- Use DEFAULTS constant for default values
- Never hardcode strings

**Python Rules:**
- Type hints on all functions
- Dataclasses over classes
- List comprehensions over loops
- 120 char line length

## Step 5: Verify

Run the verification command from task details.

## Step 6: Mark Complete

```bash
uv run python .claude/scripts/orchestrator.py complete <task_id>
```

If response includes `CHECKPOINT:phase-X`:
```bash
uv run python .claude/scripts/orchestrator.py checkpoint phase-X "Phase X complete"
```

## Step 7: Continue or Report

Output status in this format for loop compatibility:

```
TASK: <task_id>
MODE: PARALLEL|SEQUENTIAL
STATUS: PASSED|FAILED
CHECKPOINT: <phase>|NONE
NEXT: <next_task>|COMPLETE|BLOCKED|ROLLBACK
ERROR: <message if failed>
```

Then continue with Step 1 unless COMPLETE.
