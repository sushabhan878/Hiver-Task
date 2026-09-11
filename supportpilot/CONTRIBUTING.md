# Contributing to SupportPilot

Thanks for your interest in making SupportPilot better. This project is
evaluation-first: every change that can affect predictions, metrics, or
routing decisions must come with evidence.

## Prerequisites

- Python 3.11+ (CI runs 3.11 and 3.12; development tested on 3.14)
- [Ollama](https://ollama.com) with the models below (local, no API keys)
- ~3 GB disk for models, ~450 MB for data

```bash
git clone <your-fork-url>
cd supportpilot
python -m venv .venv
.venv\Scripts\activate         # Windows PowerShell
pip install -r requirements.txt -r requirements-dev.txt
ollama pull qwen2.5:3b
ollama pull nomic-embed-text
pre-commit install
```

## Development workflow

1. **Fork & branch** — branch from `main` using a descriptive name:
   `feat/hybrid-retrieval-weight-tuning`, `fix/guardrail-url-false-positive`.
2. **Make your change** — keep diffs focused; one logical change per PR.
3. **Run the gates locally** — CI will run these exact commands:

   ```bash
   make lint        # ruff check + format check
   make typecheck   # mypy on src/
   make tests       # pytest (unit + integration)
   ```

4. **Full evaluation before merging** — if you touched anything under
   `src/` (intents, retrieval, generation, routing, evaluation) or
   `configs/`:

   ```bash
   make evaluate    # re-run agent + baselines on the golden set
   ```

   Compare `reports/results.json` before/after and include the deltas in
   your PR description. Regressions in escalation recall or unsafe
   auto-handle will block the merge.

5. **Open a Pull Request** — fill in the PR template. PRs without evidence
   for behavior-affecting changes will be marked `needs-evidence`.

## Code style

- Formatting and linting are enforced by [ruff](https://docs.astral.sh/ruff/)
  via `pyproject.toml` — the checked-in config is the single source of
  truth. Run `make format` before committing.
- Line length is 100 characters.
- Prefer explicit, self-documenting names (the linter rejects ambiguous
  names like `l`).
- Docstrings on public functions/classes in `src/`; scripts may stay lean.
- No comments that narrate the obvious; comments explain *why*.

## Testing expectations

- New features and bug fixes require tests (unit or integration) that fail
  before the change and pass after.
- Tests run without network or Ollama: mock or use the disk-cached LLM
  fixtures. Anything hitting Ollama belongs in `tests/` only with mocked
  clients.
- Aim to keep or raise coverage on the module you touched:
  `make coverage`.

## Evaluation integrity rules

These are non-negotiable, project-specific rules:

- **Never tune on the golden set.** Threshold tuning uses the validation
  split only (`python -m scripts.evaluate --thresholds`).
- **Never hand-edit** `data/golden/golden_set.jsonl` outputs — corrections
  go through `scripts/annotate_golden.py --finalize`.
- **Report honestly.** If a metric regressed, say so in the PR; the
  project's culture is honest reporting over flattering numbers (see the
  judge-calibration caveat in `reports/final_report.md`).
- Determinism: seed 42, temperature 0, hash-based splits. Do not introduce
  non-determinism (wall-clock keys, random iteration order) into artifacts
  or cache keys.

## Commit messages

We follow [Conventional Commits](https://www.conventionalcommits.org/):

```
<type>(<scope>): <short imperative summary>

<body: what and why>

<footer: BREAKING CHANGE, issue refs>
```

Types: `feat`, `fix`, `docs`, `test`, `refactor`, `perf`, `build`, `ci`,
`chore`. Scopes commonly used: `retrieval`, `routing`, `generation`,
`taxonomy`, `evaluation`, `data`, `pipeline`, `docs`, `config`.

A `.gitmessage.txt` template is provided:

```bash
git config commit.template .gitmessage.txt
```

## Reporting bugs and asking questions

- Bugs: open an issue using the bug report template.
- Questions: open a discussion or an issue labeled `question`.
- Vulnerabilities: **do not open a public issue** — see `SECURITY.md`.

## License

By contributing, you agree that your contributions will be licensed under
the MIT License in `LICENSE`.
