"""Dense embedding index (cosine similarity) using Ollama nomic-embed-text."""

from __future__ import annotations

import numpy as np

from src.config import ROOT
from src.llm.client import OllamaClient

INDEX_CACHE = ROOT / "cache" / "index" / "cases_with_embeddings.npz"


class EmbeddingIndex:
    def __init__(self, client: OllamaClient, texts: list[str], case_ids: list[str] | None = None):
        self.client = client
        self.texts = texts
        self.matrix: np.ndarray | None = None
        if not texts:
            return
        # Reuse the committed precomputed matrix when it matches this corpus
        if case_ids is not None and INDEX_CACHE.exists():
            try:
                cached = np.load(INDEX_CACHE, allow_pickle=False)
                cached_ids = [str(x) for x in cached["case_ids"]]
                if cached_ids == case_ids:
                    m = cached["matrix"].astype(np.float32)
                    norms = np.linalg.norm(m, axis=1, keepdims=True) + 1e-9
                    self.matrix = m / norms
            except Exception:
                self.matrix = None
        if self.matrix is None:
            embs = client.embed(texts)
            m = np.array(embs, dtype=np.float32)
            norms = np.linalg.norm(m, axis=1, keepdims=True) + 1e-9
            self.matrix = m / norms

    def search(self, query: str, top_k: int) -> list[tuple[int, float]]:
        if self.matrix is None:
            return []
        q = np.array(self.client.embed([query])[0], dtype=np.float32)
        q = q / (np.linalg.norm(q) + 1e-9)
        sims = self.matrix @ q
        top = np.argsort(-sims)[:top_k]
        return [(int(i), float(sims[i])) for i in top]
