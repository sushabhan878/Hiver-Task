"""Intent classifier: embedding nearest-example voting + LLM fallback for ambiguity.

Option C (hybrid) from the PRD, kept simple:
- a labelled example bank (per-intent positives from the golden-labelled
  retrieval split) provides embedding neighbors;
- kNN vote gives scores + margin;
- ambiguous cases (low margin) are resolved by a single LLM call.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from src.config import config, intents_cfg, thresholds_cfg
from src.llm.client import OllamaClient


@dataclass
class IntentPrediction:
    intent: str
    confidence: float
    scores: dict[str, float]
    margin: float
    retrieval_consistency: float = 0.0
    used_llm: bool = False


class IntentClassifier:
    def __init__(
        self,
        client: OllamaClient,
        example_bank: list[dict] | None = None,
        cfg: dict | None = None,
        icfg: dict | None = None,
        tcfg: dict | None = None,
    ):
        self.client = client
        self.cfg = cfg or config()
        self.icfg = icfg or intents_cfg()
        self.tcfg = tcfg or thresholds_cfg()
        self.intents = list(self.icfg["intents"].keys())
        # example bank: [{"intent": ..., "text": ...}]
        self.bank: list[dict] = example_bank or []
        self.bank_embs: np.ndarray | None = None
        self.bank_intents: list[str] = []

    # ------------------------------------------------------------------ setup
    def build_bank(self) -> None:
        texts = [b["text"] for b in self.bank]
        embs = self.client.embed(texts) if texts else []
        self.bank_embs = np.array(embs, dtype=np.float32) if embs else None
        self.bank_intents = [b["intent"] for b in self.bank]

    # --------------------------------------------------------------- predict
    def knn_scores(self, text: str, k: int = 5) -> tuple[dict[str, float], float]:
        """Returns (normalized per-intent scores, top margin)."""
        if self.bank_embs is None or len(self.bank) == 0:
            return {i: 1.0 / len(self.intents) for i in self.intents}, 0.0
        q = np.array(self.client.embed([text])[0], dtype=np.float32)
        q = q / (np.linalg.norm(q) + 1e-9)
        bank = self.bank_embs / (np.linalg.norm(self.bank_embs, axis=1, keepdims=True) + 1e-9)
        sims = bank @ q
        top = np.argsort(-sims)[:k]
        scores: dict[str, float] = dict.fromkeys(self.intents, 0.0)
        total = 0.0
        for idx in top:
            w = float(sims[idx])
            if w <= 0:
                continue
            scores[self.bank_intents[idx]] += w
            total += w
        if total > 0:
            scores = {i: s / total for i, s in scores.items()}
        sorted_scores = sorted(scores.values(), reverse=True)
        margin = sorted_scores[0] - (sorted_scores[1] if len(sorted_scores) > 1 else 0.0)
        return scores, margin

    def predict(
        self, text: str, retrieved_intents: list[str] | None = None, use_llm_fallback: bool = True
    ) -> IntentPrediction:
        scores, margin = self.knn_scores(text)
        top2 = sorted(scores.items(), key=lambda x: -x[1])[:2]
        top_intent, top_score = top2[0]

        # retrieval consistency: fraction of retrieved cases with predicted intent
        consistency = 0.0
        if retrieved_intents:
            same = sum(1 for i in retrieved_intents if i == top_intent)
            consistency = same / len(retrieved_intents)

        w = self.tcfg["intent_confidence_weights"]
        confidence = (
            w["classifier_confidence"] * top_score
            + w["top_intent_margin"] * margin
            + w["retrieval_consistency"] * consistency
        )

        used_llm = False
        if use_llm_fallback and margin < 0.15 and top_score < 0.6:
            llm_intent = self._llm_classify(text)
            if llm_intent in scores:
                top_intent = llm_intent
                used_llm = True
                # LLM agreed label: when it confirms the kNN top-1, treat the
                # agreement as evidence (floor 0.65); disagreement keeps raw score
                llm_score = max(
                    scores[llm_intent], 0.70 if llm_intent == top_intent else scores[llm_intent]
                )
                confidence = (
                    w["classifier_confidence"] * llm_score
                    + w["top_intent_margin"] * margin
                    + w["retrieval_consistency"] * consistency
                )

        return IntentPrediction(
            intent=top_intent,
            confidence=round(min(confidence, 1.0), 4),
            scores={i: round(s, 4) for i, s in scores.items()},
            margin=round(margin, 4),
            retrieval_consistency=round(consistency, 4),
            used_llm=used_llm,
        )

    def _llm_classify(self, text: str) -> str:
        taxonomy_lines = []
        for name, spec in self.icfg["intents"].items():
            taxonomy_lines.append(f"- {name}: {spec['definition']}")
        prompt = (
            "Classify this customer support message into exactly one intent.\n\n"
            "Intents:\n" + "\n".join(taxonomy_lines) + "\n\n"
            f"Customer message: {text}\n\n"
            'Reply with JSON only: {"intent": "<name>"}'
        )
        try:
            out = self.client.chat_json([{"role": "user", "content": prompt}], num_predict=64)
            return str(out.get("intent", "other"))
        except Exception:
            return "other"
