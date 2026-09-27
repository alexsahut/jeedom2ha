#!/bin/bash
# Prepare a local Python 3.9 test environment, user-space, no sudo/apt.
set -euo pipefail

usage() {
    cat <<'EOF'
Usage:
  scripts/setup-test-env.sh [--venv-dir <path>]

Prepares a user-space Python 3.9 virtual environment for running the
project's test suite, without sudo or a system package manager:
  - installs uv (https://astral.sh/uv) into $HOME/.local/bin if missing
  - installs a managed Python 3.9 toolchain via `uv python install 3.9`
  - creates/reuses a virtualenv (default: .venv) via `uv venv --python 3.9`
  - installs the project with its `test` extras into that virtualenv

Idempotent: safe to run multiple times.
EOF
}

fail() {
    echo "setup-test-env failed: $1" >&2
    exit 1
}

VENV_DIR=".venv"

while [[ $# -gt 0 ]]; do
    case "$1" in
        --venv-dir)
            [[ $# -ge 2 ]] || fail "missing value for --venv-dir."
            VENV_DIR="$2"
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

# Ensure uv is on PATH (user-space install, no sudo).
if ! command -v uv >/dev/null 2>&1 && [[ -x "$HOME/.local/bin/uv" ]]; then
    export PATH="$HOME/.local/bin:$PATH"
fi

if ! command -v uv >/dev/null 2>&1; then
    echo "uv not found. Installing uv into \$HOME/.local/bin (no sudo)..."
    curl -LsSf https://astral.sh/uv/install.sh | sh
    export PATH="$HOME/.local/bin:$PATH"
fi

command -v uv >/dev/null 2>&1 || fail "uv installation failed or uv is still not on PATH."

echo "uv version: $(uv --version)"

echo "Ensuring managed Python 3.9 toolchain is installed via uv..."
uv python install 3.9

if [[ -x "$VENV_DIR/bin/python" ]]; then
    VENV_PY_VERSION=$("$VENV_DIR/bin/python" --version 2>&1 | awk '{print $2}')
    if [[ "$VENV_PY_VERSION" == 3.9.* ]]; then
        echo "Reusing existing virtualenv '$VENV_DIR'."
    else
        echo "Existing virtualenv '$VENV_DIR' uses Python $VENV_PY_VERSION, not 3.9. Recreating..."
        rm -rf "$VENV_DIR"
        uv venv --python 3.9 "$VENV_DIR"
    fi
else
    echo "Creating virtualenv '$VENV_DIR' with Python 3.9..."
    uv venv --python 3.9 "$VENV_DIR"
fi

echo "Installing project (test extras) into '$VENV_DIR'..."
uv pip install --python "$VENV_DIR/bin/python" -e ".[test]"

echo ""
echo "Test environment ready: $VENV_DIR"
"$VENV_DIR/bin/python" --version
