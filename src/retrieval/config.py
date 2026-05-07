from __future__ import annotations

import os
from dataclasses import dataclass
from dotenv import load_dotenv

load_dotenv()


@dataclass(frozen=True)
class Config:
    openrouter_api_key: str = os.getenv("OPENROUTER_API_KEY", "")
    openrouter_base_url: str = os.getenv("OPENROUTER_BASE_URL", "https://openrouter.ai/api/v1")

    qdrant_url: str = os.getenv("QDRANT_URL", "http://localhost:6333")
    qdrant_api_key: str = os.getenv("QDRANT_API_KEY", "")
    qdrant_collection_name: str = os.getenv("QDRANT_COLLECTION_NAME", "sepsis-evidence")

    embedding_model: str = os.getenv("EMBEDDING_MODEL", "text-embedding-3-small")
    reranker_model: str = os.getenv("RERANKER_MODEL", "bge-reranker-v2-m3")
    embedding_dimension: int = int(os.getenv("EMBEDDING_DIMENSION", "1536"))

    app_env: str = os.getenv("APP_ENV", "development")
    log_level: str = os.getenv("LOG_LEVEL", "INFO")


config = Config()
