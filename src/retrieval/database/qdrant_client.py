from __future__ import annotations

import logging
from typing import Any, Dict, Iterable, List

from qdrant_client import QdrantClient
from qdrant_client.http import models as qmodels

from src.retrieval.config import config

logger = logging.getLogger(__name__)


class QdrantDBClient:
    def __init__(self) -> None:
        self._client: QdrantClient | None = None

    def initialize(self) -> None:
        self._client = QdrantClient(
            url=config.qdrant_url,
            api_key=config.qdrant_api_key or None,
            prefer_grpc=False,
        )

        collections = self._client.get_collections().collections
        existing = {collection.name for collection in collections}

        if config.qdrant_collection_name not in existing:
            self._client.create_collection(
                collection_name=config.qdrant_collection_name,
                vectors_config=qmodels.VectorParams(
                    size=config.embedding_dimension,
                    distance=qmodels.Distance.COSINE,
                ),
            )
            logger.info("Created Qdrant collection '%s'", config.qdrant_collection_name)

        logger.info("Connected to Qdrant collection '%s'", config.qdrant_collection_name)

    @property
    def client(self) -> QdrantClient:
        if self._client is None:
            raise RuntimeError("Qdrant client is not initialized.")
        return self._client

    def health_check(self) -> bool:
        try:
            _ = self.client.get_collection(config.qdrant_collection_name)
            return True
        except Exception as exc:
            logger.warning("Qdrant health check failed: %s", exc)
            return False

    def upsert(self, points: Iterable[Dict[str, Any]]) -> None:
        point_structs: List[qmodels.PointStruct] = []
        for point in points:
            point_structs.append(
                qmodels.PointStruct(
                    id=point["id"],
                    vector=point["vector"],
                    payload=point.get("payload", {}),
                )
            )

        self.client.upsert(
            collection_name=config.qdrant_collection_name,
            points=point_structs,
            wait=True,
        )

    def query(
        self,
        vector: List[float],
        top_k: int = 5,
        metadata_filter: Dict[str, Any] | None = None,
    ):
        query_filter = None
        if metadata_filter:
            conditions = [
                qmodels.FieldCondition(
                    key=key,
                    match=qmodels.MatchValue(value=value),
                )
                for key, value in metadata_filter.items()
            ]
            query_filter = qmodels.Filter(must=conditions)

        return self.client.search(
            collection_name=config.qdrant_collection_name,
            query_vector=vector,
            query_filter=query_filter,
            limit=top_k,
            with_payload=True,
            with_vectors=False,
        )


_qdrant_client: QdrantDBClient | None = None


def get_qdrant_client() -> QdrantDBClient:
    global _qdrant_client
    if _qdrant_client is None:
        _qdrant_client = QdrantDBClient()
    return _qdrant_client
