## Summary

<!-- What does this PR do and why? Link the issue it closes (Closes #N). -->

## Change type

<!-- Check one -->
- [ ] `feat` — new capability
- [ ] `fix` — bug fix
- [ ] `docs` — documentation only
- [ ] `test` — tests only
- [ ] `refactor` / `perf` — no behavior change
- [ ] `build` / `ci` / `chore` — tooling

## Does this affect agent behavior?

<!-- If anything under src/ or configs/ changed, this MUST be "yes" -->
- [ ] Yes — evaluation evidence required below
- [ ] No — pure docs/tooling change

## Evaluation evidence (required if behavior-affecting)

Commands run: `make evaluate` (agent + baselines + judge on the golden set)

| Metric | Before | After | Δ |
|---|---|---|---|
| Intent macro-F1 | | | |
| Retrieval Recall@5 | | | |
| Auto-handle coverage | | | |
| Escalation recall | | | |
| Unsafe auto-handle (human subset) | | | |

Safety invariants (check all):

- [ ] No tuning on the golden set (validation split only)
- [ ] Guardrails run on every generated reply before auto-handle
- [ ] Determinism preserved (seed 42, temp 0, stable cache keys)
- [ ] No raw conversation text / personal data added to logs or reports
- [ ] No secrets or new paid/hosted service dependencies

## Checklist

- [ ] Branch is up to date with `main`
- [ ] `make lint` passes
- [ ] `make typecheck` passes
- [ ] `make tests` passes (44+ tests)
- [ ] Tests added/updated for the change
- [ ] `CHANGELOG.md` updated (user-visible changes)
- [ ] PR title follows Conventional Commits (`type(scope): summary`)

## Notes for reviewers

<!-- Anything non-obvious, risky, or worth a second pair of eyes. -->
