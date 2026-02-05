#!/usr/bin/env python3
"""
FLEX+ Migration Orchestrator

Usage: uv run python orchestrator.py <command> [args]

Commands:
    next                    Get next executable task(s)
    status                  Show current progress
    graph                   Show dependency graph
    details <task_id>       Show task details
    complete <task_id>      Mark task as complete
    fail <task_id> <msg>    Mark task as failed
    checkpoint <name> <msg> Create git checkpoint
    rollback [target]       Rollback to checkpoint
    validate <type> [file]  Run validation (standards|security|bash|frontend)
    reset                   Reset all progress
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

# === Configuration ===

PROJECT_DIR = Path(os.environ.get("CLAUDE_PROJECT_DIR", Path.cwd()))
STATE_FILE = PROJECT_DIR / ".claude" / "state" / "progress.json"
MAX_CONSECUTIVE_FAILURES = 3


# === Data Classes ===


@dataclass
class Task:
    """Migration task definition."""

    id: str
    name: str
    phase: str
    file: str | None = None
    dependencies: list[str] = field(default_factory=list)
    parallel_group: str | None = None
    verify: str = ""
    requires_docker: bool = False


@dataclass
class State:
    """Persistent state for migration progress."""

    tasks: dict[str, dict[str, Any]] = field(default_factory=dict)
    checkpoints: dict[str, dict[str, Any]] = field(default_factory=dict)
    consecutive_failures: int = 0
    last_updated: str = ""

    @classmethod
    def load(cls) -> State:
        STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
        if STATE_FILE.exists():
            data = json.loads(STATE_FILE.read_text())
            return cls(**{k: data.get(k, v) for k, v in cls().__dict__.items()})
        return cls()

    def save(self) -> None:
        self.last_updated = datetime.now(timezone.utc).isoformat()
        STATE_FILE.write_text(json.dumps(self.__dict__, indent=2))

    def get_status(self, task_id: str) -> str:
        return self.tasks.get(task_id, {}).get("status", "pending")

    def set_status(self, task_id: str, status: str, message: str = "") -> None:
        self.tasks[task_id] = {
            "status": status,
            "message": message,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
        self.save()


# === Task Definitions (Single Source of Truth) ===

PHASES = {
    "phase-1": {"name": "Database Schema", "tasks": ["1.1", "1.2", "1.3", "1.4"]},
    "phase-2": {"name": "Energy API", "tasks": ["2.1", "2.2", "2.3", "2.4"]},
    "phase-3": {"name": "Docker R Environment", "tasks": ["3.1", "3.2", "3.3"]},
    "phase-4": {"name": "Frontend Constants", "tasks": ["4.1", "4.2", "4.3", "4.4"]},
    "phase-5": {"name": "Integration", "tasks": ["5.1", "5.2", "5.3"]},
}

PARALLEL_GROUPS = {"schema": ["1.1", "1.2"], "constants": ["4.1", "4.2", "4.3"]}

TASKS: dict[str, Task] = {
    # Phase 1: Database Schema
    "1.1": Task(
        "1.1", "Create Simulation Tables Schema", "phase-1",
        "packages/db/src/schema/simulations.ts", [], "schema",
        "bun run check-types 2>&1 | grep -q 'error' && exit 1 || exit 0",
    ),
    "1.2": Task(
        "1.2", "Create Usage Tracking Schema", "phase-1",
        "packages/db/src/schema/usage.ts", [], "schema",
        "bun run check-types 2>&1 | grep -q 'error' && exit 1 || exit 0",
    ),
    "1.3": Task(
        "1.3", "Export Schemas and Generate Migration", "phase-1",
        "packages/db/src/schema/index.ts", ["1.1", "1.2"], None,
        "bun run db:generate && bun run check-types",
    ),
    "1.4": Task(
        "1.4", "Run Migration", "phase-1", None, ["1.3"], None,
        "docker compose exec -T postgres psql -U postgres -d app_db -c '\\dt' | grep -q simulations",
        requires_docker=True,
    ),
    # Phase 2: Energy API
    "2.1": Task(
        "2.1", "Create R Simulator Pydantic Models", "phase-2",
        "apps/energy-api/src/energy_api/models/simulation.py", [], None,
        "cd apps/energy-api && uv run python -c 'from energy_api.models.simulation import SimulationInput'",
    ),
    "2.2": Task(
        "2.2", "Create R Subprocess Runner", "phase-2",
        "apps/energy-api/src/energy_api/services/r_runner.py", ["2.1"], None,
        "cd apps/energy-api && uv run python -c 'from energy_api.services.r_runner import run_simulation'",
    ),
    "2.3": Task(
        "2.3", "Create Simulation Router", "phase-2",
        "apps/energy-api/src/energy_api/api/routers/simulations.py", ["2.1", "2.2"], None,
        "cd apps/energy-api && uv run python -m py_compile src/energy_api/api/routers/simulations.py",
    ),
    "2.4": Task(
        "2.4", "Register Simulation Router", "phase-2",
        "apps/energy-api/src/energy_api/main.py", ["2.3"], None,
        "cd apps/energy-api && uv run python -c 'from energy_api.main import app; "
        "assert any(\"simulation\" in str(r.path) for r in app.routes)'",
    ),
    # Phase 3: Docker R Environment
    "3.1": Task(
        "3.1", "Create R Wrapper Script", "phase-3",
        "apps/energy-api/r_scripts/run_simulation.R", [], None,
        "test -f apps/energy-api/r_scripts/run_simulation.R",
    ),
    "3.2": Task(
        "3.2", "Create Combined Dockerfile", "phase-3",
        "apps/energy-api/Dockerfile.dev", ["3.1"], None,
        "docker build -f apps/energy-api/Dockerfile.dev -t energy-api-dev apps/energy-api",
        requires_docker=True,
    ),
    "3.3": Task(
        "3.3", "Update Docker Compose", "phase-3",
        "docker-compose.yml", ["3.2"], None,
        "docker compose config --quiet",
        requires_docker=True,
    ),
    # Phase 4: Frontend Constants
    "4.1": Task(
        "4.1", "Create Labels Constant", "phase-4",
        "packages/ui/src/constants/labels.ts", [], "constants",
        "bun run check-types",
    ),
    "4.2": Task(
        "4.2", "Create Units Constant", "phase-4",
        "packages/ui/src/constants/units.ts", [], "constants",
        "bun run check-types",
    ),
    "4.3": Task(
        "4.3", "Create Defaults Constant", "phase-4",
        "packages/ui/src/constants/defaults.ts", [], "constants",
        "bun run check-types",
    ),
    "4.4": Task(
        "4.4", "Create Constants Index", "phase-4",
        "packages/ui/src/constants/index.ts", ["4.1", "4.2", "4.3"], None,
        "bun run check-types",
    ),
    # Phase 5: Integration
    "5.1": Task(
        "5.1", "Start Full Stack", "phase-5", None, ["1.4", "3.3", "4.4"], None,
        "docker compose ps --format json | jq -e 'map(select(.State == \"running\")) | length >= 3'",
        requires_docker=True,
    ),
    "5.2": Task(
        "5.2", "Health Check Services", "phase-5", None, ["5.1"], None,
        "curl -sf http://localhost:3000/api/health && curl -sf http://localhost:8000/enapi/v1/health",
        requires_docker=True,
    ),
    "5.3": Task(
        "5.3", "Run Full Test Suite", "phase-5", None, ["5.2"], None,
        "bun test && cd apps/energy-api && uv run pytest",
    ),
}


# === Helper Functions ===


def deps_satisfied(task_id: str, state: State) -> bool:
    """Check if all task dependencies are satisfied."""
    return all(state.get_status(dep) == "passed" for dep in TASKS[task_id].dependencies)


def get_status_symbol(status: str) -> str:
    """Get emoji symbol for task status."""
    return {"passed": "✅", "failed": "❌", "pending": "⏳"}.get(status, "⏳")


def run_git(*args: str) -> subprocess.CompletedProcess[str]:
    """Run git command in project directory."""
    return subprocess.run(["git", *args], capture_output=True, text=True, cwd=PROJECT_DIR)


# === Commands ===


def cmd_next() -> None:
    """Get next executable task(s)."""
    state = State.load()

    if state.consecutive_failures >= MAX_CONSECUTIVE_FAILURES:
        print(f"ROLLBACK_NEEDED:{state.consecutive_failures} consecutive failures")
        return

    executable = [
        tid for tid in TASKS
        if state.get_status(tid) in ("pending", "failed") and deps_satisfied(tid, state)
    ]

    if not executable:
        print("COMPLETE" if all(state.get_status(t) == "passed" for t in TASKS) else "BLOCKED")
        return

    # Check for parallel tasks
    for group_tasks in PARALLEL_GROUPS.values():
        parallel = [t for t in executable if t in group_tasks]
        if len(parallel) > 1:
            print(f"PARALLEL:{' '.join(parallel)}")
            return

    print(f"SEQUENTIAL:{executable[0]}")


def cmd_status() -> None:
    """Show current progress."""
    state = State.load()
    passed = sum(1 for t in TASKS if state.get_status(t) == "passed")
    failed = sum(1 for t in TASKS if state.get_status(t) == "failed")

    current_phase = next(
        (p["name"] for p in PHASES.values() if not all(state.get_status(t) == "passed" for t in p["tasks"])),
        "Complete",
    )

    print(f"Phase: {current_phase}")
    print(f"Progress: {passed}/{len(TASKS)} tasks ({failed} failed)")
    print(f"Failures: {state.consecutive_failures}/{MAX_CONSECUTIVE_FAILURES}\n")

    for phase in PHASES.values():
        print(f"[{phase['name']}]")
        for tid in phase["tasks"]:
            task = TASKS[tid]
            symbol = get_status_symbol(state.get_status(tid))
            parallel = " [∥]" if task.parallel_group else ""
            print(f"  {symbol} {tid}: {task.name}{parallel}")
        print()


def cmd_graph() -> None:
    """Show dependency graph."""
    state = State.load()
    print("╔════════════════════════════════════════════════════════════╗")
    print("║            FLEX+ Migration Dependency Graph                ║")
    print("╚════════════════════════════════════════════════════════════╝\n")

    for phase in PHASES.values():
        print(f"┌─ {phase['name']} {'─' * (48 - len(phase['name']))}┐")
        for tid in phase["tasks"]:
            task = TASKS[tid]
            symbol = get_status_symbol(state.get_status(tid))
            deps = f" ← [{', '.join(task.dependencies)}]" if task.dependencies else ""
            parallel = " [∥]" if task.parallel_group else ""
            print(f"│ {symbol} {tid}: {task.name[:32]:<32}{parallel}{deps}")
        print(f"└{'─' * 54}┘\n")

    print("Legend: ✅ Passed  ❌ Failed  ⏳ Pending  [∥] Parallelizable")


def cmd_details(task_id: str) -> None:
    """Show task details."""
    if task_id not in TASKS:
        print(f"Unknown task: {task_id}", file=sys.stderr)
        sys.exit(1)

    task = TASKS[task_id]
    print(f"Task: {task.id} - {task.name}")
    print(f"Phase: {PHASES[task.phase]['name']}")
    print(f"File: {task.file or 'N/A'}")
    print(f"Dependencies: {', '.join(task.dependencies) or 'None'}")
    print(f"Verify: {task.verify}")
    print(f"Parallel: {task.parallel_group or 'No'}")
    print(f"Docker: {'Yes' if task.requires_docker else 'No'}")


def cmd_complete(task_id: str) -> None:
    """Mark task as complete."""
    if task_id not in TASKS:
        print(f"Unknown task: {task_id}", file=sys.stderr)
        sys.exit(1)

    state = State.load()
    state.set_status(task_id, "passed", "Completed")
    state.consecutive_failures = 0
    state.save()

    task = TASKS[task_id]
    phase_tasks = PHASES[task.phase]["tasks"]
    if all(state.get_status(t) == "passed" for t in phase_tasks):
        print(f"CHECKPOINT:{task.phase}")
    else:
        print("OK")


def cmd_fail(task_id: str, message: str) -> None:
    """Mark task as failed."""
    if task_id not in TASKS:
        print(f"Unknown task: {task_id}", file=sys.stderr)
        sys.exit(1)

    state = State.load()
    state.set_status(task_id, "failed", message)
    state.consecutive_failures += 1
    state.save()

    if state.consecutive_failures >= MAX_CONSECUTIVE_FAILURES:
        print(f"ROLLBACK_NEEDED:{state.consecutive_failures}")
    else:
        print(f"FAILED:{state.consecutive_failures}/{MAX_CONSECUTIVE_FAILURES}")


def cmd_checkpoint(name: str, message: str) -> None:
    """Create git checkpoint."""
    if not run_git("status", "--porcelain").stdout.strip():
        print("No changes to checkpoint")
        return

    subprocess.run(["git", "add", "-A"], cwd=PROJECT_DIR, check=True)
    commit_msg = f"checkpoint({name}): {message}\n\nAutomated checkpoint by Claude Code."
    subprocess.run(["git", "commit", "-m", commit_msg], cwd=PROJECT_DIR, check=True)

    tag = f"checkpoint/flexplus/{name}-{datetime.now().strftime('%Y%m%d-%H%M%S')}"
    subprocess.run(["git", "tag", tag], cwd=PROJECT_DIR, check=True)

    state = State.load()
    state.checkpoints[name] = {
        "commit": run_git("rev-parse", "HEAD").stdout.strip(),
        "tag": tag,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
    state.save()
    print(f"Checkpoint: {tag}")


def cmd_rollback(target: str = "last") -> None:
    """Show rollback instructions."""
    if target == "last":
        target_ref = "HEAD~1"
    else:
        state = State.load()
        if target in state.checkpoints:
            target_ref = state.checkpoints[target]["commit"]
        else:
            result = run_git("rev-parse", f"checkpoint/flexplus/{target}")
            target_ref = result.stdout.strip() if result.returncode == 0 else target

    print(f"Rollback to: {target_ref}")
    run_git("log", "--oneline", f"{target_ref}..HEAD")
    print(f"\nExecute: git reset --hard {target_ref}")


def cmd_validate(validation_type: str, file_path: str = "") -> None:
    """Run validation checks."""
    if validation_type == "bash":
        cmd = sys.stdin.read() if not file_path else file_path
        dangerous = ["DROP TABLE", "DROP DATABASE", "rm -rf /", "rm -rf ~", "--force.*main"]
        if any(p.lower() in cmd.lower() for p in dangerous):
            print("BLOCKED: Dangerous command", file=sys.stderr)
            sys.exit(2)
        print("OK")

    elif validation_type == "frontend":
        if not file_path or not file_path.endswith((".ts", ".tsx", ".js", ".jsx")):
            sys.exit(0)
        content = Path(file_path).read_text() if Path(file_path).exists() else ""
        issues = []
        if "http://localhost:" in content:
            issues.append("Hardcoded localhost URL")
        if any(p in content.lower() for p in ["api_key=", "secret=", "password="]):
            issues.append("Potential credential")
        if issues:
            print(f"Warning: {', '.join(issues)}", file=sys.stderr)

    elif validation_type == "standards":
        print("TypeScript: bun run check-types && bun run check")
        print("Python: cd apps/energy-api && uv run ruff check")
        print("Frontend: Use LABELS/UNITS/DEFAULTS constants")

    elif validation_type == "security":
        patterns = ["API_KEY", "SECRET", "PASSWORD", "TOKEN"]
        for pattern in patterns:
            result = subprocess.run(
                ["rg", "-i", pattern, "--type", "ts", "--type", "py", "-l"],
                capture_output=True, text=True, cwd=PROJECT_DIR,
            )
            if result.stdout.strip():
                print(f"{pattern}: {result.stdout.strip()}")


def cmd_reset() -> None:
    """Reset all progress."""
    if STATE_FILE.exists():
        STATE_FILE.unlink()
    print("Progress reset.")


# === Main ===


def main() -> None:
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)

    cmd, args = sys.argv[1], sys.argv[2:]

    commands: dict[str, Any] = {
        "next": cmd_next,
        "status": cmd_status,
        "graph": cmd_graph,
        "details": lambda: cmd_details(args[0]) if args else print("Usage: details <task_id>"),
        "complete": lambda: cmd_complete(args[0]) if args else print("Usage: complete <task_id>"),
        "fail": lambda: cmd_fail(args[0], " ".join(args[1:])) if len(args) >= 2 else print("Usage: fail <id> <msg>"),
        "checkpoint": lambda: cmd_checkpoint(args[0], " ".join(args[1:])) if len(args) >= 2 else print("Usage: checkpoint <name> <msg>"),
        "rollback": lambda: cmd_rollback(args[0] if args else "last"),
        "validate": lambda: cmd_validate(args[0], args[1] if len(args) > 1 else "") if args else print("Usage: validate <type>"),
        "reset": cmd_reset,
    }

    if cmd not in commands:
        print(f"Unknown: {cmd}\n{__doc__}")
        sys.exit(1)

    commands[cmd]() if callable(commands[cmd]) else commands[cmd]


if __name__ == "__main__":
    main()
