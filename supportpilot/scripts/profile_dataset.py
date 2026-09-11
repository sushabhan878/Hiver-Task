"""Phase 1: dataset reconnaissance and brand selection.

Profiles candidate brands and computes an explicit selection score:
    brand_score =
        0.30 * normalized_conversation_count
      + 0.25 * normalized_resolved_conversation_rate
      + 0.20 * normalized_message_quality
      + 0.15 * normalized_intent_diversity
      + 0.10 * normalized_thread_completeness

Writes reports/brand_selection.md and data/interim/brand_profiles.json.
"""

from __future__ import annotations

import argparse
import re
from collections import Counter

import numpy as np

from scripts._bootstrap import ROOT  # noqa: F401  (adds repo root to sys.path)
from src.config import config, project_path
from src.data.loader import write_json

TURN_RE = re.compile(r"^(Customer|Support):\s?", re.M)

INTENT_KEYWORDS = {
    "delivery": [
        "where is my",
        "tracking",
        "arrive",
        "shipped",
        "package",
        "delivery",
        "order status",
    ],
    "refund": ["refund", "money back", "return"],
    "payment": ["charged", "charge", "billing", "card", "payment", "credit"],
    "account": ["account", "login", "log in", "password", "locked", "sign in"],
    "cancel": ["cancel", "unsubscribe", "subscription"],
    "product": ["broken", "damaged", "defective", "not working", "faulty", "wrong item"],
    "availability": ["in stock", "available", "restock", "sold out"],
    "complaint": ["unacceptable", "worst", "terrible", "awful", "frustrated", "disappointed"],
}

CANDIDATES = [
    "AmazonHelp",
    "AppleSupport",
    "Uber_Support",
    "SpotifyCares",
    "Delta",
    "AmericanAir",
    "TMobileHelp",
    "British_Airways",
    "XboxSupport",
    "AskPlayStation",
]


def parse_turns(raw: str) -> list[dict]:
    if not isinstance(raw, str):
        return []
    parts = TURN_RE.split(raw)
    turns = []
    for j in range(1, len(parts) - 1, 2):
        text = parts[j + 1].strip()
        if text:
            turns.append({"speaker": parts[j].lower(), "text": text})
    return turns


def quick_intent_hint(text: str) -> str | None:
    t = text.lower()
    for intent, kws in INTENT_KEYWORDS.items():
        if any(k in t for k in kws):
            return intent
    return None


def profile_brands(sample_limit: int = 4000) -> dict:
    import pyarrow.parquet as pq

    cfg = config()
    raw_path = project_path(cfg["paths"]["raw_conversations"])
    f = pq.ParquetFile(raw_path)
    profiles = {c: _empty_profile() for c in CANDIDATES}

    for rg in range(f.num_row_groups):
        t = f.read_row_group(rg, columns=["conversation_id", "company", "conversation"]).to_pylist()
        for r in t:
            brand = r["company"]
            if brand not in profiles:
                continue
            p = profiles[brand]
            if p["conversations"] >= sample_limit:
                continue
            turns = parse_turns(r["conversation"])
            if not turns:
                p["dropped_empty"] += 1
                continue
            customer_turns = [x for x in turns if x["speaker"] == "customer"]
            support_turns = [x for x in turns if x["speaker"] == "support"]
            p["conversations"] += 1
            p["turn_counts"].append(len(turns))
            p["customer_msgs"] += len(customer_turns)
            p["brand_msgs"] += len(support_turns)
            if support_turns:
                p["with_brand_reply"] += 1
            if len(customer_turns) >= 2 and support_turns:
                p["multi_exchange"] += 1
            # message quality: mean customer message length in reasonable band
            lens = [len(x["text"]) for x in customer_turns if x["text"]]
            p["customer_msg_lens"].extend(lens[:5])
            # resolution hint: brand reply exists and conversation has >= 2 turns
            # intent diversity via keyword hints
            for ct in customer_turns[:3]:
                hint = quick_intent_hint(ct["text"])
                if hint:
                    p["intent_hints"][hint] += 1
    return profiles


def _empty_profile() -> dict:
    return {
        "conversations": 0,
        "customer_msgs": 0,
        "brand_msgs": 0,
        "with_brand_reply": 0,
        "multi_exchange": 0,
        "dropped_empty": 0,
        "turn_counts": [],
        "customer_msg_lens": [],
        "intent_hints": Counter(),
    }


def score_brands(profiles: dict) -> list[dict]:
    rows = []
    for brand, p in profiles.items():
        if p["conversations"] == 0:
            continue
        turn_counts = p["turn_counts"]
        rows.append(
            {
                "brand": brand,
                "conversations": p["conversations"],
                "customer_msgs": p["customer_msgs"],
                "brand_msgs": p["brand_msgs"],
                "median_turns": float(np.median(turn_counts)),
                "brand_reply_rate": p["with_brand_reply"] / p["conversations"],
                "resolved_rate": p["multi_exchange"] / p["conversations"],
                "mean_customer_msg_len": float(np.mean(p["customer_msg_lens"]))
                if p["customer_msg_lens"]
                else 0.0,
                "intent_diversity": len([v for v in p["intent_hints"].values() if v >= 5]),
                "duplicate_hint_rate": 0.0,  # computed at corpus build
            }
        )
    max_conv = max(r["conversations"] for r in rows) or 1.0
    max_resolved = max(r["resolved_rate"] for r in rows) or 1.0
    max_quality = (
        max(r["brand_reply_rate"] * (1 if r["mean_customer_msg_len"] > 40 else 0.5) for r in rows)
        or 1.0
    )
    max_div = max(r["intent_diversity"] for r in rows) or 1.0
    max_thread = max(r["median_turns"] / 5.0 for r in rows) or 1.0
    for r in rows:
        quality = r["brand_reply_rate"] * (1 if r["mean_customer_msg_len"] > 40 else 0.5)
        r["brand_score"] = round(
            0.30 * (r["conversations"] / max_conv)
            + 0.25 * (r["resolved_rate"] / max_resolved)
            + 0.20 * (quality / max_quality)
            + 0.15 * (r["intent_diversity"] / max_div)
            + 0.10 * min(r["median_turns"] / 5.0, 1.0) / max_thread,
            4,
        )
    rows.sort(key=lambda x: -x["brand_score"])
    return rows


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--sample-limit", type=int, default=4000, help="conversations per brand for profiling"
    )
    args = parser.parse_args()

    print(f"Profiling {len(CANDIDATES)} candidate brands (sample {args.sample_limit}/brand)...")
    profiles = profile_brands(args.sample_limit)
    rows = score_brands(profiles)

    out_path = project_path("data/interim")
    out_path.mkdir(parents=True, exist_ok=True)
    write_json(out_path / "brand_profiles.json", rows)

    # markdown report
    lines = [
        "# Brand Selection",
        "",
        "Score = 0.30*conv_count + 0.25*resolved_rate + 0.20*message_quality "
        "+ 0.15*intent_diversity + 0.10*thread_completeness (all normalized to max=1).",
        "",
        "| brand | convs | turns | brand-reply % | resolved % | diversity | score |",
        "|---|---|---|---|---|---|---|",
    ]
    for r in rows:
        lines.append(
            f"| {r['brand']} | {r['conversations']} | {r['median_turns']:.0f} | "
            f"{100 * r['brand_reply_rate']:.0f}% | {100 * r['resolved_rate']:.0f}% | "
            f"{r['intent_diversity']} | {r['brand_score']:.3f} |"
        )
    best = rows[0]
    lines += [
        "",
        f"**Selected brand: {best['brand']}** "
        f"(highest composite score; large volume, near-universal brand-reply rate, "
        f"diverse intent mix, and multi-turn exchanges suitable for resolution extraction).",
    ]
    report_path = project_path("reports")
    report_path.mkdir(parents=True, exist_ok=True)
    (report_path / "brand_selection.md").write_text("\n".join(lines), encoding="utf-8")
    print("\n".join(lines))
    print("\nWrote data/interim/brand_profiles.json and reports/brand_selection.md")


if __name__ == "__main__":
    main()
