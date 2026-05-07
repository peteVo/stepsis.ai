from __future__ import annotations

from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class IngestionChunk(BaseModel):
    source_id: str
    page_number: int
    content_type: str
    raw_content: str
    metadata: Dict[str, Any] = Field(default_factory=dict)
    extracted_keywords: List[str] = Field(default_factory=list)


class IngestionResponse(BaseModel):
    ingested: int
    collection_name: str
    indexed_keywords: int
    skipped_duplicates: int = 0
    batches_written: int = 0


class RetrievalQuery(BaseModel):
    query: str = Field(min_length=3)
    top_k: int = Field(default=5, ge=1, le=20)


class RetrievedChunk(BaseModel):
    rank: int
    text: str
    source_reference: str
    confidence_score: float = Field(ge=0.0, le=1.0)
    keyword_score: float = Field(default=0.0, ge=0.0, le=1.0)
    semantic_score: float = Field(default=0.0, ge=0.0, le=1.0)
    reranker_score: float = Field(default=0.0, ge=0.0, le=1.0)
    source_id: Optional[str] = None
    page_number: Optional[int] = None
    content_type: Optional[str] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)


class RetrievalResponse(BaseModel):
    query: str
    retrieved_context: List[RetrievedChunk]


class HealthCheck(BaseModel):
    status: str
    vector_db_connected: bool
    openrouter_configured: bool
    details: Optional[str] = None
