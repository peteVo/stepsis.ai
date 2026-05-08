# Sepsis Atlas: AI-Powered Clinical Evidence Retrieval

A end-to-end RAG (Retrieval-Augmented Generation) pipeline for extracting structured, source-grounded clinical evidence from sepsis research PDFs.

## Pipeline Overview

The system implements three main stages:

1. **Ingestion**: Extract PDFs → Markdown → AI vision analysis → JSON chunks
2. **Embedding & Storage**: Embed chunks via OpenRouter → Store in Qdrant cloud
3. **Retrieval**: Hybrid search (BM25 + semantic) → Rerank → Return ranked results

## Quick Start

### Prerequisites

- Python 3.13+ (with `.venv` virtual environment)
- OpenRouter API key (for embeddings & reranking)
- Qdrant Cloud instance
- PDF articles in `articles/` directory

### Running the Pipeline

The main entry point is `run.sh`, which orchestrates the full workflow.

#### Basic Usage

Run the complete pipeline (extraction → ingestion → retrieval):

```bash
bash run.sh
```

This will:
- Extract PDFs to Markdown
- Run AI vision analysis on images
- Chunk Markdown files
- Ingest chunks into Qdrant
- Output success messages for each step

#### With a Query

Run the full pipeline and retrieve results for a clinical question:

```bash
bash run.sh "Which study reported the highest mortality?"
```

Output: JSON with 15 ranked results (default from `config/params.yml`)

#### With Custom Result Count

Control the number of results returned using `TOP_K` environment variable:

```bash
TOP_K=10 bash run.sh "What are risk factors for sepsis?"
TOP_K=30 bash run.sh "Lactate levels and outcomes"
```

Valid range: 1-30 (capped by `reranker_top_k` in config)

#### Skip Ingestion (Caching)

Qdrant caching is enabled by default. On subsequent runs, Step 2 (ingestion) skips if the collection already has sufficient chunks:

```bash
bash run.sh "Which interventions improve survival?"
# Step 2 output: "✅ Qdrant cache hit: 5994 chunks already present. Skipping ingestion."
```

To force re-ingestion (e.g., after updating chunks):

```bash
bash run.sh --force-ingest "query"
# or
FORCE_INGEST=1 bash run.sh "query"
```

## Configuration

Tunable parameters are in `config/params.yml`. Key settings:

```yaml
# Result ranking
reranker_top_k: 30          # Max candidates before reranking
final_top_k: 15             # Default results returned (if not specified in query)

# Hybrid retrieval weights
hybrid_keyword_weight: 0.3  # BM25 keyword search weight
hybrid_semantic_weight: 0.7 # Qdrant semantic search weight

# Search candidates
bm25_candidate_limit: 50    # Initial keyword candidates

# Text chunking
text_chunk_size: 1100       # Characters per chunk
text_chunk_overlap: 120     # Overlap between chunks

# Ingestion
ingestion_batch_size: 32    # Batch size for embedding API
```

Changes to `params.yml` take effect on the next run.

## Environment Variables

```bash
# Required: Set before running
export OPENROUTER_API_KEY="your-api-key"
export QDRANT_URL="https://your-cluster.eu-central-1-0.aws.cloud.qdrant.io:6333"
export QDRANT_API_KEY="your-qdrant-key"

# Optional: Override defaults
export TOP_K=20             # Results per query (1-30)
export FORCE_INGEST=1       # Skip caching, re-ingest
export APP_ENV=development  # development or production
export LOG_LEVEL=INFO       # DEBUG, INFO, WARNING, ERROR
```

## Output Format

Query results are returned as JSON with ranked chunks:

```json
{
  "query": "Which study reported the highest mortality?",
  "retrieved_context": [
    {
      "rank": 1,
      "text": "...",
      "source_reference": "Wang_2020, Page 1, Chunk 1/2",
      "confidence_score": 0.535,
      "keyword_score": 0.0,
      "semantic_score": 0.884,
      "reranker_score": 0.861,
      "source_id": "Wang_2020",
      "page_number": 1,
      "metadata": {...}
    },
    ...
  ]
}
```

### Score Breakdown

- **confidence_score**: Normalized hybrid score (keyword + semantic)
- **keyword_score**: BM25 keyword match relevance
- **semantic_score**: Qdrant vector similarity
- **reranker_score**: Cohere reranking model score (0.0-1.0)

## Workflow Steps

### Step 1: Extraction
- Converts PDFs to Markdown using `pymupdf4llm`
- Extracts embedded images as PNG files
- Stores in `src/ingestion/extracted_markdowns/`

### Step 2: Image Vision Analysis
- Analyzes extracted images with OpenRouter multimodal API
- Injects AI-generated descriptions back into Markdown files

### Step 3: Chunking
- Splits Markdown into semantic chunks (default: 1100 chars, 120 char overlap)
- Outputs `*_chunks.json` files alongside Markdown

### Step 4: Embedding & Storage
- Embeds chunks via OpenRouter (`text-embedding-3-small`, 1536 dims)
- Creates BM25 keyword index
- Upserts to Qdrant with metadata payloads

### Step 5: Retrieval (Optional)
- Embeds query
- Searches BM25 index + Qdrant semantic vectors
- Merges results with normalized hybrid scores
- Reranks with Cohere (`cohere/rerank-4-pro`)
- Returns top-k results sorted by reranker score

## Examples

### Example 1: Find mortality studies
```bash
bash run.sh "Which study reported the highest mortality?"
```
Returns 15 ranked chunks with mortality statistics

### Example 2: Get more results
```bash
TOP_K=25 bash run.sh "What are risk factors for sepsis?"
```
Returns 25 chunks analyzing risk factors

### Example 3: Force fresh ingestion
```bash
bash run.sh --force-ingest "Lactate levels and patient outcomes"
```
Re-embeds all chunks and updates Qdrant, then queries

### Example 4: Just run extraction & ingestion (no query)
```bash
bash run.sh
```
Completes Steps 1-4, skips retrieval

## Troubleshooting

**"ModuleNotFoundError: pymupdf4llm"**
- `pymupdf4llm` only exists in conda `sepsis` environment
- Extraction uses conda, retrieval uses `.venv`
- Verify: `which pymupdf4llm`

**"Qdrant connection failed"**
- Check `QDRANT_URL` and `QDRANT_API_KEY` are set
- Verify network access to Qdrant cloud cluster
- Test: `curl -H "api-key: $QDRANT_API_KEY" $QDRANT_URL/collections`

**"OpenRouter API errors"**
- Verify `OPENROUTER_API_KEY` is valid
- Check quota and rate limits in OpenRouter dashboard
- Embeddings use `text-embedding-3-small`; reranking uses `cohere/rerank-4-pro`

**"No results returned"**
- Confirm chunks are indexed: `bash run.sh` (without query) runs ingestion
- Check Qdrant collection: `curl -H "api-key: $QDRANT_API_KEY" $QDRANT_URL/collections/sepsis-evidence`
- Try a simpler query: `bash run.sh "sepsis mortality"`

## Architecture

```
PDFs (articles/)
    ↓
[extract_text.py] → extract_image.py → chunk.py
    ↓
Markdown + Images + JSON chunks
    ↓
[ingest_markdowns.py] → OpenRouter embeddings → Qdrant upsert
    ↓
Collection: sepsis-evidence (5994+ points)
    ↓
[HybridSearchService] (BM25 + semantic search)
    ↓
[RerankerService] (Cohere rerank)
    ↓
[ResponseFormatter] → JSON output
```

## Performance

- **Ingestion**: ~4700 chunks in 158 batches (~30 sec)
- **Qdrant Query**: <500ms semantic search + BM25
- **Reranking**: ~1 sec for 30 candidates
- **Total retrieval time**: ~2 seconds end-to-end

## License

See LICENSE file for details.
