import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.routing.policy import RoutingPolicy, RoutingSignals, run_guardrails  # noqa: E402
from src.routing.risk import RiskTiers  # noqa: E402


def _signals(**kw):
    defaults = {
        "intent": "delivery_status",
        "intent_confidence": 0.9,
        "retrieval_best_score": 0.7,
        "retrieval_confidence": 0.8,
        "has_strong_match": True,
        "evidence_ids": ["c1"],
        "reply": "Please DM us your order details.",
        "evidence_texts": ["Please DM us your order details."],
        "generated_groundedness": 0.6,
        "safety_score": 1.0,
    }
    defaults.update(kw)
    return RoutingSignals(**defaults)


def test_auto_handle_happy_path():
    p = RoutingPolicy()
    d = p.decide(_signals())
    assert d.action == "auto_handle"
    assert d.reason is None


def test_high_risk_escalates():
    p = RoutingPolicy()
    d = p.decide(_signals(intent="refund_request", intent_confidence=0.95))
    assert d.action == "escalate"
    assert d.reason == "HIGH_RISK_INTENT"


def test_low_intent_confidence_escalates():
    p = RoutingPolicy()
    d = p.decide(_signals(intent_confidence=0.3))
    assert d.action == "escalate"
    assert d.reason == "LOW_INTENT_CONFIDENCE"


def test_weak_retrieval_escalates():
    p = RoutingPolicy()
    d = p.decide(_signals(retrieval_best_score=0.2, retrieval_confidence=0.2))
    assert d.action == "escalate"
    assert d.reason == "WEAK_RETRIEVAL_EVIDENCE"


def test_no_strong_match_escalates():
    p = RoutingPolicy()
    d = p.decide(_signals(has_strong_match=False))
    assert d.action == "escalate"
    assert d.reason == "NO_STRONG_MATCH"


def test_refund_promise_guardrail():
    flags, safety = run_guardrails(
        "We have issued your refund of $50.", ["customer got refund"], ["c1"]
    )
    assert any("refund_promise" in f for f in flags)
    assert safety < 1.0


def test_invented_url_guardrail():
    flags, _ = run_guardrails("See http://bit.ly/abc", [], ["c1"])
    assert any("url" in f for f in flags)


def test_money_without_evidence_guardrail():
    flags, _ = run_guardrails("Your refund is $50.", ["we can look into it"], ["c1"])
    assert any("money" in f for f in flags)


def test_money_with_evidence_ok():
    flags, _ = run_guardrails("Your refund is $50.", ["refund of $50 processed"], ["c1"])
    assert not any("money" in f for f in flags)


def test_no_evidence_ids_guardrail():
    flags, _ = run_guardrails("Please DM us.", [], [])
    assert "NO_EVIDENCE_ATTACHED" in flags


def test_risk_tiers():
    rt = RiskTiers()
    assert rt.risk_of("refund_request") == "high"
    assert rt.risk_of("general_info") == "low"
    assert rt.is_high_risk("account_access")
    assert not rt.is_high_risk("feedback")
    assert rt.default_action_for("refund_request") == "escalate"
    assert rt.default_action_for("availability_question") == "auto_handle"


def test_clean_reply_no_flags():
    flags, safety = run_guardrails(
        "Sorry about the delay! Please DM your order number so we can check.",
        ["DM your order number"],
        ["c1"],
    )
    assert flags == []
    assert safety == 1.0


def test_refund_offer_without_evidence_flagged():
    flags, _ = run_guardrails(
        "Sorry! Would you like a refund or a replacement?",
        ["Sorry to hear. Please DM your order number."],
        ["c1"],
    )
    assert any("refund_offer" in f for f in flags)


def test_refund_offer_with_evidence_ok():
    flags, _ = run_guardrails(
        "Sorry! Would you like a refund or a replacement?",
        ["we can offer you a refund or replacement"],
        ["c1"],
    )
    assert not any("refund_offer" in f for f in flags)


def test_meta_leak_flagged():
    flags, _ = run_guardrails(
        "Based on the historical cases, there is no clear precedent for this.",
        ["some evidence"],
        ["c1"],
    )
    assert any("meta_leak" in f for f in flags)


def test_escalation_promise_flagged():
    flags, _ = run_guardrails(
        "I'll escalate this to the relevant team for review.", ["please contact support"], ["c1"]
    )
    assert any("escalation_promise" in f for f in flags)
