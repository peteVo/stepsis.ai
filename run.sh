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

# Prefer the active Python on PATH when it already has the retrieval deps.
# Fall back to the repository .venv so the workflow still runs from a plain shell.
PYTHON_BIN="${PYTHON_BIN:-$(command -v python)}"

if [[ -z "$PYTHON_BIN" || ! -x "$PYTHON_BIN" ]]; then
  PYTHON_BIN="$ROOT_DIR/.venv/bin/python"
fi

if ! "$PYTHON_BIN" - <<'PY' >/dev/null 2>&1; then
import qdrant_client  # noqa: F401
PY
  PYTHON_BIN="$ROOT_DIR/.venv/bin/python"
fi

if [[ -z "$PYTHON_BIN" || ! -x "$PYTHON_BIN" ]]; then
  echo "No usable Python found. Activate an environment or create .venv." >&2
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
  PYTHONPATH="$ROOT_DIR" "$PYTHON_BIN" - "$QUERY" "$TOP_K" "$ROOT_DIR" <<'PY'
import json
import sys
import re
from datetime import datetime
from pathlib import Path

from fastapi.testclient import TestClient

import src.retrieval.main as main_mod

query = sys.argv[1]
top_k_str = sys.argv[2]
root_dir = Path(sys.argv[3])

# Build payload; only include top_k if explicitly provided
payload = {"query": query}
if top_k_str:
    payload["top_k"] = int(top_k_str)

def slugify(value: str) -> str:
    slug = re.sub(r"[^a-zA-Z0-9]+", "_", value.strip().lower()).strip("_")
    return slug[:80] or "query"

output_dir = root_dir / "outputs" / "retrieval"
output_dir.mkdir(parents=True, exist_ok=True)
timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
output_path = output_dir / f"{timestamp}_{slugify(query)}.json"

with TestClient(main_mod.app) as client:
    response = client.post("/retrieve", json=payload)
    response.raise_for_status()
    data = response.json()

with output_path.open("w", encoding="utf-8") as fh:
    json.dump(data, fh, indent=2, ensure_ascii=False)
    fh.write("\n")

print(json.dumps(data, indent=2, ensure_ascii=False))
print(f"Saved retrieval output to: {output_path}")
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