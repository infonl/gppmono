# Task Implementation Template

Use this template when implementing a task.

## Task: $TASK_ID - $TASK_NAME

### File to Create/Modify
`$FILE_PATH`

### Requirements
$REQUIREMENTS

### Verification Command
```bash
$VERIFY_COMMAND
```

### Dependencies
$DEPENDENCIES

---

## Implementation Checklist

- [ ] Read existing code in target file (if exists)
- [ ] Follow AGENTS.md coding standards
- [ ] Implement required functionality
- [ ] Run verification command
- [ ] Mark task complete

## After Implementation

```bash
# If verification passes:
uv run python .claude/scripts/orchestrator.py complete $TASK_ID

# If verification fails:
uv run python .claude/scripts/orchestrator.py fail $TASK_ID "error message"
```
