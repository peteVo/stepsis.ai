from __future__ import annotations

from typing import Dict, List


class RerankerService:
    # Placeholder
    async def rerank(self, query: str, candidates: List[Dict], top_k: int = 5) -> List[Dict]:
        _ = query
        return candidates[:top_k]
