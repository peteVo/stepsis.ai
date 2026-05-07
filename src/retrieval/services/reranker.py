from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Dict, List

import httpx

from src.retrieval.config import config
from src.retrieval.models.schemas import RetrievedChunk

logger = logging.getLogger(__name__)


@dataclass
class RerankCandidate:
    chunk: RetrievedChunk
    reranker_score: float
    adjusted_confidence: float


class RerankerService:
    def __init__(self) -> None:
        self._enabled = bool(config.openrouter_api_key)

    async def rerank(self, query: str, candidates: List[RetrievedChunk], top_k: int = 15) -> List[RetrievedChunk]:
        if not candidates:
            return []

        limited_candidates = candidates[: config.reranker_top_k]
        scores = await self._score_candidates(query, limited_candidates)
        reranked: List[RerankCandidate] = []

        for index, candidate in enumerate(limited_candidates):
            reranker_score = scores.get(str(index), 0.0)
            adjusted_confidence = self._combine_scores(candidate, reranker_score)
            reranked.append(
                RerankCandidate(
                    chunk=candidate,
                    reranker_score=self._clip(reranker_score),
                    adjusted_confidence=self._clip(adjusted_confidence),
                )
            )

        reranked.sort(key=lambda item: item.adjusted_confidence, reverse=True)

        results: List[RetrievedChunk] = []
        for rank, item in enumerate(reranked[:top_k], start=1):
            results.append(
                item.chunk.model_copy(
                    update={
                        "rank": rank,
                        "reranker_score": item.reranker_score,
                        "confidence_score": item.adjusted_confidence,
                    }
                )
            )
        return results

    async def _score_candidates(self, query: str, candidates: List[RetrievedChunk]) -> Dict[str, float]:
        if not self._enabled:
            return self._heuristic_scores(query, candidates)

        headers = {
            "Authorization": f"Bearer {config.openrouter_api_key}",
            "Content-Type": "application/json",
            "HTTP-Referer": "http://localhost",
            "X-Title": "Sepsis Atlas Retrieval Reranker",
        }
        documents = [candidate.text for candidate in candidates]
        payload = {
            "model": config.reranker_model,
            "query": query,
            "documents": documents,
            "top_n": min(config.reranker_top_k, len(documents)),
        }

        try:
            async with httpx.AsyncClient(timeout=45.0) as client:
                response = await client.post(
                    f"{config.openrouter_base_url}/rerank",
                    headers=headers,
                    json=payload,
                )
                response.raise_for_status()
                data = response.json()

            logger.info("OpenRouter rerank response: %s", data)
            scores: Dict[str, float] = {}
            for result in data.get("results", []):
                doc_index = result.get("index", -1)
                relevance_score = result.get("relevance_score", 0.0)
                if doc_index >= 0:
                    scores[str(doc_index)] = self._clip(float(relevance_score))
            return scores
        except Exception as exc:
            logger.warning("OpenRouter rerank failed, using heuristic fallback: %s", exc)
            return self._heuristic_scores(query, candidates)


    def _heuristic_scores(self, query: str, candidates: List[RetrievedChunk]) -> Dict[str, float]:
        query_tokens = set(self._tokenize(query))
        scores: Dict[str, float] = {}
        for index, candidate in enumerate(candidates):
            text_tokens = set(self._tokenize(candidate.text))
            overlap = len(query_tokens & text_tokens)
            density = self._evidence_density(candidate)
            score = (0.45 * candidate.keyword_score) + (0.35 * candidate.semantic_score) + (0.20 * density)
            if overlap:
                score += min(0.15, overlap / max(len(query_tokens), 1) * 0.15)
            scores[str(index)] = self._clip(score)
        return scores


    def _combine_scores(self, candidate: RetrievedChunk, reranker_score: float) -> float:
        density = self._evidence_density(candidate)
        return (
            config.reranker_keyword_boost * candidate.keyword_score
            + config.reranker_semantic_boost * candidate.semantic_score
            + config.reranker_density_boost * density
            + config.reranker_llm_boost * reranker_score
        )

    def _evidence_density(self, candidate: RetrievedChunk) -> float:
        text = candidate.text.lower()
        markers = [
            "auc",
            "or ",
            "hr ",
            "%",
            "ci",
            "sensitivity",
            "specificity",
            "logistic regression",
            "roc",
            "cox",
            "table",
            "results",
            "adjusted",
            "univariable",
            "multivariable",
        ]
        hits = sum(1 for marker in markers if marker in text)
        return self._clip(hits / max(len(markers), 1))

    @staticmethod
    def _candidate_key(candidate: RetrievedChunk) -> str:
        return f"{candidate.source_reference}|{candidate.source_id or ''}|{candidate.page_number or ''}|{candidate.content_type or ''}"

    @staticmethod
    def _tokenize(text: str) -> List[str]:
        tokens: List[str] = []
        for raw_token in text.lower().split():
            token = "".join(char for char in raw_token if char.isalnum() or char in {"/", "-"})
            if token:
                tokens.append(token)
        return tokens

    @staticmethod
    def _clip(value: float) -> float:
        return max(0.0, min(1.0, value))


_reranker_service: RerankerService | None = None


def get_reranker_service() -> RerankerService:
    global _reranker_service
    if _reranker_service is None:
        _reranker_service = RerankerService()
    return _reranker_service
