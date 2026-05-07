from __future__ import annotations

import logging
from typing import List

import httpx

from src.retrieval.config import config

logger = logging.getLogger(__name__)


class EmbeddingService:
    def __init__(self) -> None:
        self._cache: dict[str, List[float]] = {}

    async def embed_text(self, text: str) -> List[float]:
        key = text.strip()
        if key in self._cache:
            return self._cache[key]

        if not config.openrouter_api_key:
            raise ValueError("OPENROUTER_API_KEY is not set.")

        payload = {
            "model": config.embedding_model,
            "input": key,
        }

        headers = {
            "Authorization": f"Bearer {config.openrouter_api_key}",
            "Content-Type": "application/json",
        }

        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                f"{config.openrouter_base_url}/embeddings",
                headers=headers,
                json=payload,
            )
            response.raise_for_status()
            data = response.json()

        embedding = data["data"][0]["embedding"]
        self._cache[key] = embedding
        return embedding

    async def embed_batch(self, texts: List[str]) -> List[List[float]]:
        results: List[List[float]] = []
        for text in texts:
            results.append(await self.embed_text(text))
        return results


_embedding_service: EmbeddingService | None = None


def get_embedding_service() -> EmbeddingService:
    global _embedding_service
    if _embedding_service is None:
        _embedding_service = EmbeddingService()
    return _embedding_service
