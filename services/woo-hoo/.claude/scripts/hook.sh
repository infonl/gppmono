#!/bin/bash
# Slim hook wrapper - delegates to Python orchestrator
# Usage: hook.sh <hook_type>
# Hook types: pre-write, pre-bash, post-write, session-start

set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_DIR="${CLAUDE_PROJECT_DIR:-$(dirname "$(dirname "$SCRIPT_DIR")")}"
ORCHESTRATOR="$SCRIPT_DIR/orchestrator.py"

hook_type="$1"

case "$hook_type" in
    pre-bash)
        # Validate bash commands - read from stdin
        uv run python "$ORCHESTRATOR" validate bash
        ;;

    pre-write)
        # Validate file writes - file path from tool input
        INPUT=$(cat)
        FILE_PATH=$(echo "$INPUT" | jq -r '.tool_input.file_path // empty')
        if [[ "$FILE_PATH" =~ \.(ts|tsx|js|jsx)$ ]]; then
            uv run python "$ORCHESTRATOR" validate frontend "$FILE_PATH" 2>&1 || true
        fi
        exit 0
        ;;

    post-write)
        # Run linting after writes
        INPUT=$(cat)
        FILE_PATH=$(echo "$INPUT" | jq -r '.tool_input.file_path // empty')

        if [[ "$FILE_PATH" =~ \.(ts|tsx)$ ]]; then
            cd "$PROJECT_DIR" && bun run biome check "$FILE_PATH" 2>&1 | head -10 || true
        elif [[ "$FILE_PATH" =~ \.py$ ]]; then
            cd "$PROJECT_DIR/apps/energy-api" && uv run ruff check "${FILE_PATH##*/}" 2>&1 | head -10 || true
        fi
        exit 0
        ;;

    session-start)
        echo "═══════════════════════════════════════════════════════════"
        echo "  FLEX+ Migration - LOCAL FIRST Development"
        echo "═══════════════════════════════════════════════════════════"
        echo ""
        echo "Commands:"
        echo "  /implement  - Continue autonomous implementation"
        echo "  /status     - View progress and dependency graph"
        echo "  /validate   - Run validation checks"
        echo ""
        uv run python "$ORCHESTRATOR" status 2>/dev/null | head -5 || echo "No progress yet. Run /implement to start."
        echo ""
        ;;

    *)
        echo "Unknown hook type: $hook_type" >&2
        exit 1
        ;;
esac
