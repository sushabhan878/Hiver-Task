# SupportPilot

An **evidence-grounded customer-support agent** for one brand (AmazonHelp)
from the Customer Support on Twitter dataset. It understands requests with a
brand-specific intent taxonomy, retrieves similar resolved historical cases,
drafts grounded replies with a local LLM, and decides — with explicit,
inspectable reasons — when to auto-handle and when to escalate to a human.

> Optimized for trustworthy support automation, not maximum automation.

The system runs **fully locally** (Ollama; no API keys, no cloud calls) and
is reproducible in under 15 minutes.

## What it does

For every incoming customer message:

1. **Classify intent** — 13-intent AmazonHelp taxonomy; kNN over labelled
   historical cases with LLM fallback for ambiguity; calibrated confidence.
2. **Retrieve evidence** — hybrid BM25 (0.45) + embedding cosine (0.55) over
   5,613 resolved historical cases with resolution types.
3. **Draft a grounded reply** — local 3B LLM, JSON-mode structured output,
   versioned prompts, deterministic artifact cleaning.
4. **Route** — risk tiers (high-risk financial/account intents always
   escalate), confidence/retrieval gates, deterministic guardrails (refund
   promises, invented money, URLs, meta-leaks), automation score.
5. **Explain** — every prediction persists a full trace: intent scores,
   retrieved cases, guardrail flags, decision reason (fixed taxonomy).

## Quick start

### Environment

- Python 3.11+ (tested 3.14)
- [Ollama](https://ollama.com) running locally
- ~3 GB disk for models, ~450 MB for data

```bash
pip install -r requirements.txt

# local models (once)
ollama pull qwen2.5:3b
ollama pull nomic-embed-text
```

### One command

```bash
make reproduce
```

That runs: environment check → dataset download (mirrors) → brand profiling
→ corpus build → LLM labelling → index build → full evaluation
(agent + 3 baselines + judge + calibration + failure analysis).

**Cold run** (no caches): ~10–25 min (LLM labelling dominates; progress is
printed and resumable). **Warm run** (caches present): ~30 s.
All LLM/embedding calls are disk-cached (sha1 of model+prompt+options), so
repeated evaluation is deterministic and free.

### Expected output

```
Intent macro-F1:             0.506
Retrieval Recall@5:          0.709
Reply acceptability (judge): 0.246   [judge failed calibration - see report]
Auto-handle coverage:        0.116
Unsafe auto-handle (human):  0.300   [on the 50-example human-rated subset]
Escalation recall:           0.932

Results written to reports/results.json
```

Full report: [`reports/final_report.md`](reports/final_report.md)

## Repository map

```
configs/            brand, intents (taxonomy+risk tiers), thresholds (validation-tuned)
data/
  raw/              downloaded mirrors (not committed)
  processed/        conversations, labelled retrieval cases, splits
  golden/           hand-labelled golden set + annotation artifacts
src/
  data/             loader, cleaner, threading, leakage-safe splitter
  taxonomy/         intent classifier (kNN + LLM fallback + confidence)
  retrieval/        BM25, embedding index, hybrid fusion
  generation/       versioned prompts, grounded generator, reply cleaning
  routing/          risk tiers, guardrails, auto-handle policy
  evaluation/       metrics, baselines, LLM judge, calibration
  llm/              Ollama client with disk caching
  pipeline.py       end-to-end agent (trace-emitting)
scripts/            profile_dataset, build_corpus, label_corpus, build_index,
                    sample_golden, annotate_golden, evaluate, calibrate_judge,
                    double_annotate, analyze_failures, run_agent, ...
tests/              38 unit + integration tests (pytest)
reports/            results.json, final_report.md, brand_selection.md,
                    taxonomy_discovery.md, threshold_tuning.md,
                    annotation_guide.md, decision_log.md, ...
```

## Step-by-step commands

```bash
python -m scripts.profile_dataset    # brand scoring + selection report
python -m scripts.build_corpus       # clean, thread, split, extract cases
python -m scripts.label_corpus       # LLM intent labels for corpus (cached)
python -m scripts.build_index        # embeddings for retrieval
python -m scripts.sample_golden --n 200
python -m scripts.evaluate --draft   # assisted drafts for annotation
python -m scripts.annotate_golden     # produce drafts; hand-review; --finalize
python -m scripts.evaluate --thresholds   # tune on validation ONLY
python -m scripts.evaluate --systems agent,b1,b2,b3
python -m scripts.calibrate_judge    # judge vs human agreement
python -m scripts.double_annotate     # second-pass agreement report
python -m scripts.analyze_failures    # failure-mode extraction
python -m scripts.run_agent --message "where is my order?"
```

## Try the agent

```bash
python -m scripts.run_agent --message "My package still hasn't arrived and tracking hasn't changed for 4 days."
python -m scripts.run_agent --message "I want my money back immediately. Your service charged me twice."
```

The second message escalates (`HIGH_RISK_INTENT`) with a safe holding reply —
the system does not promise refunds it cannot execute.

## Evaluation summary (199-example golden set)

| System | Intent acc | Macro-F1 | Auto-handle | Unsafe auto-handle |
|---|---|---|---|---|
| Majority + canned | 0.166 | 0.022 | 0% (always escalates) | 0% |
| BM25 nearest case | 0.281 | 0.239 | 98.9% | **100%** |
| LLM no retrieval | 0.508 | 0.502 | 100% | 99.5% |
| **SupportPilot** | **0.528** | **0.506** | 11.6% | 30% (human-rated subset) |

- Golden set: stratified sampling; machine-assisted drafts; **140/199
  hand-corrected**; double-pass agreement 92.5% (kappa 0.916).
- Leakage: conversation-level hash splits; zero overlap verified; near-duplicate
  text scan implemented.
- Judge calibration: the local 3B judge **failed** calibration vs humans
  (within-one 10%, acceptable-agreement 28%) — all judge numbers are reported
  as noisy upper bounds; the human-rated subset is the safety ground truth.
  See `reports/judge_calibration.json` and the mandatory honesty section in
  the final report.

## Tests

```bash
python -m pytest tests -q     # 44 tests
```

Covers: text normalization, thread reconstruction, split determinism +
leakage checks, BM25 ranking, hybrid retrieval fusion, guardrails
(refund promises, invented money, URLs, meta-leaks), routing thresholds,
JSON parsing, and the full pipeline with mocked LLM.

## Development & quality gates

The project ships with industry-standard tooling; the config in
`pyproject.toml` is the single source of truth.

```bash
pip install -r requirements.txt -r requirements-dev.txt
pre-commit install              # optional: run the same gates on commit

make lint        # ruff check + ruff format --check
make format      # ruff autofix + format
make typecheck   # mypy (src/)
make tests       # pytest
make coverage    # pytest with coverage report
make all         # lint + typecheck + tests (what CI runs, minus Ollama)
```

- **Lint/format**: [ruff](https://docs.astral.sh/ruff/) (E, W, F, I, B, UP,
  SIM, C4 rules; line length 100)
- **Types**: mypy on `src/`
- **Docs/YAML formatting**: Prettier (`.prettierrc`) — Python is excluded
- **Git hooks**: pre-commit (`.pre-commit-config.yaml`) — whitespace, YAML/
  TOML/JSON validation, large-file and private-key detection, ruff, mypy,
  Prettier
- **CI**: GitHub Actions (`.github/workflows/ci.yml`) — lint, typecheck,
  tests on Ubuntu + Windows / Python 3.11 + 3.12, and a warm-cache
  reproduction smoke test

Contribution guide: [`CONTRIBUTING.md`](CONTRIBUTING.md) · Changes:
[`CHANGELOG.md`](CHANGELOG.md) · Security: [`SECURITY.md`](SECURITY.md)

## Reproducibility & determinism

- temperature 0 everywhere; fixed seed 42 in LLM options
- deterministic hash-based conversation splits
- all LLM/embedding outputs cached on disk with stable keys
- versioned prompts (`reply_v2`, `judge_v2`) and versioned configs
- full evaluation re-runs in ~30 s warm, ~10–25 min cold
- headline numbers regenerate from `reports/results.json` — nothing in this
  README is hand-entered

## Privacy

The dataset is public, but conversations are still treated as sensitive:
no real personal data in logs, no raw conversation text in reports beyond
short redacted excerpts (`<url>`, `<user>` masking), no secrets committed
(the system needs no API keys at all).

## Cost

$0.00 — every model runs locally via Ollama.
