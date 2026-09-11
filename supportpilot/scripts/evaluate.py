"""Phase 4/6: evaluate the agent and baselines on the golden set.

Modes:
  --draft            run intent classifier on golden sample, write drafts
  --thresholds       tune AUTO_THRESHOLD on the validation split
  (default)          full evaluation: agent + baselines + judge + routing,
                     writes reports/results.json + predictions

Usage:
  python -m scripts.evaluate --draft
  python -m scripts.evaluate --thresholds
  python -m scripts.evaluate [--systems agent,b1,b2,b3] [--judge-sample N]
"""

from __future__ import annotations

import argparse
import time

import numpy as np

from scripts._bootstrap import ROOT  # noqa: F401
from src.config import config, intents_cfg, project_path
from src.data.loader import read_jsonl, write_json
from src.evaluation.baselines import (
    BM25NearestBaseline,
    LLMNoRetrievalBaseline,
    MajorityCannedBaseline,
)
from src.evaluation.judge import LLMJudge
from src.evaluation.metrics import (
    intent_consistency_topk,
    intent_metrics,
    lexical_grounding,
    recall_at_k_and_mrr,
    routing_metrics,
    useful_resolution_in_topk,
)
from src.generation.generator import ReplyGenerator
from src.llm.client import get_client
from src.retrieval.hybrid import HybridRetriever
from src.routing.policy import RoutingPolicy
from src.taxonomy.classifier import IntentClassifier


def load_components():
    cfg = config()
    client = get_client()
    cases = read_jsonl(project_path("data/processed/retrieval_cases_labelled.jsonl"))
    retriever = HybridRetriever(cases, cfg)
    example_bank = [
        {"intent": c["intent"], "text": c["customer_problem"]}
        for c in cases
        if c.get("intent") and c["intent"] != "unlabelled"
    ]
    classifier = IntentClassifier(client, example_bank)
    classifier.build_bank()
    generator = ReplyGenerator(client)
    policy = RoutingPolicy()
    return cfg, client, cases, retriever, classifier, generator, policy


def eval_retrieval(retriever, golden, results):
    gold_intents = [g["gold_intent"] for g in golden]
    hit_lists = []
    useful_flags = []
    for g in golden:
        hits = retriever.search(g["customer_message"])
        hit_lists.append([h.case.get("intent", "other") for h in hits])
        useful_flags.append(
            any(
                h.case.get("intent") == g["gold_intent"]
                and h.case.get("resolution_type", "").startswith(
                    ("asked_to_dm", "provided", "requested", "confirmed", "directed", "explained")
                )
                for h in hits
            )
        )
    results["retrieval"] = {
        **recall_at_k_and_mrr(gold_intents, hit_lists),
        **intent_consistency_topk(gold_intents, hit_lists),
        **useful_resolution_in_topk(useful_flags),
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--draft", action="store_true")
    parser.add_argument("--thresholds", action="store_true")
    parser.add_argument("--systems", type=str, default="agent,b1,b2,b3")
    parser.add_argument(
        "--judge-sample", type=int, default=None, help="limit judge to N examples (default all)"
    )
    parser.add_argument("--coverage-sweep", action="store_true", default=True)
    args = parser.parse_args()

    t_start = time.time()
    cfg, client, cases, retriever, classifier, generator, policy = load_components()
    icfg = intents_cfg()
    intent_names = list(icfg["intents"].keys())

    # ---------------------------------------------------------------- drafts
    if args.draft:
        sample = read_jsonl(project_path("data/golden/golden_sample.jsonl"))
        drafts = []
        for ex in sample:
            pred = classifier.predict(ex["customer_message"], use_llm_fallback=True)
            drafts.append({"example_id": ex["example_id"], "predicted_intent": pred.intent})
        write_jsonl = __import__("src.data.loader", fromlist=["write_jsonl"]).write_jsonl
        write_jsonl(project_path("data/golden/golden_drafts.jsonl"), drafts)
        print(f"Wrote {len(drafts)} classifier drafts for annotation assistance")
        return

    # ------------------------------------------------------------ threshold tune
    if args.thresholds:
        validation = read_jsonl(project_path("data/processed/validation.jsonl"))
        print(f"Tuning thresholds on {len(validation)} validation conversations")
        # measure intent-confidence + retrieval-score distributions, pick threshold
        # such that estimated unsafe-auto rate <= target on validation
        scores = []
        for v in validation[:300]:
            text = v["customer_messages"][0]
            hits = retriever.search(text)
            pred = classifier.predict(text, [h.case.get("intent", "other") for h in hits])
            rconf = retriever.retrieval_confidence(hits)
            strong = any(h.score >= cfg["retrieval"]["strong_match_score"] for h in hits)
            if not strong or pred.confidence < 0.55 or rconf < 0.4:
                continue  # would escalate under hard gates regardless
            s = 0.35 * pred.confidence + 0.35 * rconf + 0.20 * 0.5 + 0.10 * 1.0
            scores.append((s, pred.intent))
        arr = np.array([s for s, _ in scores]) if scores else np.array([0.6])
        print(f"Candidate pool after hard gates: {len(scores)}")
        for t in (0.50, 0.55, 0.60, 0.65, 0.70, 0.75, 0.80):
            kept = float((arr >= t).mean()) if len(arr) else 0.0
            print(f"  threshold {t:.2f}: post-gate coverage {kept:.2f}")
        # chosen: keep the default from thresholds.yaml unless data disagrees
        tuned = float(np.percentile(arr, 25)) if len(arr) >= 30 else 0.60
        tuned = round(min(max(tuned, 0.5), 0.8), 2)
        print(f"Suggested AUTO_THRESHOLD (25th percentile of gated scores): {tuned}")
        print(
            "Applied only if it differs from configs/thresholds.yaml;"
            " see reports/threshold_tuning.md"
        )
        write_json(
            project_path("reports/threshold_tuning.json"),
            {
                "n_validation": len(validation),
                "n_gated_pool": len(scores),
                "score_percentiles": {
                    "p25": round(float(np.percentile(arr, 25)), 4) if len(arr) else None,
                    "p50": round(float(np.percentile(arr, 50)), 4) if len(arr) else None,
                    "p75": round(float(np.percentile(arr, 75)), 4) if len(arr) else None,
                },
                "chosen_auto_threshold": tuned,
            },
        )
        return

    # ------------------------------------------------------------ full evaluate
    golden = read_jsonl(project_path("data/golden/golden_set.jsonl"))
    print(f"Evaluating {len(golden)} golden examples; systems: {args.systems}")
    systems = [s.strip() for s in args.systems.split(",")]

    results = {
        "system": {"name": "SupportPilot", "version": "0.1.0"},
        "config": {
            "brand": cfg["brand"]["selected_brand"],
            "chat_model": client.chat_model,
            "embed_model": client.embed_model,
            "retrieval_cases": len(cases),
            "golden_examples": len(golden),
        },
    }

    # retrieval metrics (independent of system)
    eval_retrieval(retriever, golden, results)

    predictions = {s: [] for s in systems}
    judge = LLMJudge(client)

    # ------------------- run each system -------------------
    if "agent" in systems:
        from src.pipeline import SupportPilotAgent

        agent = SupportPilotAgent(classifier, retriever, generator, policy, cfg)
        for i, g in enumerate(golden):
            trace = agent.handle(g["customer_message"])
            predictions["agent"].append(
                {
                    "example_id": g["example_id"],
                    "pred_intent": trace["intent"]["label"],
                    "pred_action": trace["routing"]["decision"],
                    "reply": trace["generation"]["reply"],
                    "reason": trace["routing"]["reason"],
                    "evidence_ids": trace["generation"]["supporting_case_ids"],
                    "retrieved_intents": [c["intent"] for c in trace["retrieval"]["cases"]],
                    "trace": trace,
                }
            )
            if (i + 1) % 25 == 0:
                print(f"  agent {i + 1}/{len(golden)}")

    if "b1" in systems:
        b1 = MajorityCannedBaseline([c["intent"] for c in cases if c.get("intent") != "unlabelled"])
        for g in golden:
            out = b1.handle(g["customer_message"])
            predictions["b1"].append(
                {
                    "example_id": g["example_id"],
                    "pred_intent": out["intent"],
                    "pred_action": out["action"],
                    "reply": out["reply"],
                    "reason": out["reason"],
                    "evidence_ids": [],
                    "retrieved_intents": [],
                }
            )

    if "b2" in systems:
        b2 = BM25NearestBaseline(cases)
        for g in golden:
            out = b2.handle(g["customer_message"])
            predictions["b2"].append(
                {
                    "example_id": g["example_id"],
                    "pred_intent": out["intent"],
                    "pred_action": out["action"],
                    "reply": out["reply"],
                    "reason": out["reason"],
                    "evidence_ids": out["evidence_ids"],
                    "retrieved_intents": [],
                }
            )

    if "b3" in systems:
        b3 = LLMNoRetrievalBaseline(client, intent_names)
        for i, g in enumerate(golden):
            out = b3.handle(g["customer_message"])
            predictions["b3"].append(
                {
                    "example_id": g["example_id"],
                    "pred_intent": out["intent"],
                    "pred_action": out["action"],
                    "reply": out["reply"],
                    "reason": out["reason"],
                    "evidence_ids": [],
                    "retrieved_intents": [],
                }
            )
            if (i + 1) % 25 == 0:
                print(f"  b3 {i + 1}/{len(golden)}")

    # ------------------- shared judging -------------------
    gold_intents = [g["gold_intent"] for g in golden]
    gold_actions = [g["gold_action"] for g in golden]

    system_results = {}
    judge_idx = golden if args.judge_sample is None else golden[: args.judge_sample]

    for sys_name in systems:
        preds = predictions[sys_name]
        if not preds:
            continue
        # intent metrics
        im = intent_metrics(gold_intents, [p["pred_intent"] for p in preds], intent_names)

        # judge each reply
        judged = []
        for p, g in zip(preds, judge_idx, strict=True):
            ev_cases = []
            if sys_name == "agent":
                ev_cases = list(p.get("trace", {}).get("retrieval", {}).get("cases", []))
            j = judge.judge(g["customer_message"], ev_cases, p["reply"])
            judged.append(j)
        acceptable = [j["acceptable"] for j in judged]
        ground = [j["groundedness"] for j in judged]

        # deterministic lexical grounding vs retrieved evidence
        lex_ground = []
        for p in preds:
            ev_texts = []
            if sys_name == "agent":
                ev_texts = [
                    c["brand_response"]
                    for c in p.get("trace", {}).get("retrieval", {}).get("cases", [])
                ]
            elif sys_name == "b2":
                ev_texts = [p["reply"]]  # nearest case's own response
            lex_ground.append(lexical_grounding(p["reply"], ev_texts))

        # routing metrics (only meaningful when system routes)
        rm = routing_metrics([p["pred_action"] for p in preds], gold_actions, acceptable)

        system_results[sys_name] = {
            "intent": {
                "accuracy": im["accuracy"],
                "macro_f1": im["macro_f1"],
                "per_intent_f1": im["per_intent_f1"],
            },
            "reply": {
                "acceptability": round(float(np.mean(acceptable)), 4) if acceptable else None,
                "groundedness_pass_rate": round(float(np.mean([g_ >= 4 for g_ in ground])), 4)
                if ground
                else None,
                "lexical_grounding": round(float(np.mean(lex_ground)), 4) if lex_ground else None,
                "mean_overall": round(float(np.mean([j["overall"] for j in judged])), 4)
                if judged
                else None,
                "safety_pass_rate": round(float(np.mean([j["safe"] for j in judged])), 4)
                if judged
                else None,
            },
            "routing": rm,
        }

    results["systems"] = system_results

    # ------------------- coverage-quality sweep (agent only) -------------------
    if "agent" in systems and predictions["agent"]:
        preds = predictions["agent"]
        sweep = []
        for t in (0.50, 0.60, 0.70, 0.80, 0.90):
            actions = []
            for p in preds:
                score = p["trace"]["routing"]["score"]
                hard_reason = p["trace"]["routing"]["reason"]
                if (
                    hard_reason
                    in (
                        "HIGH_RISK_INTENT",
                        "LOW_INTENT_CONFIDENCE",
                        "WEAK_RETRIEVAL_EVIDENCE",
                        "NO_STRONG_MATCH",
                    )
                    or p["trace"]["routing"]["guardrail_flags"]
                ):
                    actions.append("escalate")
                else:
                    actions.append("auto_handle" if score >= t else "escalate")
            auto_idx = [i for i, a in enumerate(actions) if a == "auto_handle"]
            # recompute acceptability for swept auto set using cached judge scores
            acc = []
            for i in auto_idx:
                ex = golden[i]
                j = judge.judge(
                    ex["customer_message"],
                    preds[i]["trace"]["retrieval"]["cases"],
                    preds[i]["reply"],
                )
                acc.append(j["acceptable"])
            sweep.append(
                {
                    "threshold": t,
                    "coverage": round(len(auto_idx) / len(preds), 4),
                    "auto_acceptability": round(float(np.mean(acc)), 4) if acc else None,
                    "unsafe_rate": round(1 - float(np.mean(acc)), 4) if acc else None,
                }
            )
        results["coverage_quality_sweep"] = sweep

    # ------------------- save -------------------
    results["elapsed_seconds"] = round(time.time() - t_start, 1)
    results["llm_stats"] = client.stats
    reports = project_path("reports")
    reports.mkdir(parents=True, exist_ok=True)
    write_json(reports / "results.json", results)
    write_json(
        reports / "predictions.json",
        {
            k: [{kk: vv for kk, vv in p.items() if kk != "trace"} for p in v]
            for k, v in predictions.items()
        },
    )
    # full traces for agent (inspectability)
    if "agent" in predictions:
        write_json(reports / "agent_traces.json", [p["trace"] for p in predictions["agent"]])

    # console summary
    print("\n=== RESULTS ===")
    print(f"Retrieval: {results['retrieval']}")
    for name, r in system_results.items():
        print(
            f"[{name}] intent acc={r['intent']['accuracy']} macroF1={r['intent']['macro_f1']} "
            f"reply acc={r['reply']['acceptability']} routing={r['routing']}"
        )
    print(f"Total elapsed: {results['elapsed_seconds']}s  LLM stats: {client.stats}")


if __name__ == "__main__":
    main()
