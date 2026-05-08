#!/usr/bin/env bash

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "$SCRIPT_DIR/../.." && pwd)"

# Try to activate conda 'sepsis' env first so packages like pymupdf4llm are
# available. Otherwise fall back to repo .venv Python.
PYTHON_BIN=""
if command -v conda >/dev/null 2>&1; then
	eval "$(conda shell.bash hook)" 2>/dev/null || true
	if conda activate sepsis 2>/dev/null; then
		PYTHON_BIN="$(command -v python)"
		echo "Using conda 'sepsis' Python: $PYTHON_BIN"
	else
		echo "Warning: could not activate conda env 'sepsis' — will try venv fallback"
	fi
fi

if [[ -z "$PYTHON_BIN" ]]; then
	PYTHON_BIN="$ROOT_DIR/.venv/bin/python"
	if [[ ! -x "$PYTHON_BIN" ]]; then
		echo "Error: no usable Python found. Activate conda env 'sepsis' or create .venv." >&2
		exit 1
	fi
	echo "Using venv Python: $PYTHON_BIN"
fi

echo "======================================================"
echo "🚀 STARTING RAG INGESTION PIPELINE"
echo "======================================================"

# ---------------------------------------------------------
# STEP 1: PDF to Markdown Extraction
# ---------------------------------------------------------
echo ""
echo "▶️  STEP 1: Running extract_text.py (PDF -> MD + PNGs)..."
"$PYTHON_BIN" "$SCRIPT_DIR/extract_text.py"
echo "✅ Step 1 Complete."

# ---------------------------------------------------------
# STEP 2: Vision Analysis
# ---------------------------------------------------------
echo ""
echo "▶️  STEP 2: Running extract_image.py (AI Vision Analysis)..."
"$PYTHON_BIN" "$SCRIPT_DIR/extract_image.py"
echo "✅ Step 2 Complete."

# ---------------------------------------------------------
# STEP 3: Chunking for Vector DB
# ---------------------------------------------------------
echo ""
echo "▶️  STEP 3: Running chunk.py (MD -> JSON Chunks)..."
"$PYTHON_BIN" "$SCRIPT_DIR/chunk.py"
echo "✅ Step 3 Complete."

echo ""
echo "======================================================"
echo "🎉 PIPELINE FINISHED SUCCESSFULLY!"
echo "======================================================"
