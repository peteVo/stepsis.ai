#!/usr/bin/env python3
"""Ingest extracted chunk JSON produced by the extraction pipeline into the retrieval DB.

Scans `src/ingestion/extracted_markdowns/*`, reads the `*_chunks.json` file in
each folder, and submits the chunk objects to the retrieval ingestion handler.
"""
from __future__ import annotations

import asyncio
import json
from pathlib import Path
from typing import Any, List

from src.retrieval.database.qdrant_client import get_qdrant_client
from src.retrieval.services.ingestion import get_ingestion_handler


ROOT = Path(__file__).resolve().parents[2]
MARKDOWN_DIR = ROOT / "src" / "ingestion" / "extracted_markdowns"


def discover_chunk_files(base: Path) -> List[Path]:
    docs: List[Path] = []
    if not base.exists():
        return docs
    for sub in sorted(base.iterdir()):
        if not sub.is_dir():
            continue
        chunk_candidates = list(sub.glob("*_chunks.json"))
        if not chunk_candidates:
            continue
        chosen = None
        for chunk_file in chunk_candidates:
            if chunk_file.stem.lower() == f"{sub.name.lower()}_chunks":
                chosen = chunk_file
                break
        if chosen is None:
            chosen = chunk_candidates[0]
        docs.append(chosen)
    return docs


def _coerce_page_number(value: Any) -> int:
    if isinstance(value, int):
        return value
    if isinstance(value, str):
        try:
            return int(value)
        except ValueError:
            return 1
    return 1


def load_chunks_from_json(json_path: Path) -> List[dict]:
    raw_chunks = json.loads(json_path.read_text(encoding="utf-8"))
    if not isinstance(raw_chunks, list):
        raise ValueError(f"Expected a list in {json_path}")

    chunks: List[dict] = []
    chunk_count = len(raw_chunks)
    source_id = json_path.parent.name
    for index, chunk in enumerate(raw_chunks):
        if not isinstance(chunk, dict):
            continue
        metadata = dict(chunk.get("metadata") or {})
        metadata.setdefault("chunk_index", index)
        metadata.setdefault("chunk_count", chunk_count)
        metadata.setdefault("parent_source_id", source_id)
        raw_content = str(chunk.get("raw_content") or "")

        # Extract simple numeric facts from the chunk text for provenance and deterministic answers
        extracted_facts: List[dict] = []
        try:
            # percent matches e.g. '44%', '44.4 %'
            for m in re.finditer(r"\b(\d{1,3}(?:\.\d+)?)\s*%\b", raw_content):
                value = float(m.group(1))
                extracted_facts.append({
                    "type": "percentage",
                    "value": value,
                    "unit": "%",
                    "text": m.group(0),
                    "start": m.start(),
                    "end": m.end(),
                })
            # plain numeric matches (integers/floats) near keywords
            for m in re.finditer(r"\b(\d{1,6}(?:\.\d+)?)\b", raw_content):
                # capture small numbers as counts; leave disambiguation to verifier
                value = float(m.group(1))
                extracted_facts.append({
                    "type": "number",
                    "value": value,
                    "unit": None,
                    "text": m.group(0),
                    "start": m.start(),
                    "end": m.end(),
                })
        except Exception:
            # fall back to empty list on any unexpected parsing error
            extracted_facts = []

        chunks.append(
            {
                "source_id": str(chunk.get("source_id") or source_id),
                "page_number": _coerce_page_number(chunk.get("page_number", 1)),
                "content_type": str(chunk.get("content_type") or "text"),
                "raw_content": raw_content,
                "metadata": metadata,
                "extracted_facts": extracted_facts,
            }
        )
    return chunks


async def main(force_ingest: bool = False) -> None:
    chunk_files = discover_chunk_files(MARKDOWN_DIR)
    if not chunk_files:
        print("No chunk JSON files found in", MARKDOWN_DIR)
        return

    chunks: List[dict] = []
    for path in chunk_files:
        chunks.extend(load_chunks_from_json(path))

    expected_chunks = len(chunks)
    print(f"Discovered {len(chunk_files)} chunk files; {expected_chunks} chunks total.")

    qdrant = get_qdrant_client()
    try:
        qdrant.initialize()
    except Exception as exc:
        print("Warning: Qdrant initialization failed:", exc)
        print("Continuing; ingestion may fail if Qdrant is not reachable.")
        return

    # Check if Qdrant already has the chunks (cache hit)
    if not force_ingest:
        try:
            actual_count = qdrant.client.count(
                collection_name="sepsis-evidence"
            ).count
            if actual_count >= expected_chunks:
                print(
                    f"✅ Qdrant cache hit: {actual_count} chunks already present "
                    f"(expected ≥{expected_chunks}). Skipping ingestion."
                )
                print("Use FORCE_INGEST=1 or pass --force-ingest to re-ingest.")
                return
        except Exception as exc:
            print(f"Warning: Could not check Qdrant count: {exc}")
            print("Proceeding with full ingestion.")

    print(f"Ingesting {expected_chunks} chunks...")
    handler = get_ingestion_handler()
    result = await handler.ingest(chunks)
    print(
        json.dumps(
            {
                "ingested": result.ingested,
                "skipped_duplicates": result.skipped_duplicates,
                "batches_written": result.batches_written,
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    import os
    import sys

    force = os.environ.get("FORCE_INGEST", "").lower() in ("1", "true", "yes")
    if "--force-ingest" in sys.argv:
        force = True

    asyncio.run(main(force_ingest=force))