# Decision Log

Non-obvious engineering and product decisions, with rationale.

1. **Brand = AmazonHelp** via explicit scoring (conversation volume, reply
   rate 100%, multi-exchange 63%, intent diversity, thread completeness);
   largest pool gives the retrieval corpus enough resolved cases. Not chosen
   "because biggest" alone — the composite score also ranked it first among
   10 candidates on quality terms.

2. **Conversation-level, hash-based splitting** instead of time-based: the
   public conversation mirror drops timestamps, so true time-aware splitting
   is impossible. sha1(seed:conversation_id) mapping is deterministic across
   machines and guarantees a conversation never straddles splits. Documented
   as a deviation from the PRD's preferred time-aware split.

3. **8-15 intents -> 13 intents** (incl. `other`): fewer would collapse
   delivery_status/delayed_delivery distinctions that drive different
   replies; more would make the 199-example golden set per-intent cells too
   sparse for stable F1 (already ~4-33 per intent).

4. **Conversations excluded from retrieval corpus** unless: brand replied
   substantively (>=15 chars), a resolution type was extractable, and a
   customer problem text exists. 5,613 of 5,663 retrieval-split conversations
   qualified. Unclear resolutions would poison evidence.

5. **Hybrid retrieval (BM25 0.45 + embeddings 0.55)**: BM25 catches order-
   number strings and keywords; embeddings catch paraphrases and non-English.
   Neither alone reached usable recall on spot checks.

6. **Retrieval evidence required for auto-handle**: the routing policy
   requires top-1 hybrid score >= 0.40 AND at least one case >= 0.55 AND
   judge-independent guardrails pass. Auto-handling without evidence is how
   b2 (BM25-nearest) ends up 100% unsafe.

7. **High-risk intents default to escalation** (refund, payment, account):
   monetary/account actions are irreversible and evidence in this corpus is
   advisory chatter, not authoritative policy; no historical tweet is
   sufficient basis to promise money movements.

8. **Thresholds tuned only on validation**: AUTO_THRESHOLD=0.70 chosen from
   the validation split's gated-pool score percentiles; never tuned on the
   golden set (reports/threshold_tuning.md).

9. **Stratified golden sampling** over length-band x sentiment cells with
   per-cell quota, not random: random sampling of this corpus over-weights
   short neutral delivery chatter and would miss rare intents.

10. **Assisted + reviewed labelling**: machine drafts (keyword rules +
    classifier) seeded every golden label, then 140/199 were changed in
    human review. The draft is NOT the label. Double-pass agreement (92.5%,
    kappa 0.916) is reported before any result.

11. **LLM judge calibrated before use — and it failed calibration**
    (within-one 10%, acceptable-agreement 28%, Pearson 0.08 on the final
    pass). Consequence: judge acceptability is reported but the human-rated
    subset is the ground truth for the unsafe-auto-handle headline. We do not
    discard the judge; we disclose it.

12. **LLM-without-retrieval baseline included** to demonstrate grounding's
    value: b3 matches the agent on intent accuracy (0.51 vs 0.53) but its
    replies are ungrounded (0/199 lexically grounded acceptable, 99.5%
    judge-unsafe at full coverage). Retrieval, not the model, buys safety.

13. **No real support actions executed** — no refunds, cancellations, or
    account changes: this is a drafting/routing prototype; execution would
    require internal systems and authorization that do not exist here.

14. **temperature=0 + disk-cached LLM/embedding calls keyed by sha1(model,
    prompt, options)**: full evaluation re-runs in ~26s warm; first cold run
    ~12 min. Reproduction under 15 minutes depends on these caches, which
    are deterministic; cold-cache reruns stay within budget because the
    corpus is capped at 8,000 conversations.

15. **Some failures intentionally left unresolved**: delivery_status vs
    delayed_delivery boundary confusion and service_complaint tone
    ambiguity persist because fixing them requires either multi-turn
    conversation state (not in scope for a single-message pipeline) or a
    larger local judge; both are recorded as next-week work rather than
    half-fixed now.
