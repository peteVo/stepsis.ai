from __future__ import annotations

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from src.retrieval.config import config
from src.retrieval.database.qdrant_client import get_qdrant_client
from src.retrieval.models.schemas import HealthCheck

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
        "message": "Hello World",
    }
