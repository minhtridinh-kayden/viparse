#!/usr/bin/env bash
#
# dev.sh — run the local quality gates. CI (.github/workflows/ci.yml) calls the
# same gates through this script, so `scripts/dev.sh` locally == what CI runs.
# See `scripts/dev.sh --help` for the available commands.
set -euo pipefail

# Always run from the repository root, regardless of the caller's cwd.
REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$REPO_ROOT"

usage() {
    cat <<'EOF'
dev.sh — run the local quality gates.

Usage:
  scripts/dev.sh            # run the CI gates: lint + type-check + test
  scripts/dev.sh lint       # ruff check + ruff format --check
  scripts/dev.sh type       # mypy src
  scripts/dev.sh test       # pytest with coverage
  scripts/dev.sh build      # build the wheel/sdist (not a CI gate)
  scripts/dev.sh -h|--help  # show this help
EOF
}

lint() {
    echo ">> lint (ruff)"
    ruff check .
    ruff format --check .
}

type_check() {
    echo ">> type-check (mypy)"
    mypy src
}

test_suite() {
    echo ">> test (pytest + coverage)"
    pytest --cov=viparse --cov-report=term-missing
}

build() {
    echo ">> build (python -m build)"
    python -m build
}

main() {
    if [ "$#" -gt 1 ]; then
        echo "error: too many arguments; expected at most one command" >&2
        echo >&2
        usage >&2
        exit 2
    fi
    local cmd="${1:-all}"
    case "$cmd" in
        lint) lint ;;
        type) type_check ;;
        test) test_suite ;;
        build) build ;;
        all)
            # Mirrors ci.yml's quality job exactly — no build (CI never builds).
            lint
            type_check
            test_suite
            ;;
        -h | --help) usage ;;
        *)
            echo "error: unknown command '$cmd'" >&2
            echo >&2
            usage >&2
            exit 2
            ;;
    esac
}

main "$@"
