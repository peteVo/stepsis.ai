from __future__ import annotations

from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class IngestionChunk(BaseModel):
    source_id: str
    page_number: int
    content_type: str
    raw_content: str
    metadata: Dict[str, Any] = Field(default_factory=dict)


class RetrievalQuery(BaseModel):
    query: str = Field(min_length=3)
    top_k: int = Field(default=5, ge=1, le=20)


class RetrievedContextItem(BaseModel):
    rank: int
    text: str
    source_reference: str
    confidence_score: float = Field(ge=0.0, le=1.0)


class RetrievalResponse(BaseModel):
    query: str
    retrieved_context: List[RetrievedContextItem]


class HealthCheck(BaseModel):
    status: str
    vector_db_connected: bool
    openrouter_configured: bool
    details: Optional[str] = None
