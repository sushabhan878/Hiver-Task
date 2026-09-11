# Support

## Where to get help

| Need | Channel |
|---|---|
| Bug reports | [Open an issue](../../issues/new?template=bug_report.md) using the bug template |
| Feature ideas | [Open an issue](../../issues/new?template=feature_request.md) using the feature template |
| Questions / usage help | [GitHub Discussions](../../discussions) or an issue labeled `question` |
| Security vulnerabilities | Private report — see [`SECURITY.md`](SECURITY.md). **Never** a public issue |
| Code of conduct concerns | `conduct@supportpilot.example` — see [`CODE_OF_CONDUCT.md`](CODE_OF_CONDUCT.md) |

## Before you file an issue

1. **Search** existing issues and discussions to avoid duplicates.
2. **Reproduce from a clean state** — the fastest sanity check:

   ```bash
   make check        # environment + dependencies + Ollama models
   make tests        # 44 tests, should all pass
   ```

3. **Attach the basics**: OS, Python version, Ollama version and models
   pulled, the exact command, and the full traceback (redact any personal
   data).

## Common problems

- **`make reproduce` seems slow on first run** — expected: cold runs
  download data and label ~5.6k cases with a local LLM (~10–25 min). Warm
  runs take ~30 s thanks to disk caches in `cache/`.
- **Connection refused on 127.0.0.1:11434** — Ollama is not running;
  start it (`ollama serve`) and re-run `make check`.
- **Model not found** — run `ollama pull qwen2.5:3b` and
  `ollama pull nomic-embed-text`.
- **Windows paths** — the project is developed on Windows but tested
  cross-platform; if you hit a path bug, please open an issue with the
  traceback.

## Response expectations

This is a small project maintained on a best-effort basis. Bug reports
that include a minimal reproduction get answered first.
