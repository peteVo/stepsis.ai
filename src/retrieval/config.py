from __future__ import annotations

import os
from dataclasses import dataclass
from dotenv import load_dotenv

load_dotenv()


@dataclass
class Config:
    openrouter_api_key: str = os.getenv("OPENROUTER_API_KEY", "")
    openrouter_base_url: str = os.getenv("OPENROUTER_BASE_URL", "https://openrouter.ai/api/v1")

    qdrant_url: str = os.getenv("QDRANT_URL", "https://YOUR-QDRANT-CLUSTER-URL")
    qdrant_api_key: str = os.getenv("QDRANT_API_KEY", "")
    qdrant_collection_name: str = os.getenv("QDRANT_COLLECTION_NAME", "sepsis-evidence")

    # API / secret settings remain loaded from environment
    embedding_model: str = os.getenv("EMBEDDING_MODEL", "text-embedding-3-small")
    reranker_model: str = os.getenv("RERANKER_MODEL", "cohere/rerank-4-pro")
    embedding_dimension: int = 1536
    # Tunable parameters (use params.yml or code defaults; do not read from env)
    embedding_cache_size: int = 500
    hybrid_keyword_weight: float = 0.3
    hybrid_semantic_weight: float = 0.7
    bm25_candidate_limit: int = 50
    reranker_top_k: int = 20
    final_top_k: int = 5
    ingestion_batch_size: int = 32
    text_chunk_size: int = 1000
    text_chunk_overlap: int = 120
    reranker_keyword_boost: float = 0.25
    reranker_semantic_boost: float = 0.35
    reranker_density_boost: float = 0.20
    reranker_llm_boost: float = 0.20

    app_env: str = os.getenv("APP_ENV", "development")
    log_level: str = os.getenv("LOG_LEVEL", "INFO")


config = Config()


def _load_params_yaml() -> None:
    from pathlib import Path
    import logging

    logger = logging.getLogger(__name__)

    project_root = Path(__file__).resolve().parents[2]
    params_path = project_root / "config" / "params.yml"
    if not params_path.exists():
        return

    try:
        import yaml
    except Exception:
        logger.warning("PyYAML not installed; skipping params.yml load: %s", params_path)
        return

    with params_path.open("r", encoding="utf-8") as fh:
        data = yaml.safe_load(fh) or {}

    # Merge values from YAML into the config instance, casting to existing types
    for key, value in data.items():
        if not hasattr(config, key):
            continue
        current = getattr(config, key)
        try:
            if isinstance(current, bool):
                casted = bool(value)
            elif isinstance(current, int):
                casted = int(value)
            elif isinstance(current, float):
                casted = float(value)
            elif isinstance(current, (list, dict)):
                casted = value
            else:
                casted = str(value)
            setattr(config, key, casted)
        except Exception:
            logger.warning("Failed to cast config param %s with value %r", key, value)


# Load optional parameter overrides from config/params.yml (if present)
_load_params_yaml()
