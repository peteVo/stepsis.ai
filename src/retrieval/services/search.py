from __future__ import annotations

import logging
from typing import Dict, List

from src.retrieval.config import config
from src.retrieval.models.schemas import RetrievedChunk
from src.retrieval.services.embedding import get_embedding_service
from src.retrieval.services.ingestion import IngestedRecord, get_ingestion_handler
from src.retrieval.services.reranker import get_reranker_service

logger = logging.getLogger(__name__)


class HybridSearchService:
    def __init__(self) -> None:
        self._ingestion_handler = get_ingestion_handler()
        self._embedding_service = get_embedding_service()
        self._reranker_service = get_reranker_service()

    async def search(self, query: str, top_k: int = 5) -> List[RetrievedChunk]:
        records = self._ingestion_handler.all_records()

        keyword_matches = self._ingestion_handler.keyword_index().search(
            query,
            top_k=config.bm25_candidate_limit,
        )
        query_embedding = await self._embedding_service.embed_text(query)
        semantic_matches = self._ingestion_handler.qdrant().query(
            query_embedding,
            top_k=config.bm25_candidate_limit,
        )

        ranked = self._merge_results(records, keyword_matches, semantic_matches)
        preliminary_output: List[RetrievedChunk] = []
        for rank, item in enumerate(ranked[: config.reranker_top_k], start=1):
            preliminary_output.append(
                RetrievedChunk(
                    rank=rank,
                    text=item["record"].text,
                    source_reference=item["record"].source_reference,
                    confidence_score=item["confidence_score"],
                    keyword_score=item["keyword_score"],
                    semantic_score=item["semantic_score"],
                    reranker_score=0.0,
                    source_id=item["record"].chunk.source_id,
                    page_number=item["record"].chunk.page_number,
                    content_type=item["record"].chunk.content_type,
                    metadata=item["record"].chunk.metadata,
                )
            )

        reranked = await self._reranker_service.rerank(query, preliminary_output, top_k=top_k)
        return reranked

    def _merge_results(self, records: List[IngestedRecord], keyword_matches, semantic_matches) -> List[Dict]:
        combined: Dict[str, Dict] = {}

        for index, keyword_score in keyword_matches:
            if index >= len(records):
                continue
            record = records[index]
            normalized_keyword = self._normalize(keyword_score, keyword_matches)
            combined[record.point_id] = {
                "record": record,
                "keyword_score": normalized_keyword,
                "semantic_score": 0.0,
            }

        for match in semantic_matches:
            point_id = str(match.id)
            payload = match.payload or {}
            record = self._record_from_payload(point_id, payload)
            normalized_semantic = self._normalize(float(match.score or 0.0), semantic_matches)
            if point_id not in combined:
                combined[point_id] = {
                    "record": record,
                    "keyword_score": 0.0,
                    "semantic_score": normalized_semantic,
                }
            else:
                combined[point_id]["semantic_score"] = max(combined[point_id]["semantic_score"], normalized_semantic)

        ranked = []
        for item in combined.values():
            confidence = (config.hybrid_keyword_weight * item["keyword_score"]) + (
                config.hybrid_semantic_weight * item["semantic_score"]
            )
            ranked.append(
                {
                    "record": item["record"],
                    "keyword_score": self._clip(item["keyword_score"]),
                    "semantic_score": self._clip(item["semantic_score"]),
                    "confidence_score": self._clip(confidence),
                }
            )

        ranked.sort(key=lambda item: item["confidence_score"], reverse=True)
        return ranked

    @staticmethod
    def _normalize(value: float, matches) -> float:
        scores = [float(match[1] if isinstance(match, tuple) else match.score or 0.0) for match in matches]
        max_score = max(scores) if scores else 1.0
        if max_score <= 0:
            return 0.0
        return float(value) / max_score

    @staticmethod
    def _clip(value: float) -> float:
        return max(0.0, min(1.0, value))

    @staticmethod
    def _record_from_payload(point_id: str, payload: Dict) -> IngestedRecord:
        from src.retrieval.models.schemas import IngestionChunk

        chunk = IngestionChunk.model_validate(
            {
                "source_id": payload.get("source_id", "unknown"),
                "page_number": payload.get("page_number", 0),
                "content_type": payload.get("content_type", "text"),
                "raw_content": payload.get("raw_content", ""),
                "metadata": payload.get("metadata", {}),
                "extracted_keywords": payload.get("keywords", []),
            }
        )
        return IngestedRecord(
            chunk=chunk,
            text=chunk.raw_content,
            keywords=list(payload.get("keywords", [])),
            point_id=point_id,
            source_reference=str(payload.get("source_reference", f"{chunk.source_id}, Page {chunk.page_number}")),
        )
