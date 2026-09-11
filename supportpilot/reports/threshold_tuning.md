# Threshold Tuning (validation split only)

**Never tuned on the golden set.** All numbers below come from the 1,126-conversation
validation split (conversation-level, leakage-safe from golden pool).

## Procedure

1. For 300 sampled validation conversations, we computed the same signals the
   online policy uses: intent confidence (kNN + margin + retrieval consistency),
   hybrid retrieval score, and the hard gates:
   - intent_confidence >= 0.55
   - retrieval_best >= 0.40
   - at least one retrieved case >= 0.55 (strong match)
2. Only 81/300 conversations survived the hard gates. The gates, not the
   threshold, are the primary safety mechanism — by design.
3. Automation-score distribution of the gated pool:

| percentile | automation score |
|---|---|
| p25 | 0.79 |
| p50 | 0.81 |
| p75 | 0.83 |

## Decision

- `AUTO_THRESHOLD = 0.70`. The gated-pool score mass sits at 0.79–0.83, so any
  threshold in [0.5, 0.75] auto-handles the entire gated pool; the sweep
  thresholds (0.5–0.9) reported in the final results show the trade-off curve.
- Hard gates (risk tier, intent confidence, retrieval strength, guardrails)
  remain the dominant escalation drivers; the automation threshold is a final
  backstop rather than the main control.

## Notes

- The threshold is deliberately loose because every auto-handle candidate has
  already passed four independent checks. Tightening it further mostly reduces
  coverage without changing which *risky* cases are escalated.
- The coverage/quality sweep in reports/results.json shows coverage and
  (judge-rated) acceptability at thresholds 0.50–0.90 for transparency.
