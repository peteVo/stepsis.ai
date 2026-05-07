from __future__ import annotations

from typing import List

from rank_bm25 import BM25Okapi


class KeywordIndex:
    def __init__(self, docs: List[str] | None = None) -> None:
        self._docs = docs or []
        tokenized = [doc.lower().split() for doc in self._docs]
        self._bm25 = BM25Okapi(tokenized) if tokenized else None

    def build(self, docs: List[str]) -> None:
        self._docs = docs
        tokenized = [doc.lower().split() for doc in docs]
        self._bm25 = BM25Okapi(tokenized) if tokenized else None

    def search(self, query: str, top_k: int = 10) -> List[int]:
        if self._bm25 is None:
            return []
        scores = self._bm25.get_scores(query.lower().split())
        ranked_indices = sorted(range(len(scores)), key=lambda idx: scores[idx], reverse=True)
        return ranked_indices[:top_k]
