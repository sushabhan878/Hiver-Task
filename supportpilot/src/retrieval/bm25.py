"""Minimal BM25 (Okapi) implementation over normalized case text."""

from __future__ import annotations

import math
import re
from collections import Counter

TOKEN_RE = re.compile(r"[a-z0-9#]+")


def tokenize(text: str) -> list[str]:
    return TOKEN_RE.findall(text.lower())


class BM25Index:
    def __init__(self, docs: list[str], k1: float = 1.5, b: float = 0.75):
        self.k1 = k1
        self.b = b
        self.doc_tokens = [tokenize(d) for d in docs]
        self.doc_tf: list[Counter] = [Counter(toks) for toks in self.doc_tokens]
        self.doc_len = [len(toks) for toks in self.doc_tokens]
        self.n = len(docs)
        self.avgdl = sum(self.doc_len) / self.n if self.n else 0.0
        df: Counter = Counter()
        for tf in self.doc_tf:
            for term in tf:
                df[term] += 1
        self.idf = {t: math.log((self.n - d + 0.5) / (d + 0.5) + 1.0) for t, d in df.items()}

    def score(self, query: str, idx: int) -> float:
        q_tokens = tokenize(query)
        tf = self.doc_tf[idx]
        dl = self.doc_len[idx]
        s = 0.0
        for t in q_tokens:
            if t not in tf:
                continue
            idf = self.idf.get(t, 0.0)
            f = tf[t]
            denom = f + self.k1 * (1 - self.b + self.b * dl / (self.avgdl or 1))
            s += idf * f * (self.k1 + 1) / denom
        return s

    def search(self, query: str, top_k: int) -> list[tuple[int, float]]:
        """Brute-force scores; corpus is capped at ~8k cases for speed."""
        scored = [(i, self.score(query, i)) for i in range(self.n)]
        scored = [x for x in scored if x[1] > 0]
        scored.sort(key=lambda x: -x[1])
        return scored[:top_k]
