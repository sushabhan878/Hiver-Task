"""Conversation reconstruction from the TNE-AI conversation-format mirror.

The upstream parquet stores each conversation as a single string:
    "Customer: ... | Support: ... | Customer: ..."
We parse it into structured turns, clean text, and drop unusable rows.
"""
from __future__ import annotations

import re

from src.data.cleaner import CleaningStats, clean_text, is_spam_or_bot

TURN_RE = re.compile(r"^(Customer|Support):\s?", re.M)


def parse_turns(raw: str) -> list[dict]:
    if not isinstance(raw, str):
        return []
    parts = TURN_RE.split(raw)
    turns = []
    for j in range(1, len(parts) - 1, 2):
        text = parts[j + 1].strip()
        if not text:
            continue
        turns.append({"speaker": parts[j].lower(), "text": text})
    return turns


def build_conversation_record(conv_id: str, company: str, raw: str,
                               stats: CleaningStats | None = None) -> dict | None:
    """Convert a raw conversation string into a structured record.

    Returns None for records that are unusable (no turns, no customer message,
    no brand reply, spam, or empty after cleaning).
    """
    turns = parse_turns(raw)
    if not turns:
        if stats:
            stats.dropped_empty += 1
        return None
    has_customer = any(t["speaker"] == "customer" for t in turns)
    has_support = any(t["speaker"] == "support" for t in turns)
    if not has_customer:
        if stats:
            stats.dropped_empty += 1
        return None

    cleaned_turns = []
    for t in turns:
        text = clean_text(t["text"], stats)
        if not text:
            continue
        cleaned_turns.append({"speaker": t["speaker"], "text": text})

    if not cleaned_turns or not any(t["speaker"] == "customer" for t in cleaned_turns):
        if stats:
            stats.dropped_empty += 1
        return None

    first_customer = next(t["text"] for t in cleaned_turns if t["speaker"] == "customer")
    if is_spam_or_bot(first_customer):
        if stats:
            stats.dropped_spam += 1
        return None

    return {
        "conversation_id": conv_id,
        "brand": company,
        "customer_messages": [t["text"] for t in cleaned_turns if t["speaker"] == "customer"],
        "brand_messages": [t["text"] for t in cleaned_turns if t["speaker"] == "support"],
        "turns": cleaned_turns,
        "has_brand_reply": has_support,
        "n_turns": len(cleaned_turns),
        "metadata": {},
    }
