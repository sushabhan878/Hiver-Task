"""Phase 2: build the conversation corpus for the selected brand.

Steps:
1. Stream raw conversations for AmazonHelp, clean + thread them.
2. Assign leakage-safe conversation-level splits (hash-based; upstream has no
   timestamps, documented in decision log).
3. Extract historical resolution cases from retrieval-split conversations
   (rule-based resolution typing + heuristics; unclear ones are excluded).
4. Write: data/processed/{conversations,retrieval_cases,splits}.jsonl

Usage: python -m scripts.build_corpus [--max-conversations 8000]
"""

from __future__ import annotations

import argparse

from scripts._bootstrap import ROOT  # noqa: F401
from src.config import config, project_path
from src.data.cleaner import CleaningStats
from src.data.loader import write_jsonl
from src.data.splitter import split_bucket
from src.data.threading import build_conversation_record

RESOLUTION_TYPES = [
    (
        "asked_to_dm",
        [
            "dm us",
            "send us a dm",
            "dm with",
            "in a dm",
            "via dm",
            "direct message",
            "detailed information via dm",
            "info in a dm",
        ],
    ),
    ("provided_tracking_info", ["tracking", "tracking number", "shipment status"]),
    (
        "requested_details",
        [
            "order number",
            "order id",
            "account details",
            "provide us with",
            "send us the",
            "full name",
            "email address",
            "confirm your",
        ],
    ),
    (
        "directed_to_help",
        ["help page", "help center", "faq", "our site", "visit", "here's a link", "link here"],
    ),
    (
        "apologized_explained",
        [
            "sorry for",
            "we apologize",
            "apologies for",
            "we're sorry",
            "thanks for letting us know",
            "sorry about",
        ],
    ),
    (
        "explained_policy",
        [
            "policy",
            "we're unable to",
            "we can't",
            "we are unable",
            "unfortunately we",
            "not possible",
        ],
    ),
    (
        "confirmed_action",
        [
            "we've cancelled",
            "we canceled",
            "we've issued",
            "we've refunded",
            "we've processed",
            "we've sent",
            "we've escalated",
            "i've gone ahead",
            "we've reshipped",
            "we've replaced",
        ],
    ),
    (
        "escalated_internally",
        [
            "escalat",
            "forward this",
            "look into this right away",
            "looking into this",
            "pass this along",
            "flag this",
        ],
    ),
]


def classify_resolution(brand_messages: list[str]) -> str | None:
    """Rule-based resolution typing over the brand's reply messages."""
    text = " ".join(brand_messages).lower()
    if not text:
        return None
    for rtype, kws in RESOLUTION_TYPES:
        if any(k in text for k in kws):
            return rtype
    if len(text) >= 20:
        return "acknowledged_no_action"
    return None


def is_resolved(conversation: dict) -> bool:
    """A conversation is 'resolved' if the brand replied substantively at least once."""
    brand = conversation.get("brand_messages") or []
    return any(len(m) >= 15 for m in brand)


def extract_case(conversation: dict, intent: str | None) -> dict | None:
    """Derive a reusable historical case from a resolved conversation."""
    if not is_resolved(conversation):
        return None
    rtype = classify_resolution(conversation["brand_messages"])
    if rtype is None:
        return None
    customer_problem = " ".join(conversation["customer_messages"][:3])
    if not customer_problem or len(customer_problem) < 10:
        return None
    # brand response = first substantive brand message
    brand_response = next((m for m in conversation["brand_messages"] if len(m) >= 15), "")
    return {
        "case_id": f"case_{conversation['conversation_id'][:12]}",
        "source_conversation_id": conversation["conversation_id"],
        "customer_problem": customer_problem[:500],
        "brand_response": brand_response[:500],
        "resolution_type": rtype,
        "intent": intent or "unlabelled",
        "n_turns": conversation["n_turns"],
    }


def keyword_intent(text: str) -> str | None:
    """Cheap keyword-based intent hint used only to bootstrap corpus intents.

    The real taxonomy classifier runs later; this provides coarse corpus stats.
    """
    t = text.lower()
    rules = [
        ("refund_request", ["refund", "money back"]),
        (
            "payment_issue",
            [
                "charged twice",
                "double charg",
                "charged for",
                "billing",
                "credit card was",
                "card was charged",
                "promotional credit",
                "gift card balance",
            ],
        ),
        (
            "account_access",
            [
                "log in",
                "login",
                "locked out",
                "password",
                "sign in",
                "my account",
                "2fa",
                "two factor",
                "otp",
            ],
        ),
        (
            "cancellation",
            [
                "cancel my order",
                "cancel my prime",
                "cancel the order",
                "cancel my subscription",
                "unsubscribe",
                "cancel my membership",
            ],
        ),
        (
            "delivery_status",
            [
                "where is my order",
                "where's my order",
                "order status",
                "tracking",
                "when will my",
                "has my order shipped",
                "has it shipped",
                "has my package",
                "delivery date",
                "estimated delivery",
                "when will it arrive",
                "arrive",
            ],
        ),
        (
            "delayed_delivery",
            [
                "still hasn't arrived",
                "hasn't arrived",
                "has not arrived",
                "late",
                "delayed",
                "stuck in transit",
                "never came",
                "didn't arrive",
                "did not arrive",
                "waiting for my",
                "overdue",
                "days now",
            ],
        ),
        (
            "product_issue",
            [
                "broken",
                "damaged",
                "defective",
                "not working",
                "stopped working",
                "wrong item",
                "wrong size",
                "faulty",
                "missing part",
                "was empty",
                "leaked",
                "arrived open",
            ],
        ),
        (
            "pricing_charge",
            [
                "price",
                "how much is",
                "fee",
                "shipping cost",
                "why was i charged",
                "charged me",
                "overcharged",
            ],
        ),
        (
            "availability_question",
            ["in stock", "available", "restock", "when will you have", "sold out", "back in stock"],
        ),
        (
            "service_complaint",
            [
                "unacceptable",
                "worst",
                "terrible",
                "awful",
                "disgusting",
                "frustrated",
                "disappointed",
                "furious",
                "ridiculous",
                "never ordering again",
            ],
        ),
        (
            "feedback",
            [
                "thank you",
                "thanks for",
                "great service",
                "love amazon",
                "appreciate it",
                "good job",
            ],
        ),
        (
            "general_info",
            [
                "how do i",
                "does amazon",
                "can i",
                "is there a way",
                "how does",
                "what happens if",
                "do you offer",
                "do you ship",
            ],
        ),
    ]
    for intent, kws in rules:
        if any(k in t for k in kws):
            return intent
    return None


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--max-conversations", type=int, default=None)
    args = parser.parse_args()

    cfg = config()
    brand = cfg["brand"]["selected_brand"]
    max_conv = args.max_conversations or cfg["brand"]["max_conversations"]
    seed = cfg["split"]["seed"]
    rfrac = cfg["split"]["retrieval_frac"]
    vfrac = cfg["split"]["validation_frac"]

    from src.data.loader import load_raw_conversations

    print(f"Streaming raw conversations for {brand}...")
    raw_rows = load_raw_conversations(project_path(cfg["paths"]["raw_conversations"]), brand=brand)
    print(f"Found {len(raw_rows):,} raw conversations")

    stats = CleaningStats()
    conversations: list[dict] = []
    for r in raw_rows[: max_conv * 2] if max_conv else raw_rows:
        rec = build_conversation_record(
            r["conversation_id"], r["company"], r["conversation"], stats
        )
        if rec is None:
            continue
        if rec["n_turns"] < cfg["brand"]["min_turns"]:
            continue
        if rec["n_turns"] > cfg["brand"]["max_turns"]:
            continue
        rec["split"] = split_bucket(rec["conversation_id"], seed, rfrac, vfrac)
        conversations.append(rec)
        if len(conversations) >= max_conv:
            break

    print(
        f"Kept {len(conversations):,} conversations "
        f"(dropped empty={stats.dropped_empty}, spam={stats.dropped_spam})"
    )

    # split stats
    from collections import Counter

    split_counts = Counter(c["split"] for c in conversations)
    print("Split counts:", dict(split_counts))

    # extract historical cases from retrieval split only
    cases = []
    for c in conversations:
        if c["split"] != "retrieval":
            continue
        intent = keyword_intent(" ".join(c["customer_messages"][:3]))
        case = extract_case(c, intent)
        if case:
            cases.append(case)
    print(f"Extracted {len(cases):,} historical resolution cases from retrieval split")

    out = project_path("data/processed")
    out.mkdir(parents=True, exist_ok=True)
    write_jsonl(out / "conversations.jsonl", conversations)
    write_jsonl(out / "retrieval_cases.jsonl", cases)
    write_jsonl(
        out / "golden_pool.jsonl", [c for c in conversations if c["split"] == "golden_pool"]
    )
    write_jsonl(out / "validation.jsonl", [c for c in conversations if c["split"] == "validation"])

    # intent distribution of cases (bootstrapped via keywords)
    intent_counts = Counter(c["intent"] for c in cases)
    print("Case intent distribution (keyword bootstrap):", dict(intent_counts.most_common()))

    # quality checks
    from src.data.splitter import check_leakage

    retrieval_ids = {c["conversation_id"] for c in conversations if c["split"] == "retrieval"}
    golden_ids = {c["conversation_id"] for c in conversations if c["split"] == "golden_pool"}
    leak = check_leakage(retrieval_ids, golden_ids)
    print(f"Leakage check: overlap={leak['n_overlap']} leakage_free={leak['leakage_free']}")
    assert leak["leakage_free"], "LEAKAGE DETECTED - aborting"

    print("Wrote data/processed/{conversations,retrieval_cases,golden_pool,validation}.jsonl")


if __name__ == "__main__":
    main()
