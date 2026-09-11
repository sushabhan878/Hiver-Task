import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.data.splitter import check_leakage, split_bucket  # noqa: E402
from src.data.threading import build_conversation_record, parse_turns  # noqa: E402


def test_parse_turns_basic():
    conv = "Customer: my package is late\nSupport: sorry! DM us\nCustomer: ok"
    turns = parse_turns(conv)
    assert [t["speaker"] for t in turns] == ["customer", "support", "customer"]
    assert turns[0]["text"].startswith("my package")


def test_parse_turns_empty():
    assert parse_turns("") == []
    assert parse_turns(None) == []


def test_build_record_drops_customerless():
    rec = build_conversation_record("c1", "AmazonHelp", "Support: only brand turn")
    assert rec is None


def test_build_record_keeps_valid():
    rec = build_conversation_record(
        "c1",
        "AmazonHelp",
        "Customer: where is my order 12345\nSupport: Please DM us your order details.",
    )
    assert rec is not None
    assert rec["has_brand_reply"] is True
    assert rec["n_turns"] == 2


def test_split_bucket_deterministic():
    a = split_bucket("conv-abc", 42, 0.70, 0.15)
    b = split_bucket("conv-abc", 42, 0.70, 0.15)
    assert a == b
    assert a in ("retrieval", "validation", "golden_pool")


def test_split_bucket_distribution():
    import collections

    buckets = collections.Counter(split_bucket(f"conv-{i}", 42, 0.70, 0.15) for i in range(2000))
    assert buckets["retrieval"] > buckets["validation"]
    assert buckets["golden_pool"] > 100


def test_check_leakage():
    assert check_leakage({"a", "b"}, {"c"})["leakage_free"]
    res = check_leakage({"a", "b"}, {"b"})
    assert not res["leakage_free"] and res["n_overlap"] == 1
