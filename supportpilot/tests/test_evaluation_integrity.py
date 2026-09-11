"""Evaluation integrity tests: golden immutability, no leakage, metric determinism."""

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

GOLDEN = ROOT / "data/golden/golden_set.jsonl"


def test_golden_set_schema_valid():
    with open(GOLDEN, encoding="utf-8") as f:
        rows = [json.loads(line) for line in f]
    assert 150 <= len(rows) <= 250
    required = {
        "example_id",
        "conversation_id",
        "customer_message",
        "gold_intent",
        "gold_action",
        "difficulty",
    }
    for r in rows:
        assert required.issubset(r.keys()), f"missing keys in {r['example_id']}"
        assert r["gold_action"] in ("auto_handle", "escalate")
        assert r["difficulty"] in ("easy", "medium", "hard")


def test_golden_ids_unique_and_stable():
    with open(GOLDEN, encoding="utf-8") as f:
        rows = [json.loads(line) for line in f]
    ids = [r["example_id"] for r in rows]
    assert len(ids) == len(set(ids))


def test_no_conversation_overlap_retrieval_vs_golden():
    cases_path = ROOT / "data/processed/retrieval_cases_labelled.jsonl"
    with open(cases_path, encoding="utf-8") as f:
        cases = [json.loads(line) for line in f]
    with open(GOLDEN, encoding="utf-8") as f:
        golden = [json.loads(line) for line in f]
    retrieval_convs = {c["source_conversation_id"] for c in cases}
    golden_convs = {g["conversation_id"] for g in golden}
    assert not (retrieval_convs & golden_convs), "conversation leakage!"


def test_metrics_deterministic():
    from src.evaluation.metrics import intent_metrics, recall_at_k_and_mrr

    y = ["a", "a", "b", "c"]
    p1 = intent_metrics(y, ["a", "a", "b", "b"], ["a", "b", "c"])
    p2 = intent_metrics(y, ["a", "a", "b", "b"], ["a", "b", "c"])
    assert p1 == p2
    r1 = recall_at_k_and_mrr(["a"], [["b", "a", "c"]])
    r2 = recall_at_k_and_mrr(["a"], [["b", "a", "c"]])
    assert r1 == r2 and r1["recall_at_3"] == 1.0 and abs(r1["mrr"] - 0.5) < 1e-9


def test_lexical_grounding_bounds():
    from src.evaluation.metrics import lexical_grounding

    assert lexical_grounding("please dm your order number", ["please dm your order number"]) == 1.0
    assert lexical_grounding("completely unrelated text here", ["something else entirely"]) < 0.3
