#!/bin/bash
set -euo pipefail

usage() {
    cat <<'EOF'
Usage:
  scripts/start-story-worktree.sh <branch-name> [worktree-path]

Creates a dedicated branch and worktree from local main after verifying:
  - command runs from the main clone
  - current branch is main
  - working tree is clean
  - local main is aligned with origin/main
EOF
}

fail() {
    echo "Story worktree setup failed: $1" >&2
    exit 1
}

[[ $# -ge 1 && $# -le 2 ]] || {
    usage >&2
    exit 2
}

BRANCH_NAME="$1"
CUSTOM_PATH="${2:-}"

REPO_ROOT=$(git rev-parse --show-toplevel 2>/dev/null) || fail "run this command from inside the repository."
cd "$REPO_ROOT"

MAIN_WORKTREE=""
while IFS= read -r line; do
    case "$line" in
        worktree\ *)
            MAIN_WORKTREE=${line#worktree }
            break
            ;;
    esac
done < <(git worktree list --porcelain)

[[ -n "$MAIN_WORKTREE" ]] || fail "unable to detect the main clone worktree."
CURRENT_PATH=$(pwd -P)

[[ "$CURRENT_PATH" == "$MAIN_WORKTREE" ]] || fail "run this helper from the main clone, not from a linked worktree."

CURRENT_BRANCH=$(git symbolic-ref --quiet --short HEAD 2>/dev/null || true)
[[ "$CURRENT_BRANCH" == "main" ]] || fail "main clone must be on branch 'main'. Current branch: '$CURRENT_BRANCH'."

case "$BRANCH_NAME" in
    ""|main|beta|stable)
        fail "branch '$BRANCH_NAME' is not allowed for story work."
        ;;
esac

WORKTREE_STATUS=$(git status --porcelain --untracked-files=normal)
if [[ -n "$WORKTREE_STATUS" ]]; then
    echo "$WORKTREE_STATUS" >&2
    fail "main clone is not clean."
fi

echo "Fetching origin..."
git fetch origin

LOCAL_MAIN=$(git rev-parse main)
REMOTE_MAIN=$(git rev-parse origin/main)
[[ "$LOCAL_MAIN" == "$REMOTE_MAIN" ]] || fail "local main is not aligned with origin/main."

if git show-ref --verify --quiet "refs/heads/$BRANCH_NAME"; then
    fail "local branch '$BRANCH_NAME' already exists."
fi

if git show-ref --verify --quiet "refs/remotes/origin/$BRANCH_NAME"; then
    fail "remote branch '$BRANCH_NAME' already exists."
fi

REPO_NAME=$(basename "$REPO_ROOT")
BRANCH_SLUG=${BRANCH_NAME//\//-}
DEFAULT_BASE=${TMPDIR:-/tmp}
DEFAULT_PATH="${DEFAULT_BASE%/}/${REPO_NAME}-${BRANCH_SLUG}"
WORKTREE_PATH="${CUSTOM_PATH:-$DEFAULT_PATH}"

[[ ! -e "$WORKTREE_PATH" ]] || fail "worktree path already exists: $WORKTREE_PATH"

git worktree add -b "$BRANCH_NAME" "$WORKTREE_PATH" main

echo "Created branch '$BRANCH_NAME' in worktree:"
echo "$WORKTREE_PATH"
