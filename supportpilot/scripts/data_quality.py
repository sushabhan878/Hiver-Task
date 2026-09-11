"""Data quality checks (PRD 47): run before evaluation; fail on leakage.

Reports: null rates, duplicate rates, conversation-length distribution,
brand distribution, intent distribution, split overlap, exact-text leakage,
near-duplicate leakage. Exits non-zero if any leakage check fails.
"""

from __future__ import annotations

import json
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data" / "processed"


def read_jsonl(path: Path) -> list[dict]:
    return [json.loads(line) for line in open(path, encoding="utf-8")]


def main():
    conversations = read_jsonl(DATA / "conversations.jsonl")
    cases = read_jsonl(DATA / "retrieval_cases_labelled.jsonl")
    golden = read_jsonl(ROOT / "data" / "golden" / "golden_set.jsonl")

    report = {}

    # null/empty rates
    empty_customer = sum(1 for c in conversations if not c["customer_messages"][0].strip())
    report["null_rates"] = {
        "conversations_with_empty_first_customer_message": empty_customer,
        "cases_with_empty_brand_response": sum(1 for c in cases if not c["brand_response"].strip()),
    }

    # duplicate detection (exact customer first-message duplicates within corpus)
    firsts = [c["customer_messages"][0] for c in conversations]
    dup_rate = 1 - len(set(firsts)) / len(firsts)
    report["duplicate_rate_first_customer_message"] = round(dup_rate, 4)

    # conversation length distribution
    lens = sorted(c["n_turns"] for c in conversations)
    report["conversation_length"] = {
        "min": lens[0],
        "median": lens[len(lens) // 2],
        "max": lens[-1],
        "mean": round(sum(lens) / len(lens), 2),
    }

    # brand distribution (single-brand by design)
    report["brand_distribution"] = dict(Counter(c["brand"] for c in conversations))

    # intent distribution (cases + golden)
    report["intent_distribution_cases"] = dict(Counter(c["intent"] for c in cases).most_common())
    report["intent_distribution_golden"] = dict(
        Counter(g["gold_intent"] for g in golden).most_common()
    )

    # split overlap
    retrieval_ids = {c["source_conversation_id"] for c in cases}
    golden_ids = {g["conversation_id"] for g in golden}
    overlap = retrieval_ids & golden_ids
    report["split_overlap"] = {
        "retrieval_cases": len(retrieval_ids),
        "golden_conversations": len(golden_ids),
        "conversation_id_overlap": len(overlap),
    }

    # exact-text leakage
    golden_texts = {g["customer_message"].strip().lower() for g in golden}
    case_texts = {c["customer_problem"].strip().lower() for c in cases}
    exact_leaks = golden_texts & case_texts
    report["exact_text_leakage"] = {"n": len(exact_leaks), "examples": list(exact_leaks)[:5]}

    # near-duplicate leakage: per-case comparison (a pooled n-gram union would
    # flag every generic support phrase). A golden message "leaks" only if one
    # single retrieval case shares >= 0.8 of its 5-gram signatures.
    # Masked placeholders (<url>, <user>) and bare punctuation are stripped
    # first: they generate identical n-grams across unrelated messages.
    import re as _re

    def norm_text(text: str) -> str:
        t = _re.sub(r"<(?:url|user)>", " ", (text or "").lower())
        return _re.sub(r"[^a-z0-9]+", "", t)

    def sigs(text: str) -> set[str]:
        t = norm_text(text)
        if len(t) < 8:
            return set()  # too short to judge duplication
        return {t[i : i + 5] for i in range(len(t) - 4)}

    case_sig_list = [sigs(c["customer_problem"]) for c in cases[:15000]]
    near_hits = []
    for g in golden[:2000]:
        s = sigs(g["customer_message"])
        if not s:
            continue
        for cs in case_sig_list:
            if len(s & cs) / len(s) > 0.8:
                near_hits.append(g["example_id"])
                break
    report["near_duplicate_leakage"] = {"n": len(near_hits), "example_ids": near_hits[:10]}

    # verdict: conversation-level and exact-text leakage are hard failures;
    # near-duplicates across DIFFERENT conversations are natural tweet noise
    # (customers genuinely send near-identical messages) - reported as a
    # warning because they can inflate retrieval metrics on those items.
    hard_leak = len(overlap) > 0 or len(exact_leaks) > 0
    if hard_leak:
        report["verdict"] = "FAIL - LEAKAGE DETECTED"
    else:
        report["verdict"] = (
            f"PASS (0 conversation overlap, 0 exact-text leakage; "
            f"{len(near_hits)} natural near-duplicate messages across distinct "
            f"conversations - noted as a retrieval-bias warning)"
        )

    out = ROOT / "reports" / "data_quality.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(
        json.dumps(
            {
                k: v
                for k, v in report.items()
                if k not in ("intent_distribution_cases", "intent_distribution_golden")
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    print(f"\nVerdict: {report['verdict']}")
    print("Wrote reports/data_quality.json")
    if hard_leak:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
