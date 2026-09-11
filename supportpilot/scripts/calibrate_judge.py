"""Phase 6b: calibrate the LLM judge against human ratings.

Humans rate a 40-60 example subset using the same rubric; we report
exact/±1 agreement, acceptable/not-acceptable agreement, and Pearson r.

The human ratings used here were produced by the author in a blind pass
over judge-hidden replies (see reports/annotation_guide.md). Scores live in
data/golden/human_rubric_ratings.jsonl.

Usage: python -m scripts.calibrate_judge
"""

from __future__ import annotations

from scripts._bootstrap import ROOT  # noqa: F401
from src.config import project_path, thresholds_cfg
from src.data.loader import read_json, read_jsonl, write_json
from src.evaluation.judge import LLMJudge
from src.evaluation.metrics import judge_human_agreement, weighted_reply_score
from src.llm.client import get_client


def main():
    tcfg = thresholds_cfg()
    golden = {g["example_id"]: g for g in read_jsonl(project_path("data/golden/golden_set.jsonl"))}
    predictions = read_json(project_path("reports/predictions.json"))
    agent_preds = {p["example_id"]: p for p in predictions.get("agent", [])}

    human = read_jsonl(project_path("data/golden/human_rubric_ratings.jsonl"))
    print(f"Calibrating judge against {len(human)} human-rated examples")

    client = get_client()
    judge = LLMJudge(client)

    judge_scores, human_scores = [], []
    per_example = []
    for h in human:
        ex_id = h["example_id"]
        if ex_id not in agent_preds:
            continue
        g = golden[ex_id]
        p = agent_preds[ex_id]
        # judge the same reply the human rated
        j = judge.judge(g["customer_message"], [], p["reply"])
        # human weighted overall (same weights as judge)
        h_overall = weighted_reply_score(h["human_scores"])
        judge_scores.append(j["overall"])
        human_scores.append(h_overall)
        per_example.append(
            {
                "example_id": ex_id,
                "judge_overall": j["overall"],
                "human_overall": round(h_overall, 2),
                "judge_acceptable": j["acceptable"],
                "human_acceptable": h_overall >= tcfg["judge"]["acceptability_min"],
            }
        )

    agreement = judge_human_agreement(
        judge_scores, human_scores, tcfg["judge"]["acceptability_min"]
    )

    # Human-ground-truth routing safety on the rated subset: an auto-handled
    # case is unsafe if the human deems the reply unacceptable (weighted < min).
    unsafe_detail = []
    n_auto = 0
    n_unsafe = 0
    for h, rec in zip(human, per_example, strict=False):
        p = agent_preds.get(h["example_id"])
        if p is None:
            continue
        if p["pred_action"] != "auto_handle":
            continue
        n_auto += 1
        human_overall = rec["human_overall"]
        if human_overall < tcfg["judge"]["acceptability_min"]:
            n_unsafe += 1
            unsafe_detail.append(
                {
                    "example_id": h["example_id"],
                    "human_overall": human_overall,
                    "reply": (p["reply"] or "")[:140],
                }
            )

    human_unsafe_rate = (n_unsafe / n_auto) if n_auto else None

    out = {
        "n": len(per_example),
        "agreement": agreement,
        "human_rated_auto_handle": {
            "n_auto_handled": n_auto,
            "n_unsafe": n_unsafe,
            "human_unsafe_auto_handle_rate": round(human_unsafe_rate, 4)
            if human_unsafe_rate is not None
            else None,
            "unsafe_examples": unsafe_detail,
        },
        "per_example": per_example,
        "interpretation": (
            "The local 3B judge is NOT a reliable proxy for humans on this rubric "
            "(low within-one and acceptable agreement). Judge scores are reported "
            "as indicative-only; the human-rated subset is the ground truth for "
            "reply acceptability and unsafe-auto-handle claims."
        ),
    }
    write_json(project_path("reports/judge_calibration.json"), out)
    print("Agreement:", agreement)
    print("Wrote reports/judge_calibration.json")


if __name__ == "__main__":
    main()
