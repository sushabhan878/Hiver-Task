"""Failure analysis: identify top failure modes with real golden examples.

Categorizes each golden-set miss into failure modes and picks representative
examples for the final report. Writes reports/failure_cases.json.
"""

import json
from collections import Counter
from pathlib import Path

ROOT = Path(r"C:\Users\susha\OneDrive\Desktop\HIver\supportpilot")
GOLDEN_PATH = ROOT / "data/golden/golden_set.jsonl"
with open(GOLDEN_PATH, encoding="utf-8") as f:
    golden = [json.loads(line) for line in f]
with open(ROOT / "reports/agent_traces.json", encoding="utf-8") as f:
    traces = json.load(f)
with open(ROOT / "reports/results.json", encoding="utf-8") as f:
    results = json.load(f)

failures = []
for g, t in zip(golden, traces, strict=True):
    f_intent = g["gold_intent"] != t["intent"]["label"]
    f_action = g["gold_action"] != t["routing"]["decision"]
    if not f_intent and not f_action:
        continue
    mode = []
    if f_intent:
        mode.append("intent_misclassification")
    if f_action:
        if g["gold_action"] == "auto_handle" and t["routing"]["decision"] == "escalate":
            mode.append("over_escalation")
        else:
            mode.append("missed_escalation")
    failures.append(
        {
            "example_id": g["example_id"],
            "text": g["customer_message"][:160],
            "gold_intent": g["gold_intent"],
            "pred_intent": t["intent"]["label"],
            "intent_conf": t["intent"]["confidence"],
            "gold_action": g["gold_action"],
            "pred_action": t["routing"]["decision"],
            "escalation_reason": t["routing"]["reason"],
            "automation_score": t["routing"]["score"],
            "modes": mode,
            "difficulty": g["difficulty"],
        }
    )

mode_counts = Counter(m for f in failures for m in f["modes"])
print("Failure mode counts:", dict(mode_counts))
print(f"Total cases with >=1 failure: {len(failures)}/{len(golden)}")

# representative examples per mode (prefer confusable pairs)
by_mode = {}
for f in failures:
    for m in f["modes"]:
        by_mode.setdefault(m, []).append(f)

out = {"total_failures": len(failures), "mode_counts": dict(mode_counts), "representative": {}}
for m, cases in by_mode.items():
    # pick 3 diverse: one low intent conf, one high conf, one medium
    cases_sorted = sorted(cases, key=lambda x: x["intent_conf"])
    picks = [cases_sorted[0], cases_sorted[len(cases_sorted) // 2], cases_sorted[-1]]
    out["representative"][m] = [dict(p) for p in picks]

# confusion pairs for intent failures
pairs = Counter(
    (f["gold_intent"], f["pred_intent"])
    for f in failures
    if "intent_misclassification" in f["modes"]
)
out["top_confusions"] = [{"gold": a, "pred": b, "count": n} for (a, b), n in pairs.most_common(8)]

with open(ROOT / "reports/failure_cases.json", "w", encoding="utf-8") as fjson:
    json.dump(out, fjson, ensure_ascii=False, indent=2)
print("Wrote reports/failure_cases.json")

# print representatives for the report (console-safe: ASCII-only fallback)
import sys as _sys


def _safe(s: str) -> str:
    enc = getattr(_sys.stdout, "encoding", None) or "ascii"
    try:
        s.encode(enc)
        return s
    except (UnicodeEncodeError, LookupError):
        return s.encode("ascii", errors="replace").decode("ascii")


for m, reps in out["representative"].items():
    print(f"\n=== {m}")
    for r in reps:
        print(
            f"  [{r['example_id']}] gold={r['gold_intent']}/pred={r['pred_intent']} "
            f"conf={r['intent_conf']} action={r['gold_action']}/{r['pred_action']} "
            f"reason={r['escalation_reason']}"
        )
        print(f"     text: {_safe(r['text'][:110])}")
