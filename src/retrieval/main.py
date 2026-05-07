from __future__ import annotations

import logging
from contextlib import asynccontextmanager
from typing import List

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from src.retrieval.config import config
from src.retrieval.database.qdrant_client import get_qdrant_client
from src.retrieval.models.schemas import HealthCheck, IngestionResponse, RetrievalQuery, RetrievalResponse
from src.retrieval.services.ingestion import get_ingestion_handler
from src.retrieval.services.response_formatter import get_response_formatter
from src.retrieval.services.search import HybridSearchService

logging.basicConfig(level=getattr(logging, config.log_level.upper(), logging.INFO))
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Starting Sepsis Atlas Retrieval API in %s mode", config.app_env)
    qdrant_ready = False
    try:
        qdrant = get_qdrant_client()
        qdrant.initialize()
        qdrant_ready = True
    except Exception as exc:
        logger.warning("Qdrant not ready at startup: %s", exc)
    app.state.qdrant_ready = qdrant_ready
    app.state.ingestion_handler = get_ingestion_handler()
    app.state.search_service = HybridSearchService()
    app.state.response_formatter = get_response_formatter()
    yield


app = FastAPI(
    title="Sepsis Atlas Retrieval API",
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health", response_model=HealthCheck)
async def health() -> HealthCheck:
    openrouter_configured = bool(config.openrouter_api_key)
    qdrant_connected = False

    try:
        if getattr(app.state, "qdrant_ready", False):
            qdrant_connected = get_qdrant_client().health_check()
    except Exception as exc:
        logger.warning("Health check qdrant probe failed: %s", exc)

    status = "healthy" if qdrant_connected and openrouter_configured else "degraded"
    details = None
    if not openrouter_configured:
        details = "OPENROUTER_API_KEY is missing"
    elif not qdrant_connected:
        details = "Qdrant is not connected"

    return HealthCheck(
        status=status,
        vector_db_connected=qdrant_connected,
        openrouter_configured=openrouter_configured,
        details=details,
    )


@app.get("/")
async def root() -> dict:
    return {
        "service": "Sepsis Atlas Retrieval API",
        "phase": "Phase 2 in progress",
    }


@app.post("/ingest_chunks", response_model=IngestionResponse)
async def ingest_chunks(chunks: List[dict]) -> IngestionResponse:
    try:
        handler = getattr(app.state, "ingestion_handler")
        result = await handler.ingest(chunks)
        indexed_keywords = sum(len(record.keywords) for record in result.records)
        return IngestionResponse(
            ingested=result.ingested,
            collection_name=handler.collection_name(),
            indexed_keywords=indexed_keywords,
            skipped_duplicates=result.skipped_duplicates,
            batches_written=result.batches_written,
        )
    except Exception as exc:
        logger.exception("Chunk ingestion failed")
        raise HTTPException(status_code=500, detail=str(exc))


@app.post("/retrieve", response_model=RetrievalResponse)
async def retrieve(query: RetrievalQuery) -> RetrievalResponse:
    try:
        search_service = getattr(app.state, "search_service")
        formatter = getattr(app.state, "response_formatter")
        retrieved_context = await search_service.search(query.query, top_k=query.top_k)
        return formatter.format_retrieval(query.query, retrieved_context)
    except Exception as exc:
        logger.exception("Retrieval failed")
        raise HTTPException(status_code=500, detail=str(exc))
