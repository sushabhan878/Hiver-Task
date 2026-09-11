"""Hybrid retrieval: 0.45 * BM25 + 0.55 * embedding similarity (both normalized)."""

from __future__ import annotations

from dataclasses import dataclass

from src.config import config
from src.retrieval.bm25 import BM25Index
from src.retrieval.embeddings import EmbeddingIndex


@dataclass
class RetrievedCase:
    case_id: str
    score: float
    bm25_score: float
    emb_score: float
    case: dict


class HybridRetriever:
    def __init__(
        self,
        cases: list[dict],
        cfg: dict | None = None,
        bm25_index: BM25Index | None = None,
        emb_index: EmbeddingIndex | None = None,
    ):
        self.cfg = (cfg or config())["retrieval"]
        self.cases = cases
        self.case_texts = [c["customer_problem"] for c in cases]
        self.bm25 = bm25_index or BM25Index(self.case_texts)
        from src.llm.client import get_client

        self.emb = emb_index or EmbeddingIndex(
            get_client(), self.case_texts, case_ids=[c["case_id"] for c in cases]
        )

    def search(self, query: str, top_k: int | None = None) -> list[RetrievedCase]:
        k = top_k or self.cfg["top_k"]
        # fetch 3x candidates from each side for the fusion pool
        pool_k = min(len(self.cases), max(k * 3, 15))
        bm25_hits = self.bm25.search(query, pool_k)
        emb_hits = self.emb.search(query, pool_k)

        max_bm25 = max((s for _, s in bm25_hits), default=0.0) or 1.0
        max_emb = max((s for _, s in emb_hits), default=0.0) or 1.0

        fused: dict[int, dict[str, float]] = {}
        for i, s in bm25_hits:
            fused.setdefault(i, {"bm25": s / max_bm25, "emb": 0.0})["bm25"] = s / max_bm25
        for i, s in emb_hits:
            fused.setdefault(i, {"bm25": 0.0, "emb": s})["emb"] = s / max_emb

        w_bm25 = self.cfg["bm25_weight"]
        w_emb = self.cfg["embedding_weight"]
        scored = [
            (i, w_bm25 * v["bm25"] + w_emb * v["emb"], v["bm25"], v["emb"])
            for i, v in fused.items()
        ]
        scored.sort(key=lambda x: -x[1])
        results = []
        for i, score, b, e in scored[:k]:
            results.append(
                RetrievedCase(
                    case_id=self.cases[i]["case_id"],
                    score=round(score, 4),
                    bm25_score=round(b, 4),
                    emb_score=round(e, 4),
                    case=self.cases[i],
                )
            )
        return results

    def retrieval_confidence(self, hits: list[RetrievedCase]) -> float:
        """Confidence from hit scores: top score scaled, saturating near 0.8."""
        if not hits:
            return 0.0
        best = hits[0].score
        return round(min(best / 0.8, 1.0), 4)
