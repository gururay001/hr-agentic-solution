#!/usr/bin/env bash
# Spine Owner Pod Verification Script (scripts/verify_pod.sh)
# Usage: ./scripts/verify_pod.sh feat/pod3-workweek-hitl pod3

set -euo pipefail

BRANCH="${1:-feat/pod3-workweek-hitl}"
POD_PREFIX="${2:-pod3}"

echo "=== 1. Fetching latest remote branches from origin ==="
git fetch origin --prune

echo "=== 2. Checking commits on origin/${BRANCH} ahead of origin/main ==="
COMMITS=$(git rev-list --count "origin/main..origin/${BRANCH}")
echo "Commits ahead of main: ${COMMITS}"
if [ "${COMMITS}" -eq 0 ]; then
  echo "⚠️  No new commits pushed to origin/${BRANCH} yet (branch is still at $(git rev-parse --short origin/${BRANCH}))."
  echo "   Ask the engineer to run: git push origin ${BRANCH}"
  exit 0
fi

git log --oneline "origin/main..origin/${BRANCH}"

echo "=== 3. Checking Pod Directory Boundary Isolation ==="
CHANGED_FILES=$(git diff --name-only "origin/main...origin/${BRANCH}")
echo "${CHANGED_FILES}"
for file in ${CHANGED_FILES}; do
  if [[ "${file}" == app/slices/* ]] && [[ "${file}" != app/slices/${POD_PREFIX}_* ]]; then
    echo "❌ BOUNDARY VIOLATION: ${BRANCH} modified another pod's slice: ${file}"
    exit 1
  fi
done
echo "✅ Pod Boundary Check Passed!"

echo "=== 4. Running Pytest, Ruff & Mypy on ${BRANCH} ==="
git checkout "origin/${BRANCH}"
uv run --extra dev pytest tests/unit/ -v
uv run --extra dev ruff check app/ tests/unit/
uv run --extra dev mypy app/
git checkout main
echo "✅ All verification checks passed for ${BRANCH}! Ready to merge into main."
