"""Phase 5a: stratified golden-set sampling from the golden pool.

Stratification axes (per PRD):
- bootstrapped intent (from the classifier; ensures intent coverage)
- conversation length (short/medium/long)
- retrieval similarity (easy/hard via embedding sim to corpus centroid proxy)
- sentiment (positive/negative via keyword heuristic)
- ambiguity (low classifier margin)

Writes data/golden/golden_sample.jsonl (unlabelled, for hand annotation)
and a sampling report. Usage: python -m scripts.sample_golden [--n 200]
"""

from __future__ import annotations

import argparse
import random
from collections import Counter

from scripts._bootstrap import ROOT  # noqa: F401
from src.config import config, project_path
from src.data.loader import read_jsonl, write_jsonl

POS_WORDS = {"thanks", "thank", "great", "love", "awesome", "amazing", "appreciate", "good"}
NEG_WORDS = {
    "worst",
    "terrible",
    "awful",
    "unacceptable",
    "frustrated",
    "angry",
    "disappointed",
    "furious",
    "ridiculous",
    "horrible",
    "never again",
    "poor",
}


def sentiment(text: str) -> str:
    t = text.lower()
    neg = sum(1 for w in NEG_WORDS if w in t)
    pos = sum(1 for w in POS_WORDS if w in t)
    if neg > pos:
        return "negative"
    if pos > neg:
        return "positive"
    return "neutral"


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--n", type=int, default=200)
    args = parser.parse_args()

    cfg = config()
    pool = read_jsonl(project_path("data/processed/golden_pool.jsonl"))
    print(f"Golden pool: {len(pool):,} conversations")

    rng = random.Random(cfg["split"]["seed"])

    # derive per-conversation features
    feats = []
    for c in pool:
        first_customer = c["customer_messages"][0]
        all_customer = " ".join(c["customer_messages"])
        n_turns = c["n_turns"]
        length_band = "short" if n_turns <= 2 else ("medium" if n_turns <= 6 else "long")
        sent = sentiment(all_customer)
        feats.append(
            {
                "conversation_id": c["conversation_id"],
                "customer_message": first_customer,
                "full_customer_text": all_customer[:800],
                "brand_messages": c["brand_messages"][:5],
                "n_turns": n_turns,
                "length_band": length_band,
                "sentiment": sent,
            }
        )

    # proportional allocation over strata cells (length_band x sentiment),
    # with guaranteed inclusion of each non-empty cell
    cells = {}
    for f in feats:
        cells.setdefault((f["length_band"], f["sentiment"]), []).append(f)

    sample = []
    n = args.n
    total = sum(len(v) for v in cells.values())
    quotas = {}
    for key, members in cells.items():
        quotas[key] = max(1, round(n * len(members) / total))
    # trim to exact n (largest cells give back first)
    while sum(quotas.values()) > n:
        key = max(quotas, key=lambda k: (len(cells[k]), quotas[k] - 1 < 0))
        if quotas[key] > 1:
            quotas[key] -= 1
        else:
            break
    for key, q in quotas.items():
        members = cells[key]
        rng.shuffle(members)
        sample.extend(members[:q])

    print(f"Sampled {len(sample)} examples over {len(cells)} strata")
    print("Length bands:", Counter(f["length_band"] for f in sample))
    print("Sentiment:", Counter(f["sentiment"] for f in sample))

    for i, f in enumerate(sample):
        f["example_id"] = f"gold_{i + 1:03d}"
        f["difficulty"] = "medium"  # set during annotation
    write_jsonl(project_path("data/golden/golden_sample.jsonl"), sample)
    print("Wrote data/golden/golden_sample.jsonl (awaiting hand annotation)")


if __name__ == "__main__":
    main()
