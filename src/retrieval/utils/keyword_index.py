from __future__ import annotations

from typing import List, Sequence, Tuple

from rank_bm25 import BM25Okapi


def tokenize(text: str) -> List[str]:
    tokens: List[str] = []
    for raw_token in text.lower().split():
        token = "".join(char for char in raw_token if char.isalnum() or char in {"/", "-"})
        if token:
            tokens.append(token)
    return tokens


class KeywordIndex:
    def __init__(self, docs: Sequence[str] | None = None) -> None:
        self._docs = list(docs or [])
        self._tokenized = [tokenize(doc) for doc in self._docs]
        self._bm25 = BM25Okapi(self._tokenized) if self._tokenized else None

    def build(self, docs: Sequence[str]) -> None:
        self._docs = list(docs)
        self._tokenized = [tokenize(doc) for doc in self._docs]
        self._bm25 = BM25Okapi(self._tokenized) if self._tokenized else None

    def search(self, query: str, top_k: int = 10) -> List[Tuple[int, float]]:
        if self._bm25 is None:
            return []
        query_tokens = tokenize(query)
        if not query_tokens:
            return []
        scores = self._bm25.get_scores(query_tokens)
        ranked_indices = sorted(range(len(scores)), key=lambda idx: scores[idx], reverse=True)
        return [(index, float(scores[index])) for index in ranked_indices[:top_k]]

    def size(self) -> int:
        return len(self._docs)
