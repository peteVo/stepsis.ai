from __future__ import annotations

from typing import Iterable, Sequence

from src.retrieval.models.schemas import RetrievedChunk, RetrievalResponse


class ResponseFormatter:
    """Formats retrieval output without altering source text or anchors."""

    def format_retrieval(self, query: str, retrieved_context: Sequence[RetrievedChunk]) -> RetrievalResponse:
        return RetrievalResponse(
            query=query,
            retrieved_context=[self._preserve_chunk(chunk) for chunk in retrieved_context],
        )

    def format_payload(self, query: str, retrieved_context: Sequence[RetrievedChunk]) -> dict:
        return self.format_retrieval(query, retrieved_context).model_dump()

    def _preserve_chunk(self, chunk: RetrievedChunk) -> RetrievedChunk:
        # Keep tables, line breaks, and punctuation intact for downstream extraction.
        return chunk


_response_formatter: ResponseFormatter | None = None


def get_response_formatter() -> ResponseFormatter:
    global _response_formatter
    if _response_formatter is None:
        _response_formatter = ResponseFormatter()
    return _response_formatter
