#!/bin/bash
# Reproduce .github/workflows/test.yml locally: lint, pytest matrix,
# node unit tests, php lint/tests, and a bash -n sweep over scripts/.
set -euo pipefail

REPO_ROOT=$(git rev-parse --show-toplevel 2>/dev/null) || {
    echo "ci-local: run this command from inside the repository." >&2
    exit 1
}
cd "$REPO_ROOT"

export CI=true
export PATH="$HOME/.local/bin:$PATH"

OVERALL_STATUS=0
RESULTS=()

step() {
    echo
    echo "════════════════════════════════════════════════════════════"
    echo "▶ $1"
    echo "════════════════════════════════════════════════════════════"
}

record() {
    # record <name> <status: PASS|FAIL|SKIPPED ...>
    RESULTS+=("$1|$2")
    if [[ "$2" == "FAIL" ]]; then
        OVERALL_STATUS=1
    fi
}

# ---------------------------------------------------------------------------
# lint job (mirrors: flake8 resources/daemon tests, Python 3.9)
# ---------------------------------------------------------------------------
step "lint — flake8 resources/daemon tests (Python 3.9)"
./scripts/setup-test-env.sh
VENV_PY="$REPO_ROOT/.venv/bin/python"

if "$VENV_PY" -m flake8 resources/daemon tests; then
    record "lint (flake8)" "PASS"
else
    record "lint (flake8)" "FAIL"
fi

# ---------------------------------------------------------------------------
# test job (mirrors: pytest --cov matrix, Python 3.9 and 3.12)
# ---------------------------------------------------------------------------
PYTEST_ARGS=(-m pytest --cov=resources/daemon --cov-report=xml --cov-report=term-missing)
PYTEST_LOG=$(mktemp)

join_lines() {
    # Joins stdin lines with ", " (paste -d takes a rotating char list, not a string).
    awk 'NR>1{printf ", "} {printf "%s", $0} END{print ""}'
}

summarize_pytest() {
    # Extracts the final pytest summary counts, e.g. "1697 passed, 3 failed".
    grep -oE '[0-9]+ (passed|failed|error|skipped)' "$PYTEST_LOG" | tail -6 | join_lines
}

step "test — pytest + coverage (Python 3.9)"
if "$VENV_PY" "${PYTEST_ARGS[@]}" 2>&1 | tee "$PYTEST_LOG"; then
    record "test (pytest 3.9): $(summarize_pytest)" "PASS"
else
    record "test (pytest 3.9): $(summarize_pytest)" "FAIL"
fi

step "test — pytest + coverage (Python 3.12)"
: > "$PYTEST_LOG"
if uv run --python 3.12 --with-editable ".[test]" --isolated -- python "${PYTEST_ARGS[@]}" 2>&1 | tee "$PYTEST_LOG"; then
    record "test (pytest 3.12): $(summarize_pytest)" "PASS"
else
    record "test (pytest 3.12): $(summarize_pytest)" "FAIL"
fi
rm -f "$PYTEST_LOG"

# ---------------------------------------------------------------------------
# node job (mirrors: node --test tests/unit/*.node.test.js)
# ---------------------------------------------------------------------------
step "node — node --test tests/unit/*.node.test.js"
if ! command -v node >/dev/null 2>&1; then
    record "node tests" "FAIL"
    echo "ci-local: 'node' is not installed — cannot run node --test." >&2
else
    NODE_LOG=$(mktemp)
    if node --test tests/unit/*.node.test.js 2>&1 | tee "$NODE_LOG"; then
        NODE_STATUS="PASS"
    else
        NODE_STATUS="FAIL"
    fi
    # Node 24 prints summary lines as "ℹ tests 12", Node 20/22 print "# tests 12".
    NODE_SUMMARY=$(grep -E '^(ℹ|#) (tests|pass|fail) ' "$NODE_LOG" | sed -E 's/^(ℹ|#) //' | join_lines)
    record "node (node --test): $NODE_SUMMARY" "$NODE_STATUS"
    rm -f "$NODE_LOG"
fi

# ---------------------------------------------------------------------------
# bash -n sweep over scripts/ (syntax check only, never executes the scripts)
# ---------------------------------------------------------------------------
step "bash -n — syntax check every script in scripts/"
BASH_N_FAIL=0
BASH_N_TOTAL=0
for f in scripts/*.sh; do
    BASH_N_TOTAL=$((BASH_N_TOTAL + 1))
    if bash -n "$f"; then
        echo "OK   $f"
    else
        echo "FAIL $f"
        BASH_N_FAIL=$((BASH_N_FAIL + 1))
    fi
done
if [[ "$BASH_N_FAIL" -eq 0 ]]; then
    record "bash -n ($BASH_N_TOTAL/$BASH_N_TOTAL scripts OK)" "PASS"
else
    record "bash -n ($((BASH_N_TOTAL - BASH_N_FAIL))/$BASH_N_TOTAL scripts OK)" "FAIL"
fi

# ---------------------------------------------------------------------------
# php job (mirrors: setup-php + php -l + php test execution)
# A fixed, explicit list of test files under tests/ requires a real Jeedom
# core bootstrap (core/php/core.inc.php) that only exists inside an actual
# Jeedom installation. They are skipped with a clear message instead of
# failing, matching the project's long-standing convention (see
# docs/dev-deploy.md and the story implementation artifacts) of validating
# those specific tests manually on a real box rather than in a sandboxed
# checkout. Any other test failure fails this job.
# ---------------------------------------------------------------------------
step "php — php -l and php test execution"
if ! command -v php >/dev/null 2>&1; then
    record "php tests" "SKIPPED (php not installed locally)"
    echo "ci-local: 'php' is not installed — skipping php -l and php test execution."
    echo "          (php is provided on GitHub Actions runners via shivammathur/setup-php, matrix 7.4 and 8.2)"
else
    PHP_LINT_FAIL=0
    PHP_LINT_TOTAL=0
    while IFS= read -r f; do
        PHP_LINT_TOTAL=$((PHP_LINT_TOTAL + 1))
        if ! php -l "$f" >/dev/null; then
            PHP_LINT_FAIL=$((PHP_LINT_FAIL + 1))
        fi
    done < <(git ls-files '*.php')

    if [[ "$PHP_LINT_FAIL" -eq 0 ]]; then
        record "php -l ($PHP_LINT_TOTAL/$PHP_LINT_TOTAL files OK)" "PASS"
    else
        record "php -l ($((PHP_LINT_TOTAL - PHP_LINT_FAIL))/$PHP_LINT_TOTAL files OK)" "FAIL"
    fi

    NEEDS_JEEDOM_CORE=(
        "tests/test_php_published_scope_relay.php"
        "tests/test_php_topology_extraction.php"
        "tests/test_runtime_bootstrap_startup.php"
    )

    PHP_PASS=0
    PHP_SKIP=0
    PHP_FAIL=0
    while IFS= read -r f; do
        [[ -f "$f" ]] || continue
        skip=0
        for needs_core in "${NEEDS_JEEDOM_CORE[@]}"; do
            if [[ "$f" == "$needs_core" ]]; then
                skip=1
                break
            fi
        done
        if [[ "$skip" -eq 1 ]]; then
            echo "--- $f ---"
            echo "SKIP: $f requires a real Jeedom install (core.inc.php not available in this sandbox)."
            PHP_SKIP=$((PHP_SKIP + 1))
            continue
        fi
        echo "--- $f ---"
        PHP_OUT=$(php "$f" 2>&1) && PHP_CODE=0 || PHP_CODE=$?
        echo "$PHP_OUT"
        if [[ "$PHP_CODE" -eq 0 ]]; then
            PHP_PASS=$((PHP_PASS + 1))
        else
            PHP_FAIL=$((PHP_FAIL + 1))
            echo "FAIL: $f"
        fi
    done < <(printf '%s\n' tests/test_php_*.php tests/test_runtime_bootstrap_startup.php)

    if [[ "$PHP_FAIL" -eq 0 ]]; then
        record "php tests ($PHP_PASS passed, $PHP_SKIP skipped, needs real Jeedom core)" "PASS"
    else
        record "php tests ($PHP_PASS passed, $PHP_SKIP skipped, $PHP_FAIL failed)" "FAIL"
    fi
fi

# ---------------------------------------------------------------------------
# Summary
# ---------------------------------------------------------------------------
step "Summary"
for entry in "${RESULTS[@]}"; do
    printf '%-70s %s\n' "${entry%%|*}" "${entry##*|}"
done

if [[ "$OVERALL_STATUS" -eq 0 ]]; then
    echo
    echo "✅ ci-local: all checks passed."
else
    echo
    echo "❌ ci-local: at least one check failed."
fi

exit "$OVERALL_STATUS"
