"""Export a compact review sheet for hand annotation (id, text, draft labels)."""

import json

with open("data/golden/golden_annotated_draft.jsonl", encoding="utf-8") as f:
    rows = [json.loads(line) for line in f]
out = []
for r in rows:
    out.append(
        {
            "example_id": r["example_id"],
            "text": (r["customer_message"] or "")[:220],
            "ctx": (r.get("full_customer_text") or "")[:260],
            "brand_first": (r["brand_messages"][0][:150] if r["brand_messages"] else ""),
            "intent": r["gold_intent_draft"],
            "action": r["gold_action_draft"],
            "reason": r["gold_reason_draft"],
            "difficulty": r["difficulty_draft"],
        }
    )
with open("data/golden/review_sheet.json", "w", encoding="utf-8") as f:
    json.dump(out, f, ensure_ascii=False, indent=1)
print(f"Wrote {len(out)} rows to data/golden/review_sheet.json")
