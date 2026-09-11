"""Export all auto-handled agent cases (current run) for human safety review."""

import json
from pathlib import Path

ROOT = Path(r"C:\Users\susha\OneDrive\Desktop\HIver\supportpilot")
with open(ROOT / "reports/agent_traces.json", encoding="utf-8") as f:
    traces = json.load(f)
GOLDEN_PATH = ROOT / "data/golden/golden_set.jsonl"
with open(GOLDEN_PATH, encoding="utf-8") as f:
    golden = [json.loads(line) for line in f]

rows = []
for g, t in zip(golden, traces, strict=True):
    if t["routing"]["decision"] != "auto_handle":
        continue
    rows.append(
        {
            "example_id": g["example_id"],
            "customer_message": g["customer_message"][:200],
            "reply": t["generation"]["reply"],
            "score": t["routing"]["score"],
        }
    )
with open(ROOT / "data/golden/auto_handle_review.json", "w", encoding="utf-8") as f:
    json.dump(rows, f, ensure_ascii=False, indent=1)
print(f"exported {len(rows)} auto-handled cases")
