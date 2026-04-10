#!/bin/bash
set -euo pipefail

usage() {
    cat <<'EOF'
Usage:
  scripts/git-preflight.sh [--expect-branch <branch-name>]

Checks that the current Git context is safe for local development:
  - current branch is not main, beta, or stable
  - working tree is clean
  - current branch matches the expected branch when provided
EOF
}

fail() {
    echo "Git preflight failed: $1" >&2
    exit 1
}

EXPECTED_BRANCH=""

while [[ $# -gt 0 ]]; do
    case "$1" in
        --expect-branch)
            [[ $# -ge 2 ]] || fail "missing value for --expect-branch."
            EXPECTED_BRANCH="$2"
            shift 2
            ;;
        -h|--help)
            usage
            exit 0
            ;;
        *)
            usage >&2
            fail "unknown argument: $1"
            ;;
    esac
done

REPO_ROOT=$(git rev-parse --show-toplevel 2>/dev/null) || fail "run this command from inside the repository."
cd "$REPO_ROOT"

CURRENT_BRANCH=$(git symbolic-ref --quiet --short HEAD 2>/dev/null || true)
[[ -n "$CURRENT_BRANCH" ]] || fail "detached HEAD is not allowed. Checkout a dedicated work branch first."

case "$CURRENT_BRANCH" in
    main|beta|stable)
        fail "branch '$CURRENT_BRANCH' is protected. Use a dedicated story, fix, docs, or chore branch in a dedicated worktree."
        ;;
esac

if [[ -n "$EXPECTED_BRANCH" && "$CURRENT_BRANCH" != "$EXPECTED_BRANCH" ]]; then
    fail "branch '$CURRENT_BRANCH' does not match expected branch '$EXPECTED_BRANCH'."
fi

WORKTREE_STATUS=$(git status --porcelain --untracked-files=normal)
if [[ -n "$WORKTREE_STATUS" ]]; then
    echo "$WORKTREE_STATUS" >&2
    fail "working tree is not clean."
fi

echo "Git preflight passed on branch '$CURRENT_BRANCH'."
