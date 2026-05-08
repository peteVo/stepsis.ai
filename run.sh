#!/usr/bin/env bash

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
FORCE_INGEST=""
QUERY="${1:-${QUERY:-}}"
TOP_K="${TOP_K:-}"  # Empty by default; endpoint will use config values

# Check for --force-ingest flag
if [[ "$QUERY" == "--force-ingest" ]]; then
  FORCE_INGEST="--force-ingest"
  QUERY="${2:-${QUERY:-}}"  # shift to next arg if present
fi

# Use the active Python on PATH so the caller controls the environment.
PYTHON_BIN="${PYTHON_BIN:-$(command -v python)}"

if [[ -z "$PYTHON_BIN" || ! -x "$PYTHON_BIN" ]]; then
  echo "No usable Python found on PATH. Activate the desired environment first." >&2
  exit 1
fi
echo "Using Python: $PYTHON_BIN"

echo "======================================================"
echo "🚀 STARTING SEPSIS ATLAS END-TO-END WORKFLOW"
echo "======================================================"

echo ""
echo "▶️  STEP 1: Running ingestion pipeline (PDF -> Markdown -> Images -> JSON chunks)..."
bash "$ROOT_DIR/src/ingestion/run.sh"
echo "✅ Step 1 Complete."

echo ""
echo "▶️  STEP 2: Ingesting extracted chunk JSON into retrieval / Qdrant..."
PYTHONPATH="$ROOT_DIR" "$PYTHON_BIN" -m src.retrieval.ingest_markdowns $FORCE_INGEST
echo "✅ Step 2 Complete."

if [[ -n "$QUERY" ]]; then
  echo ""
  echo "▶️  STEP 3: Running retrieval query and printing JSON output..."
  PYTHONPATH="$ROOT_DIR" "$PYTHON_BIN" - "$QUERY" "$TOP_K" <<'PY'
import json
import sys

from fastapi.testclient import TestClient

import src.retrieval.main as main_mod

query = sys.argv[1]
top_k_str = sys.argv[2]

# Build payload; only include top_k if explicitly provided
payload = {"query": query}
if top_k_str:
    payload["top_k"] = int(top_k_str)

with TestClient(main_mod.app) as client:
    response = client.post("/retrieve", json=payload)
    response.raise_for_status()
    print(json.dumps(response.json(), indent=2))
PY
  echo "✅ Step 3 Complete."
else
  echo ""
  echo "No query provided; skipped retrieval output step."
fi

echo ""
echo "======================================================"
echo "🎉 WORKFLOW FINISHED"
echo "======================================================"