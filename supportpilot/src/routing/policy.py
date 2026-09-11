"""Auto-handle vs escalate routing policy with deterministic guardrails.

Escalation reasons (fixed taxonomy):
    LOW_INTENT_CONFIDENCE
    WEAK_RETRIEVAL_EVIDENCE
    NO_STRONG_MATCH
    HIGH_RISK_INTENT
    UNSUPPORTED_GENERATED_CLAIM
    NO_EVIDENCE_ATTACHED
    SAFETY_CONCERN
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

from src.config import thresholds_cfg
from src.routing.risk import RiskTiers

REASON_LOW_INTENT = "LOW_INTENT_CONFIDENCE"
REASON_WEAK_RETRIEVAL = "WEAK_RETRIEVAL_EVIDENCE"
REASON_NO_STRONG_MATCH = "NO_STRONG_MATCH"
REASON_HIGH_RISK = "HIGH_RISK_INTENT"
REASON_UNSUPPORTED_CLAIM = "UNSUPPORTED_GENERATED_CLAIM"
REASON_NO_EVIDENCE = "NO_EVIDENCE_ATTACHED"
REASON_SAFETY = "SAFETY_CONCERN"
REASON_BELOW_THRESHOLD = "AUTOMATION_SCORE_BELOW_THRESHOLD"

# Deterministic claim patterns for guardrails ---------------------------------
MONEY_RE = re.compile(
    r"\$\s?\d+|£\s?\d+|€\s?\d+|(?<!\w)(\d+)\s?(?:dollars|usd|gbp|eur)(?!\w)", re.I
)
REFUND_PROMISE_RE = re.compile(
    r"issued\s+(?:you\s+)?(?:a\s+)?refund"
    r"|(?:we|i)(?:'ve|\s+have)?\s+issued\s+(?:your\s+)?(?:a\s+)?refund"
    r"|refund\s+(?:has\s+been|is\s+being|will\s+be)\s+(?:issued|processed|sent|approved)"
    r"|(?:we|i)(?:'ve|\s+have)?\s+refunded",
    re.I,
)
COMPLETED_ACTION_RE = re.compile(
    r"(?:we(?:'ve| have)? )?(?:cancelled|canceled|reshipped|replaced|upgraded|removed)\s+your", re.I
)
INTERNAL_SYSTEM_RE = re.compile(
    r"(?:logged into|accessed)\s+(?:your|our)\s+(?:account|system)"
    r"|internal\s+(?:tool|system)",
    re.I,
)
URL_RE = re.compile(r"https?://\S+|www\.\S+")
META_LEAK_RE = re.compile(
    r"historical case|based on (?:the )?(?:historical|retrieved)"
    r"|precedent|the evidence (?:provided|suggests)",
    re.I,
)
REFUND_NO_EVIDENCE_RE = re.compile(
    r"(?:full|partial)\s+refund\s+(?:of|for)|refund\s+(?:amount|within)", re.I
)
REFUND_OFFER_RE = re.compile(
    r"(?:would|do|want|like|wollen|möchtest|moechtest|quieres|gostaria)"
    r"\s+you\s+(?:like|want)?\s*(?:a\s+)?"
    r"(?:refund|replacement|reshipment|credit)"
    r"|(?:möchtest du|moechtest du|quieres|gostaria de|would you like)"
    r".{0,40}(?:refund|erstattung|reembolso|rimborso)",
    re.I,
)
INTERNAL_ESCALATION_RE = re.compile(
    r"i'?ll\s+escalate\s+this|we'?ll\s+escalate\s+this"
    r"|escalate\s+this\s+to\s+the\s+(?:relevant|appropriate)\s+team",
    re.I,
)


@dataclass
class RoutingSignals:
    intent: str
    intent_confidence: float
    retrieval_best_score: float
    retrieval_confidence: float
    has_strong_match: bool
    evidence_ids: list[str]
    reply: str
    evidence_texts: list[str] = field(default_factory=list)
    generated_groundedness: float = 0.0  # judge/model-groundedness estimate 0..1
    safety_score: float = 0.0  # deterministic guardrail score 0..1


@dataclass
class RoutingDecision:
    action: str  # "auto_handle" | "escalate"
    automation_score: float
    reason: str | None
    guardrail_flags: list[str] = field(default_factory=list)
    details: dict = field(default_factory=dict)


def run_guardrails(
    reply: str, evidence_texts: list[str], evidence_ids: list[str]
) -> tuple[list[str], float]:
    """Deterministic safety checks. Returns (flags, safety_score 0..1)."""
    flags = []
    if not evidence_ids:
        flags.append(REASON_NO_EVIDENCE)
    if META_LEAK_RE.search(reply):
        flags.append(REASON_UNSUPPORTED_CLAIM + ":meta_leak")
    if URL_RE.search(reply):
        flags.append(REASON_UNSUPPORTED_CLAIM + ":url")
    if REFUND_PROMISE_RE.search(reply):
        flags.append(REASON_UNSUPPORTED_CLAIM + ":refund_promise")
    elif COMPLETED_ACTION_RE.search(reply):
        flags.append(REASON_UNSUPPORTED_CLAIM + ":completed_action")
    elif REFUND_NO_EVIDENCE_RE.search(reply) and not any(
        "refund" in (e or "").lower() for e in evidence_texts
    ):
        flags.append(REASON_UNSUPPORTED_CLAIM + ":refund_specifics")
    if REFUND_OFFER_RE.search(reply) and not any(
        (
            "refund" in (e or "").lower()
            or "replaced" in (e or "").lower()
            or "replacement" in (e or "").lower()
        )
        for e in evidence_texts
    ):
        flags.append(REASON_UNSUPPORTED_CLAIM + ":refund_offer")
    if INTERNAL_ESCALATION_RE.search(reply):
        flags.append(REASON_UNSUPPORTED_CLAIM + ":escalation_promise")
    if INTERNAL_SYSTEM_RE.search(reply):
        flags.append(REASON_SAFETY)
    # Numbers are allowed only when they appear in retrieved evidence
    money = MONEY_RE.search(reply)
    if money and not any(money.group(0) in (e or "") for e in evidence_texts):
        flags.append(REASON_UNSUPPORTED_CLAIM + ":money")
    # safety score: 1.0 when clean, decreasing with flags
    safety = max(0.0, 1.0 - 0.5 * len(flags))
    return flags, safety


class RoutingPolicy:
    def __init__(self, cfg: dict | None = None, risk: RiskTiers | None = None):
        self.cfg = (cfg or thresholds_cfg())["routing"]
        self.weights = (cfg or thresholds_cfg())["automation_score_weights"]
        self.risk = risk or RiskTiers()

    def automation_score(self, s: RoutingSignals) -> float:
        return (
            self.weights["intent_confidence"] * s.intent_confidence
            + self.weights["retrieval_confidence"] * s.retrieval_confidence
            + self.weights["response_groundedness"] * s.generated_groundedness
            + self.weights["safety_score"] * s.safety_score
        )

    def decide(self, s: RoutingSignals) -> RoutingDecision:
        # Hard checks first (risk overrides everything)
        if self.cfg.get("high_risk_override", True) and self.risk.is_high_risk(s.intent):
            return RoutingDecision("escalate", self.automation_score(s), REASON_HIGH_RISK)

        if s.intent_confidence < self.cfg["intent_conf_min"]:
            return RoutingDecision("escalate", self.automation_score(s), REASON_LOW_INTENT)

        if s.retrieval_best_score < self.cfg["retrieval_score_min"]:
            return RoutingDecision("escalate", self.automation_score(s), REASON_WEAK_RETRIEVAL)

        if self.cfg.get("strong_match_required", True) and not s.has_strong_match:
            return RoutingDecision("escalate", self.automation_score(s), REASON_NO_STRONG_MATCH)

        flags, safety = run_guardrails(s.reply, s.evidence_texts or [], s.evidence_ids)
        if flags:
            return RoutingDecision(
                "escalate", self.automation_score(s), flags[0], guardrail_flags=flags
            )

        score = self.automation_score(RoutingSignals(**{**s.__dict__, "safety_score": safety}))
        if score >= self.cfg["auto_threshold"]:
            return RoutingDecision("auto_handle", score, None)
        return RoutingDecision(
            "escalate", score, REASON_BELOW_THRESHOLD, details={"automation_score": score}
        )
