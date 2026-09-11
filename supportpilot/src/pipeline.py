"""End-to-end agent pipeline: classify -> retrieve -> generate -> route."""

from __future__ import annotations

import time
import uuid

from src.config import config
from src.generation.generator import ReplyGenerator
from src.retrieval.hybrid import HybridRetriever
from src.routing.policy import RoutingPolicy, RoutingSignals
from src.taxonomy.classifier import IntentClassifier

REASON_INSUFFICIENT_CONTEXT = "INSUFFICIENT_CUSTOMER_CONTEXT"


class SupportPilotAgent:
    def __init__(
        self,
        classifier: IntentClassifier,
        retriever: HybridRetriever,
        generator: ReplyGenerator,
        policy: RoutingPolicy,
        cfg: dict | None = None,
    ):
        self.classifier = classifier
        self.retriever = retriever
        self.generator = generator
        self.policy = policy
        self.cfg = cfg or config()

    def handle(self, customer_message: str) -> dict:
        t0 = time.time()
        request_id = str(uuid.uuid4())[:8]

        # 0. abstention gate: empty/blank input can never be safely automated
        if not isinstance(customer_message, str) or not customer_message.strip():
            trace = {
                "request_id": request_id,
                "input": customer_message if isinstance(customer_message, str) else "",
                "intent": {
                    "label": "other",
                    "confidence": 0.0,
                    "margin": 0.0,
                    "retrieval_consistency": 0.0,
                    "used_llm_fallback": False,
                    "scores": {},
                },
                "retrieval": {"top_k": 0, "best_score": 0.0, "case_ids": [], "cases": []},
                "generation": {
                    "model": self.generator.client.chat_model,
                    "temperature": 0,
                    "prompt_version": "n/a",
                    "reply": "",
                    "supporting_case_ids": [],
                    "grounded_claims": [],
                    "sufficient_evidence": False,
                    "parse_failed": False,
                },
                "routing": {
                    "decision": "escalate",
                    "score": 0.0,
                    "reason": REASON_INSUFFICIENT_CONTEXT,
                    "guardrail_flags": [],
                },
                "elapsed_ms": round((time.time() - t0) * 1000),
            }
            return trace

        # 1. retrieve first (needed for retrieval-consistency in confidence)
        hits = self.retriever.search(customer_message)
        retrieved_intents = [h.case.get("intent", "other") for h in hits]

        # 2. classify
        pred = self.classifier.predict(customer_message, retrieved_intents=retrieved_intents)

        # 3. generate
        gen = self.generator.generate(customer_message, pred.intent, [h.case for h in hits])

        # 4. route
        rconf = self.retriever.retrieval_confidence(hits)
        strong = any(h.score >= self.cfg["retrieval"]["strong_match_score"] for h in hits)
        groundedness = 0.5 if gen.sufficient_evidence else 0.3
        if gen.parse_failed or not gen.reply:
            groundedness = 0.0
        # deterministic guardrail pass first: safety enters the automation score
        from src.routing.policy import run_guardrails

        _, safety = run_guardrails(
            gen.reply,
            [h.case.get("brand_response", "") for h in hits],
            gen.supporting_case_ids,
        )
        signals = RoutingSignals(
            intent=pred.intent,
            intent_confidence=pred.confidence,
            retrieval_best_score=hits[0].score if hits else 0.0,
            retrieval_confidence=rconf,
            has_strong_match=strong,
            evidence_ids=gen.supporting_case_ids,
            evidence_texts=[h.case.get("brand_response", "") for h in hits],
            reply=gen.reply,
            generated_groundedness=groundedness,
            safety_score=safety,
        )
        decision = self.policy.decide(signals)

        # 5. trace (observability, PRD P5)
        trace = {
            "request_id": request_id,
            "input": customer_message,
            "intent": {
                "label": pred.intent,
                "confidence": pred.confidence,
                "margin": pred.margin,
                "retrieval_consistency": pred.retrieval_consistency,
                "used_llm_fallback": pred.used_llm,
                "scores": pred.scores,
            },
            "retrieval": {
                "top_k": len(hits),
                "best_score": hits[0].score if hits else 0.0,
                "case_ids": [h.case_id for h in hits],
                "cases": [
                    {
                        "case_id": h.case_id,
                        "score": h.score,
                        "bm25": h.bm25_score,
                        "emb": h.emb_score,
                        "intent": h.case.get("intent"),
                        "customer_problem": h.case.get("customer_problem"),
                        "brand_response": h.case.get("brand_response"),
                        "resolution_type": h.case.get("resolution_type"),
                    }
                    for h in hits
                ],
            },
            "generation": {
                "model": gen.model,
                "temperature": 0,
                "prompt_version": gen.prompt_version,
                "reply": gen.reply,
                "supporting_case_ids": gen.supporting_case_ids,
                "grounded_claims": gen.grounded_claims,
                "sufficient_evidence": gen.sufficient_evidence,
                "parse_failed": gen.parse_failed,
            },
            "routing": {
                "decision": decision.action,
                "score": round(decision.automation_score, 4),
                "reason": decision.reason,
                "guardrail_flags": decision.guardrail_flags,
            },
            "elapsed_ms": round((time.time() - t0) * 1000),
        }
        return trace
