from __future__ import annotations

import hashlib
import logging
import re
import uuid
from dataclasses import dataclass, field
from typing import Dict, List, Sequence

from src.retrieval.config import config
from src.retrieval.database.qdrant_client import get_qdrant_client
from src.retrieval.models.schemas import IngestionChunk
from src.retrieval.services.embedding import get_embedding_service
from src.retrieval.utils.keyword_index import KeywordIndex, tokenize
from src.retrieval.utils.text_splitter import RecursiveTextSplitter

logger = logging.getLogger(__name__)

KEYWORD_PATTERNS = [
    r"\bsepsis\b",
    r"\bseptic shock\b",
    r"\bmortality\b",
    r"\b28-day mortality\b",
    r"\blactate\b",
    r"\bvasopressor\b",
    r"\bicu\b",
    r"\bshock\b",
    r"\bsurvival\b",
    r"\boutcome\b",
]


@dataclass
class IngestedRecord:
    chunk: IngestionChunk
    text: str
    keywords: List[str]
    point_id: str
    source_reference: str
    embedding: List[float] = field(default_factory=list)


@dataclass
class IngestionBatchResult:
    records: List[IngestedRecord]
    ingested: int
    skipped_duplicates: int
    batches_written: int


class IngestionHandler:
    def __init__(self) -> None:
        self._records: List[IngestedRecord] = []
        self._keyword_index = KeywordIndex()
        self._known_point_ids: set[str] = set()
        self._splitter = RecursiveTextSplitter(
            chunk_size=config.text_chunk_size,
            chunk_overlap=config.text_chunk_overlap,
        )

    def _extract_keywords(self, text: str) -> List[str]:
        lowered = text.lower()
        extracted: List[str] = []
        for pattern in KEYWORD_PATTERNS:
            for match in re.findall(pattern, lowered):
                extracted.append(match)
        extracted.extend(token for token in tokenize(text) if len(token) > 4)
        deduped: List[str] = []
        seen = set()
        for keyword in extracted:
            if keyword not in seen:
                seen.add(keyword)
                deduped.append(keyword)
        return deduped

    def _point_id(self, chunk: IngestionChunk) -> str:
        signature = f"{chunk.source_id}:{chunk.page_number}:{chunk.content_type}:{chunk.raw_content}".encode("utf-8")
        hash_bytes = hashlib.sha256(signature).digest()
        return str(uuid.UUID(bytes=hash_bytes[:16]))

    async def ingest(self, chunks: Sequence[Dict]) -> IngestionBatchResult:
        validated_chunks = [IngestionChunk.model_validate(chunk) for chunk in chunks]
        embedding_service = get_embedding_service()
        qdrant = get_qdrant_client()

        records: List[IngestedRecord] = []
        skipped_duplicates = 0
        for chunk in validated_chunks:
            split_pieces = self._splitter.split_piece(chunk.raw_content, content_type=chunk.content_type)
            for piece in split_pieces:
                piece_chunk = chunk.model_copy(
                    update={
                        "raw_content": piece.text,
                        "metadata": {
                            **chunk.metadata,
                            "chunk_index": piece.chunk_index,
                            "chunk_count": piece.chunk_count,
                            "parent_chunk_size": len(chunk.raw_content),
                        },
                    }
                )
                keywords = self._extract_keywords(piece_chunk.raw_content)
                piece_chunk.extracted_keywords = keywords
                point_id = self._point_id(piece_chunk)
                if point_id in self._known_point_ids:
                    skipped_duplicates += 1
                    continue
                source_reference = f"{piece_chunk.source_id}, Page {piece_chunk.page_number}, Chunk {piece.chunk_index + 1}/{piece.chunk_count}"
                record = IngestedRecord(
                    chunk=piece_chunk,
                    text=piece_chunk.raw_content,
                    keywords=keywords,
                    point_id=point_id,
                    source_reference=source_reference,
                )
                records.append(record)

        batches_written = 0
        for start in range(0, len(records), config.ingestion_batch_size):
            batch = records[start : start + config.ingestion_batch_size]
            if not batch:
                continue

            embeddings = await embedding_service.embed_batch([record.text for record in batch])
            points = []
            for record, embedding in zip(batch, embeddings):
                record.embedding = embedding
                points.append(
                    {
                        "id": record.point_id,
                        "vector": record.embedding,
                        "payload": {
                            "source_id": record.chunk.source_id,
                            "page_number": record.chunk.page_number,
                            "content_type": record.chunk.content_type,
                            "raw_content": record.text,
                            "keywords": record.keywords,
                            "metadata": record.chunk.metadata,
                            "source_reference": record.source_reference,
                            "section_header": record.chunk.metadata.get("section_header"),
                            "coordinates": record.chunk.metadata.get("coordinates"),
                            "study_name": record.chunk.metadata.get("study_name"),
                            "population": record.chunk.metadata.get("population"),
                        },
                    }
                )

            if points:
                qdrant.upsert(points)
                batches_written += 1

        if records:
            self._records.extend(records)
            self._known_point_ids.update(record.point_id for record in records)
            self._keyword_index.build([record.text for record in self._records])

        logger.info("Ingested %d chunks into Qdrant (%d duplicates skipped, %d batches written)", len(records), skipped_duplicates, batches_written)
        return IngestionBatchResult(
            records=records,
            ingested=len(records),
            skipped_duplicates=skipped_duplicates,
            batches_written=batches_written,
        )

    def all_records(self) -> List[IngestedRecord]:
        return list(self._records)

    def keyword_index(self) -> KeywordIndex:
        return self._keyword_index

    def qdrant(self):
        return get_qdrant_client()

    def collection_name(self) -> str:
        return config.qdrant_collection_name


_ingestion_handler: IngestionHandler | None = None


def get_ingestion_handler() -> IngestionHandler:
    global _ingestion_handler
    if _ingestion_handler is None:
        _ingestion_handler = IngestionHandler()
    return _ingestion_handler
