# AGENTS.md — Guidance for AI coding agents working in this repository

This file gives coding agents (and humans) the essential conventions for
working in the SupportPilot codebase. Read it fully before making changes.

## What this project is

An evidence-grounded customer-support agent for the AmazonHelp brand from
the Customer Support on Twitter dataset. Evaluation-first: trustworthiness
and measurable behavior matter more than cleverness. Runs fully locally
via Ollama — **no API keys, no cloud calls**. Reproducible in ≤15 minutes.

## Commands

```bash
make check       # env check (deps + ollama models) + pytest
make tests       # pytest (44 tests, no network, no ollama)
make lint        # ruff check + format check (config in pyproject.toml)
make typecheck   # mypy on src/
make format      # ruff format the whole tree
make reproduce   # full one-command evaluation (uses caches)
make evaluate    # re-run agent + baselines + judge on the golden set
```

Any command must run from the repository root: scripts use
`python -m scripts.<name>` and rely on the root being on `sys.path`
(see `scripts/_bootstrap.py`).

## Code style

- **ruff** is the formatter and linter; the config in `pyproject.toml` is
  the single source of truth. Line length 100. Run `make format` after
  edits.
- Type hints on `src/` code are checked by **mypy** (non-strict, but
  growing stricter over time — do not weaken the config to pass).
- No comments unless they explain a non-obvious *why*. The codebase
  intentionally has almost no comments.
- Public functions/classes in `src/` get short docstrings; scripts may
  stay lean.
- Never commit secrets. The project needs no API keys — do not add
  dependencies on paid/hosted services.
- Do not edit `.kilo/agent-manager.json` (UI state) if one appears.

## Project-specific invariants (do not break)

1. **Determinism**: seed 42, temperature 0, hash-based conversation
   splits. Cache keys must be stable functions of inputs — never include
   wall-clock time, random state, or machine-specific paths in cache keys
   or committed artifacts.
2. **No golden-set leakage**: threshold tuning uses the validation split
   only. Never fit/tune anything on `data/golden/golden_set.jsonl`.
3. **No hand-editing generated artifacts**: golden labels go through
   `scripts/annotate_golden.py --finalize`; report tables regenerate from
   `reports/results.json`.
4. **Safety gates**: `src/routing/guardrails.py` runs on every generated
   reply before any auto-handle decision. Guardrails or routing-threshold
   changes require re-running `make evaluate` and reporting deltas in the
   PR.
5. **Redaction**: no raw conversation text or personal data in logs or
   reports; use the masking utilities (`<url>`, `<user>` placeholders).
6. **Caches are committed** intentionally (`cache/index/*`, `cache/llm/*`,
   labelled corpus) to meet the 15-minute reproduction budget. Do not
   gitignore them; do not commit their absence.

## Where things live

```
src/
  data/         loader, cleaner, threading, leakage-safe splitter
  taxonomy/     intent classifier (kNN + LLM fallback + confidence)
  retrieval/    BM25, embedding index, hybrid fusion
  generation/    versioned prompts, grounded generator, reply cleaning
  routing/      risk tiers, guardrails, auto-handle policy
  evaluation/   metrics, baselines, LLM judge, calibration
  llm/          Ollama client with disk caching
  pipeline.py   end-to-end agent (trace-emitting)
  config.py     YAML config loader (configs/*.yaml)
scripts/        runnable stages: python -m scripts.<name>
tests/          pytest; no network, mocks for LLM clients
configs/        versioned YAML configs (brand, intents, thresholds)
data/           raw (not committed) / processed / golden (committed)
cache/          committed LLM + index caches (do not delete casually)
reports/        generated results + committed analysis reports
```

## Making changes

- One logical change per PR; branch names `feat/...`, `fix/...`.
- Conventional Commits (see `.gitmessage.txt` and `CONTRIBUTING.md`).
- Add/adjust tests for behavior changes; run `make lint typecheck tests`
  before declaring done.
- If the change touches intent/retrieval/generation/routing/evaluation,
  re-run `make evaluate` and report metric deltas honestly — including
  regressions.
- Never commit secrets. Never push without being asked.
