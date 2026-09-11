import sys
from pathlib import Path
from unittest.mock import MagicMock

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


from src.retrieval.bm25 import BM25Index, tokenize  # noqa: E402
from src.retrieval.embeddings import EmbeddingIndex  # noqa: E402
from src.retrieval.hybrid import HybridRetriever  # noqa: E402


def _make_retriever(tmp_path=None):
    cases = [
        {
            "case_id": "c1",
            "customer_problem": "my package has not arrived and tracking is stuck",
            "brand_response": "Sorry! Please DM your order number.",
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
        {
            "case_id": "c4",
            "customer_problem": "where is my order it says shipped",
            "brand_response": "Let's check, DM your order details.",
            "resolution_type": "requested_details",
            "intent": "delivery_status",
        },
    ]
    client = MagicMock()

    def emb(texts):
        table = {
            "my package has not arrived and tracking is stuck": [1, 0, 0],
            "I want a refund for my broken item": [0, 1, 0],
            "how do I reset my password": [0, 0, 1],
            "where is my order it says shipped": [0.9, 0.1, 0.05],
        }
        return [table.get(t, [0.33, 0.33, 0.33]) for t in texts]

    client.embed = emb
    client.stats = {"embed_calls": 0, "embed_cached": 0}
    r = HybridRetriever.__new__(HybridRetriever)
    r.cfg = {
        "top_k": 3,
        "bm25_weight": 0.45,
        "embedding_weight": 0.55,
        "min_score": 0.35,
        "strong_match_score": 0.55,
    }
    r.cases = cases
    r.case_texts = [c["customer_problem"] for c in cases]
    r.bm25 = BM25Index(r.case_texts)
    r.emb = EmbeddingIndex(client, r.case_texts)
    return r


def test_tokenize():
    assert tokenize("Where IS my Order-123?") == ["where", "is", "my", "order", "123"]


def test_bm25_ranks_relevant_first():
    idx = BM25Index(["my package is late", "i want a refund", "password reset help"])
    hits = idx.search("my package is late", 2)
    assert hits[0][0] == 0


def test_bm25_no_match_returns_empty():
    idx = BM25Index(["alpha beta", "gamma delta"])
    assert idx.search("zzz qqq", 3) == []


def test_hybrid_prefers_similar_case():
    r = _make_retriever()
    hits = r.search("my package has not arrived and tracking is stuck")
    assert hits[0].case_id == "c1"
    assert hits[0].score > 0


def test_hybrid_returns_top_k():
    r = _make_retriever()
    hits = r.search("where is my order it says shipped", top_k=2)
    assert len(hits) <= 2
    assert all(h.score >= 0 for h in hits)


def test_retrieval_confidence_saturates():
    r = _make_retriever()
    hits = r.search("my package has not arrived and tracking is stuck")
    conf = r.retrieval_confidence(hits)
    assert 0.0 <= conf <= 1.0
