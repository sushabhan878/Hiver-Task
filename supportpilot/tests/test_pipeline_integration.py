"""Integration test: full pipeline with mocked LLM client."""

import sys
from pathlib import Path
from unittest.mock import MagicMock

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.generation.generator import ReplyGenerator  # noqa: E402
from src.retrieval.bm25 import BM25Index  # noqa: E402
from src.retrieval.embeddings import EmbeddingIndex  # noqa: E402
from src.retrieval.hybrid import HybridRetriever  # noqa: E402
from src.routing.policy import RoutingPolicy  # noqa: E402
from src.taxonomy.classifier import IntentClassifier  # noqa: E402


def _mock_client():
    client = MagicMock()

    # deterministic fake embeddings: refund-ish -> axis 0, delivery -> axis 1
    def embed(texts):
        out = []
        for t in texts:
            t = t.lower()
            if "refund" in t or "money back" in t:
                out.append([1.0, 0.0, 0.0])
            elif "not arrived" in t or "stuck" in t or "late" in t:
                out.append([0.1, 1.0, 0.0])
            elif "where is my order" in t or "tracking" in t or "shipped" in t:
                out.append([0.1, 0.5, 0.3])
            else:
                out.append([0.0, 0.0, 1.0])
        return out

    client.embed = embed
    client.chat_model = "mock"
    client.stats = {"chat_calls": 0, "chat_cached": 0, "embed_calls": 0, "embed_cached": 0}

    def chat_json(msgs, **kw):
        text = msgs[-1]["content"]
        if "Classify" in text:
            if "not arrived" in text or "stuck" in text:
                return {"intent": "delayed_delivery"}
            if "refund" in text or "money back" in text:
                return {"intent": "refund_request"}
            if "where is my order" in text:
                return {"intent": "delivery_status"}
            return {"intent": "other"}
        return {
            "reply": "Sorry to hear! Please DM us your order number so we can look into this.",
            "supporting_case_ids": ["c1"],
            "grounded_claims": ["DM requested"],
            "sufficient_evidence": True,
        }

    client.chat_json = MagicMock(side_effect=chat_json)
    return client


CASES = [
    {
        "case_id": "c1",
        "customer_problem": "my package has not arrived and tracking is stuck",
        "brand_response": "Sorry! Please DM your order number.",
        "resolution_type": "asked_to_dm",
        "intent": "delayed_delivery",
    },
    {
        "case_id": "c1b",
        "customer_problem": "order stuck in transit late delivery",
        "brand_response": "Apologies! DM us your order id to check.",
        "resolution_type": "asked_to_dm",
        "intent": "delayed_delivery",
    },
    {
        "case_id": "c1c",
        "customer_problem": "my late order still has not arrived",
        "brand_response": "Sorry about that! Please DM your order number.",
        "resolution_type": "asked_to_dm",
        "intent": "delayed_delivery",
    },
    {
        "case_id": "c2",
        "customer_problem": "I want a refund for my broken item",
        "brand_response": "We can help, DM your order id.",
        "resolution_type": "asked_to_dm",
        "intent": "refund_request",
    },
    {
        "case_id": "c3",
        "customer_problem": "how do I reset my password",
        "brand_response": "Use the Forgot Password link.",
        "resolution_type": "directed_to_help",
        "intent": "account_access",
    },
]

BANK = [
    {"intent": "delayed_delivery", "text": "my package has not arrived and tracking is stuck"},
    {"intent": "refund_request", "text": "I want a refund for my broken item"},
    {"intent": "account_access", "text": "how do I reset my password"},
    {"intent": "delivery_status", "text": "where is my order"},
    {"intent": "general_info", "text": "how does prime shipping work"},
]


def _build():
    client = _mock_client()
    retriever = HybridRetriever.__new__(HybridRetriever)
    retriever.cfg = {
        "top_k": 3,
        "bm25_weight": 0.45,
        "embedding_weight": 0.55,
        "min_score": 0.35,
        "strong_match_score": 0.55,
    }
    retriever.cases = CASES
    retriever.case_texts = [c["customer_problem"] for c in CASES]
    retriever.bm25 = BM25Index(retriever.case_texts)
    retriever.emb = EmbeddingIndex(client, retriever.case_texts)
    clf = IntentClassifier(client, BANK)
    clf.build_bank()
    gen = ReplyGenerator(client)
    policy = RoutingPolicy()
    return client, retriever, clf, gen, policy


def test_pipeline_delivery_auto_handle():
    from src.pipeline import SupportPilotAgent

    client, retriever, clf, gen, policy = _build()
    agent = SupportPilotAgent(
        clf, retriever, gen, policy, {"retrieval": {"strong_match_score": 0.55}}
    )
    # mock embed maps anything with "not arrived"/"stuck"/"late" to the same
    # vector as the delayed_delivery bank entry -> consistent evidence
    trace = agent.handle("my order is stuck and has not arrived")
    assert trace["intent"]["label"] == "delayed_delivery"
    assert trace["routing"]["decision"] == "auto_handle"
    assert trace["generation"]["reply"]
    assert trace["retrieval"]["case_ids"]


def test_pipeline_refund_escalates():
    from src.pipeline import SupportPilotAgent

    client, retriever, clf, gen, policy = _build()
    agent = SupportPilotAgent(
        clf, retriever, gen, policy, {"retrieval": {"strong_match_score": 0.55}}
    )
    trace = agent.handle("I want a refund for my broken item")
    assert trace["intent"]["label"] == "refund_request"
    assert trace["routing"]["decision"] == "escalate"
    assert trace["routing"]["reason"] == "HIGH_RISK_INTENT"


def test_pipeline_trace_complete():
    from src.pipeline import SupportPilotAgent

    client, retriever, clf, gen, policy = _build()
    agent = SupportPilotAgent(
        clf, retriever, gen, policy, {"retrieval": {"strong_match_score": 0.55}}
    )
    trace = agent.handle("where is my order")
    for key in ("request_id", "input", "intent", "retrieval", "generation", "routing"):
        assert key in trace
    assert "score" in trace["routing"]
    assert trace["intent"]["confidence"] >= 0


def test_pipeline_empty_input_abstains():
    from src.pipeline import SupportPilotAgent

    client, retriever, clf, gen, policy = _build()
    agent = SupportPilotAgent(
        clf, retriever, gen, policy, {"retrieval": {"strong_match_score": 0.55}}
    )
    for blank in ("", "   ", "\n\t "):
        trace = agent.handle(blank)
        assert trace["routing"]["decision"] == "escalate"
        assert trace["routing"]["reason"] == "INSUFFICIENT_CUSTOMER_CONTEXT"
        assert trace["generation"]["reply"] == ""
