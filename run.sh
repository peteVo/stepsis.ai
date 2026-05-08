#!/usr/bin/env bash

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
FORCE_INGEST=""
OUTPUT_DIR="$ROOT_DIR/output/retrieval"

QUERY="${1:-}"
TOP_K="${2:-}"

if [[ "$QUERY" == "--force-ingest" ]]; then
  FORCE_INGEST="--force-ingest"
  QUERY="${2:-}"
  TOP_K="${3:-}"
fi

# Prefer activating the 'sepsis' conda env (so system-installed packages like
# `pymupdf4llm` are available). If conda/activation fails, fall back to the
# repository virtual environment at .venv.
PYTHON_BIN="$ROOT_DIR/.venv/bin/python"

if [[ ! -x "$PYTHON_BIN" ]]; then
  echo "Virtual environment Python not found at $PYTHON_BIN" >&2
  exit 1
fi
echo "Using venv Python: $PYTHON_BIN"

# If a requirements.txt file exists, install into the chosen Python environment.
REQ_FILE="$ROOT_DIR/requirements.txt"
if [[ -f "$REQ_FILE" ]]; then
  echo "Installing Python requirements from $REQ_FILE into $PYTHON_BIN environment..."
  "$PYTHON_BIN" -m pip install --upgrade pip
  "$PYTHON_BIN" -m pip install -r "$REQ_FILE"
fi

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
  PYTHONPATH="$ROOT_DIR" "$PYTHON_BIN" - "$QUERY" "$TOP_K" "$OUTPUT_DIR" <<'PY'
import json
import sys
from datetime import datetime
from pathlib import Path
import re

from fastapi.testclient import TestClient

import src.retrieval.main as main_mod

query = sys.argv[1]
top_k_str = sys.argv[2]
output_dir = Path(sys.argv[3])


def slugify(value: str) -> str:
    slug = re.sub(r"[^a-zA-Z0-9]+", "_", value).strip("_")
    return slug[:80] or "query"

# Build payload; only include top_k if explicitly provided
payload = {"query": query}
if top_k_str:
    payload["top_k"] = int(top_k_str)

with TestClient(main_mod.app) as client:
    response = client.post("/retrieve", json=payload)
    response.raise_for_status()
    result = response.json()

output_dir.mkdir(parents=True, exist_ok=True)
timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
output_path = output_dir / f"{timestamp}_{slugify(query)}.json"
output_path.write_text(json.dumps(result, indent=2), encoding="utf-8")

print(json.dumps(result, indent=2))
print(f"Saved retrieval JSON to {output_path}")
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