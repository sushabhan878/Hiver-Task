"""Leakage-safe, conversation-level splits.

The TNE-AI mirror does not include timestamps, so a true time-aware split is
not possible; we document this and instead use a deterministic hash-based
conversation-level split (see decision log). The split unit is the whole
conversation, so no conversation can straddle retrieval/eval corpora.
"""
from __future__ import annotations

import hashlib


def split_bucket(conversation_id: str, seed: int, retrieval_frac: float,
                 validation_frac: float) -> str:
    """Deterministically map a conversation to retrieval/validation/golden_pool.

    Uses sha1(seed + conversation_id) so the split is stable across machines
    and independent of row order.
    """
    h = hashlib.sha1(f"{seed}:{conversation_id}".encode("utf-8")).hexdigest()
    x = int(h[:8], 16) / 0xFFFFFFFF  # [0, 1)
    if x < retrieval_frac:
        return "retrieval"
    if x < retrieval_frac + validation_frac:
        return "validation"
    return "golden_pool"


def check_leakage(retrieval_ids: set[str], eval_ids: set[str]) -> dict:
    overlap = retrieval_ids & eval_ids
    return {
        "n_overlap": len(overlap),
        "overlap_ids": sorted(overlap)[:20],
        "leakage_free": len(overlap) == 0,
    }


def check_text_leakage(retrieval_texts: list[str], eval_texts: list[str],
                       ngram: int = 5, threshold: float = 0.8) -> dict:
    """Near-duplicate leakage check: per-text comparison against every
    retrieval text (a pooled signature union would falsely flag all generic
    support phrases at corpus scale)."""
    def signatures(text: str) -> set[str]:
        t = "".join(text.lower().split())
        return {t[i:i + ngram] for i in range(max(0, len(t) - ngram + 1))}

    retrieval_sigs = [signatures(t) for t in retrieval_texts[:20000]]
    hits = 0
    examples: list[str] = []
    for t in eval_texts[:2000]:
        sigs = signatures(t)
        if not sigs:
            continue
        for rs in retrieval_sigs:
            if len(sigs & rs) / len(sigs) > threshold:
                hits += 1
                if len(examples) < 5:
                    examples.append(t[:120])
                break
    return {
        "near_duplicate_hits": hits,
        "checked_eval": min(len(eval_texts), 2000),
        "examples": examples,
        "leakage_free": hits == 0,
    }
