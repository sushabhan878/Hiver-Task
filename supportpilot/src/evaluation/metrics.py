"""Evaluation metrics: intent, retrieval, reply, routing."""

from __future__ import annotations

import re

import numpy as np


# ------------------------------------------------------------------- intent
def intent_metrics(y_true: list[str], y_pred: list[str], labels: list[str]) -> dict:
    per_label = {lab: {"tp": 0, "fp": 0, "fn": 0} for lab in labels}
    correct = 0
    for t, p in zip(y_true, y_pred, strict=True):
        if t in per_label:
            if t == p:
                per_label[t]["tp"] += 1
                correct += 1
            else:
                per_label[t]["fn"] += 1
                if p in per_label:
                    per_label[p]["fp"] += 1
    f1s = {}
    for lab, c in per_label.items():
        denom = 2 * c["tp"] + c["fp"] + c["fn"]
        f1s[lab] = round(2 * c["tp"] / denom, 4) if denom else 0.0
    macro_f1 = round(float(np.mean([f1s[lab] for lab in labels])), 4) if labels else 0.0
    accuracy = round(correct / len(y_true), 4) if y_true else 0.0
    return {"accuracy": accuracy, "macro_f1": macro_f1, "per_intent_f1": f1s}


# ---------------------------------------------------------------- retrieval
def recall_at_k_and_mrr(gold_intents: list[str], hit_intent_lists: list[list[str]]) -> dict:
    r_at = {1: 0, 3: 0, 5: 0}
    mrr_sum = 0.0
    n = len(gold_intents)
    for gold, hits in zip(gold_intents, hit_intent_lists, strict=True):
        ranks = [i + 1 for i, h in enumerate(hits) if h == gold]
        for k in r_at:
            if any(r <= k for r in ranks):
                r_at[k] += 1
        if ranks:
            mrr_sum += 1.0 / min(ranks)
    return {
        "recall_at_1": round(r_at[1] / n, 4) if n else 0.0,
        "recall_at_3": round(r_at[3] / n, 4) if n else 0.0,
        "recall_at_5": round(r_at[5] / n, 4) if n else 0.0,
        "mrr": round(mrr_sum / n, 4) if n else 0.0,
    }


def intent_consistency_topk(gold_intents: list[str], hit_intent_lists: list[list[str]]) -> dict:
    fracs = []
    for gold, hits in zip(gold_intents, hit_intent_lists, strict=True):
        if hits:
            fracs.append(sum(1 for h in hits if h == gold) / len(hits))
    return {"mean_intent_consistency_topk": round(float(np.mean(fracs)), 4) if fracs else 0.0}


def useful_resolution_in_topk(flags: list[bool]) -> dict:
    return {"useful_resolution_rate": round(float(np.mean(flags)), 4) if flags else 0.0}


# --------------------------------------------------------------------- reply
REPLY_WEIGHTS = {
    "relevance": 0.25,
    "groundedness": 0.25,
    "actionability": 0.20,
    "brand_consistency": 0.15,
    "safety": 0.10,
    "concision": 0.05,
}


def weighted_reply_score(scores: dict) -> float:
    total = 0.0
    for k, w in REPLY_WEIGHTS.items():
        total += w * float(scores.get(k, 3))
    return round(total, 4)


def lexical_grounding(reply: str, evidence_texts: list[str], n: int = 3) -> float:
    """Deterministic n-gram overlap between the reply and retrieved evidence.

    A reply is lexically grounded when its content n-grams (minus stopwords)
    appear in the evidence texts. This complements the LLM judge, whose
    groundedness scores are noisy for small local models.
    """
    stop = {
        "the",
        "a",
        "an",
        "to",
        "of",
        "and",
        "or",
        "is",
        "are",
        "was",
        "we",
        "you",
        "your",
        "our",
        "us",
        "i",
        "in",
        "on",
        "for",
        "with",
        "this",
        "that",
        "it",
        "as",
        "at",
        "be",
        "have",
        "has",
        "so",
        "if",
        "please",
        "sorry",
        "thank",
        "thanks",
        "hello",
        "hi",
    }

    def content_tokens(text: str) -> list[str]:
        return [
            t for t in re.findall(r"[a-z']+", (text or "").lower()) if t not in stop and len(t) > 2
        ]

    toks = content_tokens(reply)
    if not toks:
        return 0.0
    grams = {" ".join(toks[i : i + n]) for i in range(max(1, len(toks) - n + 1))}
    ev_toks = content_tokens(" ".join(evidence_texts or []))
    ev_grams = {" ".join(ev_toks[i : i + n]) for i in range(max(1, len(ev_toks) - n + 1))}
    if not grams:
        return 0.0
    hit = len(grams & ev_grams) / len(grams)
    return round(hit, 4)


# ------------------------------------------------------------------- routing
def routing_metrics(
    pred_actions: list[str], gold_actions: list[str], reply_acceptable: list[bool]
) -> dict:
    n = len(pred_actions)
    if n == 0:
        return {}
    auto = [i for i, a in enumerate(pred_actions) if a == "auto_handle"]
    escal = [i for i, a in enumerate(pred_actions) if a == "escalate"]
    unsafe = [i for i in auto if not reply_acceptable[i]]
    coverage = len(auto) / n
    unsafe_rate = len(unsafe) / len(auto) if auto else 0.0
    # escalation precision: of escalations, how many "should" escalate (gold escalate
    # or reply not acceptable)
    good_escal = [i for i in escal if gold_actions[i] == "escalate" or not reply_acceptable[i]]
    escal_precision = len(good_escal) / len(escal) if escal else 0.0
    # escalation recall over gold-escalate cases
    gold_escal = [i for i, a in enumerate(gold_actions) if a == "escalate"]
    if gold_escal:
        escal_recall = sum(1 for i in gold_escal if pred_actions[i] == "escalate") / len(gold_escal)
    else:
        escal_recall = 0.0
    action_agreement = sum(1 for p, g in zip(pred_actions, gold_actions, strict=True) if p == g) / n
    return {
        "auto_handle_coverage": round(coverage, 4),
        "unsafe_auto_handle_rate": round(unsafe_rate, 4),
        "escalation_precision": round(escal_precision, 4),
        "escalation_recall": round(escal_recall, 4),
        "action_agreement": round(action_agreement, 4),
        "n_auto_handled": len(auto),
        "n_unsafe_auto_handled": len(unsafe),
    }


# ------------------------------------------------------------ judge agreement
def judge_human_agreement(
    judge_scores: list[float], human_scores: list[float], accept_threshold: float = 4.0
) -> dict:
    n = len(judge_scores)
    exact = sum(1 for j, h in zip(judge_scores, human_scores, strict=True) if abs(j - h) < 1e-9)
    within1 = sum(1 for j, h in zip(judge_scores, human_scores, strict=True) if abs(j - h) <= 1.0)
    j_pass = [j >= accept_threshold for j in judge_scores]
    h_pass = [h >= accept_threshold for h in human_scores]
    pass_agree = sum(1 for a, b in zip(j_pass, h_pass, strict=True) if a == b) / n
    if n > 1 and len(set(judge_scores)) > 1 and len(set(human_scores)) > 1:
        jm = np.mean(judge_scores)
        hm = np.mean(human_scores)
        num = sum((j - jm) * (h - hm) for j, h in zip(judge_scores, human_scores, strict=True))
        den = np.sqrt(sum((j - jm) ** 2 for j in judge_scores)) * np.sqrt(
            sum((h - hm) ** 2 for h in human_scores)
        )
        pearson = float(num / den) if den else 0.0
    else:
        pearson = 0.0
    return {
        "exact_agreement": round(exact / n, 4),
        "within_one_agreement": round(within1 / n, 4),
        "acceptable_agreement": round(pass_agree, 4),
        "pearson_r": round(pearson, 4),
        "n": n,
    }
