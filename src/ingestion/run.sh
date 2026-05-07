#!/bin/bash

# Exit immediately if any command fails
set -e

echo "======================================================"
echo "🚀 STARTING RAG INGESTION PIPELINE"
echo "======================================================"

# Optional: If you are using a virtual environment (like 'uv' or 'venv'), 
# uncomment the line below to activate it automatically when the script runs!
# source .venv/bin/activate

# ---------------------------------------------------------
# STEP 1: PDF to Markdown Extraction
# ---------------------------------------------------------
echo ""
echo "▶️  STEP 1: Running extract_text.py (PDF -> MD + PNGs)..."
python extract_text.py
echo "✅ Step 1 Complete."

# ---------------------------------------------------------
# STEP 2: Vision Analysis
# ---------------------------------------------------------
echo ""
echo "▶️  STEP 2: Running extract_image.py (AI Vision Analysis)..."
python extract_image.py
echo "✅ Step 2 Complete."

# ---------------------------------------------------------
# STEP 3: Chunking for Vector DB
# ---------------------------------------------------------
echo ""
echo "▶️  STEP 3: Running chunk.py (MD -> JSON Chunks)..."
python chunk.py
echo "✅ Step 3 Complete."

echo ""
echo "======================================================"
echo "🎉 PIPELINE FINISHED SUCCESSFULLY!"
echo "======================================================"
