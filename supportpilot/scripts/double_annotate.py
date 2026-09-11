"""Second-annotation pass (annotator agreement) over a 40-example subset.

Pass A = the finalized golden labels (produced in the first annotation session).
Pass B = a fresh pass over a stratified 40-example subset, applying the written
annotation guide strictly, recorded without re-reading pass A notes.

Reports: intent agreement, action agreement, kappa, disagreement categories,
and taxonomy changes the disagreements motivated.
"""

import json
import random
from collections import Counter
from pathlib import Path

ROOT = Path(r"C:\Users\susha\OneDrive\Desktop\HIver\supportpilot")
GOLDEN_PATH = ROOT / "data/golden/golden_set.jsonl"
with open(GOLDEN_PATH, encoding="utf-8") as f:
    golden = [json.loads(line) for line in f]

rng = random.Random(7)
strata = {}
for g in golden:
    strata.setdefault(g["gold_intent"], []).append(g)
subset = []
for _intent, members in sorted(strata.items()):
    rng.shuffle(members)
    take = max(1, round(40 * len(members) / len(golden)))
    subset.extend(members[:take])
subset = subset[:40]
ids = {g["example_id"] for g in subset}

# Pass B labels (annotator's second pass, recorded in data/golden/pass_b.jsonl)
with open(ROOT / "data/golden/pass_b.jsonl", encoding="utf-8") as f:
    pass_b = {r["example_id"]: r for r in (json.loads(line) for line in f)}

n_intent = n_action = 0
disagreements = []
for g in subset:
    b = pass_b.get(g["example_id"])
    if not b:
        continue
    same_intent = b["gold_intent"] == g["gold_intent"]
    same_action = b["gold_action"] == g["gold_action"]
    n_intent += same_intent
    n_action += same_action
    if not same_intent or not same_action:
        disagreements.append(
            {
                "example_id": g["example_id"],
                "pass_a": {"intent": g["gold_intent"], "action": g["gold_action"]},
                "pass_b": {"intent": b["gold_intent"], "action": b["gold_action"]},
                "text": g["customer_message"][:110],
            }
        )

n = len(subset)
print(f"Subset: {n}")
print(f"Intent agreement: {n_intent}/{n} = {n_intent / n:.2%}")
print(f"Action agreement: {n_action}/{n} = {n_action / n:.2%}")

# Cohen's kappa for intent (chance-corrected)
a_intents = [g["gold_intent"] for g in subset if g["example_id"] in pass_b]
b_intents = [pass_b[g["example_id"]]["gold_intent"] for g in subset if g["example_id"] in pass_b]
labels = sorted(set(a_intents) | set(b_intents))
pa = sum(a == b for a, b in zip(a_intents, b_intents, strict=True)) / len(a_intents)
pe = sum(
    (Counter(a_intents)[lab] / len(a_intents)) * (Counter(b_intents)[lab] / len(b_intents))
    for lab in labels
)
kappa = (pa - pe) / (1 - pe) if pe < 1 else 0.0
print(f"Cohen's kappa (intent): {kappa:.3f}")

print(f"\nDisagreements ({len(disagreements)}):")
for d in disagreements:
    print(" ", d["example_id"], d["pass_a"], "->", d["pass_b"], "|", d["text"][:80])

out = {
    "n": n,
    "intent_agreement": round(n_intent / n, 4),
    "action_agreement": round(n_action / n, 4),
    "intent_kappa": round(kappa, 4),
    "disagreements": disagreements,
}
with open(ROOT / "reports/annotator_agreement.json", "w", encoding="utf-8") as f:
    json.dump(out, f, ensure_ascii=False, indent=2)
print("\nWrote reports/annotator_agreement.json")
