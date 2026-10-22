#!/usr/bin/env bash
# examples/agent-pipe.sh
# Demonstrates querying md-context and piping the token-budgeted context pack
# into a downstream agent or LLM processor.

set -euo pipefail

VAULT="${1:-tests/fixtures/vault}"
QUERY="${2:-valve}"
BUDGET="${3:-4000}"
CACHE_DIR="${4:-.cache}"

echo "==> Indexing vault at ${VAULT}..."
md-context index "${VAULT}" --cache-dir "${CACHE_DIR}"

echo "==> Querying: '${QUERY}' (budget: ${BUDGET} tokens)..."
# In a real setup, replace the cat pipeline with your agent CLI
# e.g.: md-context query ... | llm -m gpt-4o "Answer based on context"
md-context query "${QUERY}" --root "${VAULT}" --cache-dir "${CACHE_DIR}" --budget "${BUDGET}" | {
  echo "--- Agent stdin stream received ---"
  cat
  echo "--- Agent stdin stream completed ---"
}
