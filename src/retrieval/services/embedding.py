from __future__ import annotations

import logging
from collections import OrderedDict
from typing import List

import httpx

from src.retrieval.config import config

logger = logging.getLogger(__name__)


class EmbeddingService:
    def __init__(self) -> None:
        self._cache: OrderedDict[str, List[float]] = OrderedDict()

    def _cache_get(self, key: str) -> List[float] | None:
        embedding = self._cache.get(key)
        if embedding is not None:
            self._cache.move_to_end(key)
        return embedding

    def _cache_set(self, key: str, embedding: List[float]) -> None:
        self._cache[key] = embedding
        self._cache.move_to_end(key)
        while len(self._cache) > config.embedding_cache_size:
            self._cache.popitem(last=False)

    async def embed_text(self, text: str) -> List[float]:
        key = text.strip()
        cached = self._cache_get(key)
        if cached is not None:
            return cached
        # If no OpenRouter API key is configured, fall back to a deterministic
        # local embedding generator based on SHA256. This allows offline
        # ingestion/testing without external API access. The fallback produces
        # `config.embedding_dimension` floats in range [-1, 1].
        if not config.openrouter_api_key:
            import hashlib

            dim = config.embedding_dimension
            vec: List[float] = []
            counter = 0
            while len(vec) < dim:
                h = hashlib.sha256(f"{key}\x00{counter}".encode("utf-8")).digest()
                # convert each 4 bytes -> float in [-1,1]
                for i in range(0, len(h), 4):
                    if len(vec) >= dim:
                        break
                    chunk = h[i : i + 4]
                    val = int.from_bytes(chunk, "big", signed=False)
                    # normalize into [0,1], then map to [-1,1]
                    f = (val / 0xFFFFFFFF) * 2.0 - 1.0
                    vec.append(float(f))
                counter += 1
            embedding = vec
        else:
            payload = {
                "model": config.embedding_model,
                "input": key,
            }

            headers = {
                "Authorization": f"Bearer {config.openrouter_api_key}",
                "Content-Type": "application/json",
            }

            try:
                async with httpx.AsyncClient(timeout=30.0) as client:
                    response = await client.post(
                        f"{config.openrouter_base_url}/embeddings",
                        headers=headers,
                        json=payload,
                    )
                    response.raise_for_status()
                    data = response.json()

                embedding = data["data"][0]["embedding"]
            except Exception as exc:
                logger.warning("OpenRouter embedding failed (%s). Falling back to local embedding.", exc)
                # fallback to deterministic local embedding
                import hashlib

                dim = config.embedding_dimension
                vec: List[float] = []
                counter = 0
                while len(vec) < dim:
                    h = hashlib.sha256(f"{key}\x00{counter}".encode("utf-8")).digest()
                    for i in range(0, len(h), 4):
                        if len(vec) >= dim:
                            break
                        chunk = h[i : i + 4]
                        val = int.from_bytes(chunk, "big", signed=False)
                        f = (val / 0xFFFFFFFF) * 2.0 - 1.0
                        vec.append(float(f))
                    counter += 1
                embedding = vec
        self._cache_set(key, embedding)
        return embedding

    def cache_size(self) -> int:
        return len(self._cache)

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
