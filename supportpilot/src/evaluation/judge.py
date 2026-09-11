"""LLM-as-judge for reply quality (rubric scoring, structured output)."""

from __future__ import annotations

from src.evaluation.metrics import weighted_reply_score
from src.generation.prompts import JUDGE_PROMPT_VERSION, build_judge_prompt
from src.llm.client import OllamaClient

RUBRIC_KEYS = [
    "relevance",
    "groundedness",
    "actionability",
    "brand_consistency",
    "safety",
    "concision",
]


class LLMJudge:
    def __init__(
        self, client: OllamaClient, safety_min: float = 4.0, acceptability_min: float = 3.75
    ):
        self.client = client
        self.safety_min = safety_min
        self.acceptability_min = acceptability_min
        self.prompt_version = JUDGE_PROMPT_VERSION

    def judge(self, customer_message: str, cases: list[dict], reply: str) -> dict:
        if not reply or not reply.strip():
            return {
                "relevance": 1,
                "groundedness": 1,
                "actionability": 1,
                "brand_consistency": 1,
                "safety": 1,
                "concision": 1,
                "overall": 1.0,
                "reason": "empty or failed reply",
                "acceptable": False,
                "safe": False,
                "prompt_version": self.prompt_version,
                "parse_failed": True,
            }
        msgs = build_judge_prompt(customer_message, cases, reply)
        try:
            out = self.client.chat_json(msgs, num_predict=300)
            scores = {}
            for k in RUBRIC_KEYS:
                v = out.get(k, 3)
                try:
                    scores[k] = max(1, min(5, int(v)))
                except (TypeError, ValueError):
                    scores[k] = 3
            overall = weighted_reply_score(scores)
            safe = scores["safety"] >= self.safety_min
            acceptable = overall >= self.acceptability_min and safe
            return {
                **scores,
                "overall": overall,
                "reason": str(out.get("reason", ""))[:300],
                "acceptable": bool(acceptable),
                "safe": bool(safe),
                "prompt_version": self.prompt_version,
                "parse_failed": False,
            }
        except Exception as e:
            return {
                "relevance": 1,
                "groundedness": 1,
                "actionability": 1,
                "brand_consistency": 1,
                "safety": 1,
                "concision": 1,
                "overall": 1.0,
                "reason": f"judge error: {e}",
                "acceptable": False,
                "safe": False,
                "prompt_version": self.prompt_version,
                "parse_failed": True,
            }
