"""Baselines: majority+canned, BM25-nearest, LLM-without-retrieval."""

from __future__ import annotations

from collections import Counter

from src.llm.client import OllamaClient
from src.retrieval.bm25 import BM25Index

CANNED_REPLY = (
    "Thanks for reaching out! We've noted your message and a member of our "
    "support team will look into it shortly."
)


class MajorityCannedBaseline:
    """Baseline 1: predicts the majority intent, canned reply, always escalates."""

    def __init__(self, train_intents: list[str]):
        counts = Counter(train_intents)
        self.majority_intent = counts.most_common(1)[0][0] if counts else "general_info"

    def handle(self, customer_message: str) -> dict:
        return {
            "intent": self.majority_intent,
            "confidence": 1.0,
            "action": "escalate",
            "reason": "BASELINE_ALWAYS_ESCALATE",
            "reply": CANNED_REPLY,
            "evidence_ids": [],
        }


class BM25NearestBaseline:
    """Baseline 2: nearest historical case by BM25; returns its brand response."""

    def __init__(self, cases: list[dict]):
        self.cases = cases
        self.index = BM25Index([c["customer_problem"] for c in cases])

    def handle(self, customer_message: str) -> dict:
        hits = self.index.search(customer_message, 1)
        if not hits:
            return {
                "intent": "other",
                "confidence": 0.0,
                "action": "escalate",
                "reason": "NO_RETRIEVAL_MATCH",
                "reply": CANNED_REPLY,
                "evidence_ids": [],
            }
        idx, score = hits[0]
        case = self.cases[idx]
        return {
            "intent": case.get("intent", "other"),
            "confidence": min(score / 20.0, 1.0),  # raw BM25 score heuristic
            "action": "auto_handle",
            "reason": None,
            "reply": case["brand_response"],
            "evidence_ids": [case["case_id"]],
        }


NO_RETRIEVAL_SYSTEM_PROMPT = (
    "You are a customer-support assistant for AmazonHelp. Answer the customer "
    "directly using your general knowledge. Be concise (2-3 sentences). Do not "
    "invent policies or refund amounts. Reply with JSON only: "
    '{"reply": "...", "intent": "..."}'
)


class LLMNoRetrievalBaseline:
    """Baseline 3 (optional): pure LLM, no historical evidence."""

    def __init__(self, client: OllamaClient, intents: list[str]):
        self.client = client
        self.intents = intents

    def handle(self, customer_message: str) -> dict:
        user = (
            f"Customer message: {customer_message}\n\n"
            f"Classify the intent (one of: {', '.join(self.intents)}) and write a helpful reply. "
            "Reply with JSON only: "
            '{"reply": "...", "intent": "...", "confidence": 0.0}'
        )
        try:
            out = self.client.chat_json(
                [
                    {"role": "system", "content": NO_RETRIEVAL_SYSTEM_PROMPT},
                    {"role": "user", "content": user},
                ],
                num_predict=300,
            )
            return {
                "intent": str(out.get("intent", "other")),
                "confidence": float(out.get("confidence", 0.5)),
                "action": "auto_handle",
                "reason": None,
                "reply": str(out.get("reply", "")).strip(),
                "evidence_ids": [],
            }
        except Exception:
            return {
                "intent": "other",
                "confidence": 0.0,
                "action": "escalate",
                "reason": "LLM_PARSE_FAILED",
                "reply": "",
                "evidence_ids": [],
            }
