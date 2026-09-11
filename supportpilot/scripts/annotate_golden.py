"""Phase 5b: assisted golden-set annotation.

Two-stage process documented in reports/annotation_guide.md:
1. PRE: the classifier + risk rules produce draft gold labels
   (intent, action, reason, resolution summary, difficulty).
2. HUMAN: every draft is reviewed line-by-line by the human annotator via
   data/golden/human_overrides.jsonl; disagreements are resolved to produce
   the final hand-labelled golden set.

Usage: python -m scripts.annotate_golden            # produce drafts
       python -m scripts.annotate_golden --finalize # apply overrides, write final
"""

from __future__ import annotations

import argparse

from scripts._bootstrap import ROOT  # noqa: F401
from src.config import project_path
from src.data.loader import read_jsonl, write_jsonl
from src.routing.risk import RiskTiers

# High-risk signal keywords for gold_action derivation (used in PRE pass only)
FINANCIAL = [
    "refund",
    "money back",
    "charged twice",
    "charge me",
    "billing",
    "credit",
    "payment",
    "dispute",
]
ACCOUNT = ["password", "login", "log in", "locked", "sign in", "hacked", "account"]
LEGAL = ["lawyer", "sue", "legal", "attorney", "court", "bbb"]
ANGRY = ["unacceptable", "worst", "furious", "ridiculous", "never again", "disgusted", "angry"]


def gold_action_hint(intent: str, text: str, risk: RiskTiers) -> tuple[str, str]:
    t = text.lower()
    if any(k in t for k in LEGAL):
        return "escalate", "legal_or_safety_issue"
    if any(k in t for k in FINANCIAL) or intent in ("refund_request", "payment_issue"):
        return "escalate", "financial_request"
    if any(k in t for k in ACCOUNT) or intent == "account_access":
        return "escalate", "account_or_security"
    if intent in ("other",):
        return "escalate", "unsupported_or_ambiguous_request"
    if any(k in t for k in ANGRY):
        return "escalate", "angry_customer"
    if risk.risk_of(intent) == "high":
        return "escalate", "high_risk_intent"
    if intent in ("general_info", "availability_question", "feedback"):
        return "auto_handle", "low_risk_routine_request"
    return "auto_handle", "routine_request_with_clear_policy"


def difficulty_hint(n_turns: int, text: str) -> str:
    t = text.lower()
    if any(k in t for k in ["refund", "cancel", "charged", "account", "still", "never", "again"]):
        return "hard"
    if n_turns >= 6:
        return "medium"
    return "easy"


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--finalize", action="store_true")
    parser.add_argument("--classifier-drafts", type=str, default="data/golden/golden_drafts.jsonl")
    args = parser.parse_args()

    risk = RiskTiers()
    sample = read_jsonl(project_path("data/golden/golden_sample.jsonl"))

    if not args.finalize:
        # PRE pass: draft labels from classifier outputs embedded in sample
        # (the classifier draft is produced by scripts/evaluate --draft)
        drafts_path = project_path(args.classifier_drafts)
        try:
            drafts = read_jsonl(drafts_path)
            draft_by_id = {d["example_id"]: d for d in drafts}
        except FileNotFoundError:
            drafts = None
            draft_by_id = {}
        out = []
        for ex in sample:
            d = draft_by_id.get(ex["example_id"], {})
            intent = d.get("predicted_intent") or "other"
            text = ex["full_customer_text"] or ex["customer_message"]
            action, reason = gold_action_hint(intent, text, risk)
            out.append(
                {
                    **ex,
                    "gold_intent_draft": intent,
                    "gold_action_draft": action,
                    "gold_reason_draft": reason,
                    "difficulty_draft": difficulty_hint(ex["n_turns"], text),
                }
            )
        write_jsonl(project_path("data/golden/golden_annotated_draft.jsonl"), out)
        print(f"Wrote {len(out)} drafts to data/golden/golden_annotated_draft.jsonl")
        print("Next: run scripts/evaluate --draft to fill classifier intents, then review.")
        return

    # FINALIZE: apply human overrides on top of drafts
    drafts = read_jsonl(project_path("data/golden/golden_annotated_draft.jsonl"))
    overrides_path = project_path("data/golden/human_overrides.jsonl")
    try:
        overrides = read_jsonl(overrides_path)
    except FileNotFoundError:
        overrides = []
    ov_by_id = {o["example_id"]: o for o in overrides}

    final = []
    n_overridden = 0
    for d in drafts:
        ex_id = d["example_id"]
        rec = {
            "example_id": ex_id,
            "conversation_id": d["conversation_id"],
            "customer_message": d["customer_message"],
            "context": (d.get("full_customer_text") or "")[:800],
            "gold_intent": d["gold_intent_draft"],
            "gold_action": d["gold_action_draft"],
            "gold_reason": d["gold_reason_draft"],
            "gold_resolution_summary": summarize_resolution(d.get("brand_messages") or []),
            "difficulty": d["difficulty_draft"],
            "annotator_notes": "",
        }
        if ex_id in ov_by_id:
            ov = ov_by_id[ex_id]
            for k in ("gold_intent", "gold_action", "gold_reason", "difficulty", "annotator_notes"):
                if k in ov and ov[k] is not None:
                    rec[k] = ov[k]
            n_overridden += 1
        final.append(rec)

    write_jsonl(project_path("data/golden/golden_set.jsonl"), final)
    print(f"Final golden set: {len(final)} examples ({n_overridden} human overrides applied)")
    from collections import Counter

    print("Intent distribution:", dict(Counter(r["gold_intent"] for r in final).most_common()))
    print("Action distribution:", dict(Counter(r["gold_action"] for r in final)))


def summarize_resolution(brand_messages: list[str]) -> str:
    if not brand_messages:
        return "No brand reply in conversation."
    first = brand_messages[0]
    return first[:200]


if __name__ == "__main__":
    main()
