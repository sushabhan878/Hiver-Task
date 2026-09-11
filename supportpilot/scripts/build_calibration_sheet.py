"""Build the human calibration subset: 50 stratified examples with agent replies.

The annotator (author) rated these against the judge_v2 rubric in a pass where
judge outputs were hidden. Ratings recorded in data/golden/human_rubric_ratings.jsonl.
"""

import json
import random
from collections import Counter
from pathlib import Path

ROOT = Path(r"C:\Users\susha\OneDrive\Desktop\HIver\supportpilot")
GOLDEN_PATH = ROOT / "data/golden/golden_set.jsonl"
with open(GOLDEN_PATH, encoding="utf-8") as f:
    golden = [json.loads(line) for line in f]
with open(ROOT / "reports/agent_traces.json", encoding="utf-8") as f:
    traces = json.load(f)

rng = random.Random(42)
# stratify by action and intent to cover both auto and escalate paths
by_cell = {}
for g, t in zip(golden, traces, strict=True):
    by_cell.setdefault((g["gold_intent"], t["routing"]["decision"]), []).append((g, t))

subset = []
# proportional-ish: take up to 4 per cell, at least 1 per non-empty cell
for _cell, members in sorted(by_cell.items()):
    rng.shuffle(members)
    take = min(4, len(members))
    subset.extend(members[:take])
rng.shuffle(subset)
subset = subset[:50]

out = []
for g, t in subset:
    out.append(
        {
            "example_id": g["example_id"],
            "customer_message": g["customer_message"],
            "agent_reply": t["generation"]["reply"],
            "evidence_preview": [
                {"problem": c["customer_problem"][:80], "response": c["brand_response"][:80]}
                for c in t["retrieval"]["cases"][:3]
            ],
            "pred_action": t["routing"]["decision"],
        }
    )
with open(ROOT / "data/golden/human_rating_sheet.json", "w", encoding="utf-8") as f:
    json.dump(out, f, ensure_ascii=False, indent=1)
print(f"Wrote {len(out)} examples; action mix:", Counter(o["pred_action"] for o in out))
print("Intents:", Counter(g_["gold_intent"] for g_, _ in [(x, x) for x in subset]))
