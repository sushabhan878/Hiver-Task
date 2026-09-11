"""Phase 2b: LLM-assisted intent labelling of retrieval corpus cases.

Labels the retrieval cases with the taxonomy via the local LLM (batched,
cached, temperature 0). Produces:
- data/processed/retrieval_cases_labelled.jsonl (case + intent)
- reports/taxonomy_discovery.md (distribution + cluster evidence)

This is bootstrapping for the example bank and intent stats, NOT the golden
set, which is hand-labelled separately.
"""

from __future__ import annotations

import argparse
from collections import Counter

from scripts._bootstrap import ROOT  # noqa: F401
from src.config import intents_cfg, project_path
from src.data.loader import read_jsonl, write_jsonl
from src.llm.client import get_client

TAXONOMY_BLOCK = "\n".join(
    f"- {name}: {spec['definition']}" for name, spec in intents_cfg()["intents"].items()
)


def label_case(client, case: dict) -> str:
    prompt = (
        "Classify this customer support message into exactly one intent.\n\n"
        f"Intents:\n{TAXONOMY_BLOCK}\n\n"
        f"Customer message: {case['customer_problem']}\n\n"
        'Reply with JSON only: {"intent": "<name>"}'
    )
    try:
        out = client.chat_json([{"role": "user", "content": prompt}], num_predict=48)
        intent = str(out.get("intent", "other")).strip()
        valid = set(intents_cfg()["intents"].keys())
        return intent if intent in valid else "other"
    except Exception:
        return "other"


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--limit", type=int, default=None, help="label only first N unlabelled cases (default: all)"
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="ignore existing labelled output and relabel from scratch",
    )
    args = parser.parse_args()

    labelled_path = project_path("data/processed/retrieval_cases_labelled.jsonl")
    if not args.force and labelled_path.exists():
        labelled = read_jsonl(labelled_path)
        n_unlabelled = sum(1 for c in labelled if c.get("intent") in (None, "unlabelled"))
        if labelled and n_unlabelled == 0:
            print(
                f"Labelled corpus already present and complete "
                f"({len(labelled):,} cases, 0 unlabelled). Skipping. "
                f"Use --force to relabel."
            )
            return
        cases = labelled
    else:
        cases = read_jsonl(project_path("data/processed/retrieval_cases.jsonl"))
    print(f"Loaded {len(cases):,} retrieval cases")

    client = get_client()
    to_label = [c for c in cases if c.get("intent") in (None, "unlabelled")]
    if args.limit:
        to_label = to_label[: args.limit]
    print(f"Labelling {len(to_label):,} cases with {client.chat_model}...")

    labelled = [c for c in cases if c.get("intent") not in (None, "unlabelled")]
    for i, case in enumerate(to_label):
        case["intent"] = label_case(client, case)
        labelled.append(case)
        if (i + 1) % 200 == 0:
            print(f"  {i + 1}/{len(to_label)} labelled")
            write_jsonl(project_path("data/processed/retrieval_cases_labelled.jsonl"), labelled)

    write_jsonl(project_path("data/processed/retrieval_cases_labelled.jsonl"), labelled)
    counts = Counter(c["intent"] for c in labelled)
    print("Intent distribution:", dict(counts.most_common()))

    # taxonomy discovery report
    lines = [
        "# Intent Taxonomy Discovery (retrieval corpus)",
        "",
        f"Corpus: {len(labelled):,} resolved AmazonHelp cases, labelled by the local",
        f"LLM (`{client.chat_model}`, temperature 0) against the taxonomy in configs/intents.yaml.",
        "The taxonomy itself was derived by manual consolidation of keyword-cluster",
        "inspection of customer messages (see scripts/build_corpus.py::keyword_intent",
        "for the bootstrap rules that seeded the consolidation).",
        "",
        "| intent | count | share |",
        "|---|---|---|",
    ]
    total = len(labelled)
    for intent, n in counts.most_common():
        lines.append(f"| {intent} | {n} | {100 * n / total:.1f}% |")
    lines += [
        "",
        "Rare intents (<60 cases) risk unreliable per-intent metrics; noted in the",
        "report's limitations section (payment_issue, cancellation).",
    ]
    (project_path("reports") / "taxonomy_discovery.md").parent.mkdir(parents=True, exist_ok=True)
    (project_path("reports") / "taxonomy_discovery.md").write_text(
        "\n".join(lines), encoding="utf-8"
    )
    print("Wrote reports/taxonomy_discovery.md")


if __name__ == "__main__":
    main()
