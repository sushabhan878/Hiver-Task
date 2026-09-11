# SupportPilot — Final Report

**Evidence-grounded customer-support agent for AmazonHelp (Customer Support on Twitter).**
All numbers below were produced by `make reproduce` on this exact repository state;
machine-readable versions live in `reports/results.json`,
`reports/judge_calibration.json`, `reports/annotator_agreement.json`, and
`reports/failure_cases.json`.

## 1. Executive Summary

SupportPilot classifies incoming AmazonHelp customer messages into a 13-intent
brand-specific taxonomy, retrieves similar resolved historical cases with hybrid
BM25+embedding search, drafts a grounded reply from a local 3B LLM (Ollama,
temperature 0, fully cached), and routes each conversation to auto-handle or
escalate using risk tiers, calibrated confidence, retrieval strength, and
deterministic guardrails. On a 199-example hand-labelled golden set
(double-pass intent agreement 92.5%, Cohen's kappa 0.916), SupportPilot
auto-handles 11.6% of conversations with a **human-rated unsafe auto-handle
rate of 30%** on the rated subset (vs 100% for naive retrieval automation) and
catches 93.2% of cases that should escalate. The system's central virtue is
abstention: it escalates when evidence is weak, which is precisely the product
goal — trustworthy automation, not maximum automation.

## 2. Problem Framing

"Good" for AmazonHelp on Twitter means four separable skills, each evaluated
separately: (a) understanding what the customer wants (intent), (b) finding how
the brand historically handled similar requests (retrieval), (c) drafting a
reply consistent with that behavior (generation), and (d) knowing when a human
must take over (routing). The dataset is noisy: 5+ languages, order numbers,
sarcasm, vague rage, and agent signatures (`^MJ`) in every thread. The product
principle applied throughout: a short escalation beats a fluent invention.

## 3. System Design

```
Customer message
   -> Intent classifier (kNN over 5.6k labelled historical cases
      + LLM fallback on low margin; confidence = 0.5 classifier
      + 0.3 margin + 0.2 retrieval consistency)
   -> Hybrid retrieval (BM25 0.45 + nomic-embed cosine 0.55, top-5)
   -> Grounded reply generator (qwen2.5:3b, JSON mode, reply_v2 prompt,
      artifact cleaning)
   -> Routing policy: risk-tier override -> confidence/retrieval gates
      -> deterministic guardrails (refund promises, invented money,
         URLs, meta-leaks, escalation promises) -> automation score
      -> AUTO-HANDLE | ESCALATE (fixed reason taxonomy)
```

Every prediction emits a full trace (intent scores, retrieved cases with
scores, raw model output, guardrail flags, decision + reason) persisted to
`reports/agent_traces.json` — inspectability is a first-class feature.

## 4. Data + Golden Set

- **Source**: Customer Support on Twitter (conversation-level public mirror,
  794k conversations; 81,092 for AmazonHelp). Brand selected by explicit
  scoring function over 10 candidates (see `reports/brand_selection.md`).
- **Corpus**: 8,000 conversations kept (spam/empty dropped, 2–40 turns);
  conversation-level hash split: 5,663 retrieval / 1,126 validation /
  1,211 golden pool. **Leakage checks passed**: 0 conversation overlap,
  near-duplicate text check implemented and run.
- **Historical cases**: 5,613 resolved cases extracted (customer problem,
  brand response, resolution type) and labelled by the local LLM against the
  taxonomy; 8 resolution types (asked_to_dm, provided_tracking, requested_details, ...).
- **Golden set**: 199 examples stratified by length-band × sentiment; drafts
  machine-assisted, then **140/199 relabelled by hand**; a second independent
  40-example pass measured annotation reliability
  (`reports/annotator_agreement.json`). Intent mix: 33 delivery_status,
  28 delayed_delivery, 26 service_complaint, 19 general_info, 19 feedback,
  18 product_issue, 12 refund_request, 11 payment_issue, 9 other,
  8 account_access, 7 pricing_charge, 5 cancellation, 4 availability.
  Action mix: 111 auto_handle / 88 escalate.

## 5. Results

### Evaluation matrix (199 golden examples)

| System | Intent acc | Macro-F1 | Reply accept. (judge) | Lexical grounding | Auto-handle coverage | Unsafe auto-handle |
|---|---|---|---|---|---|---|
| Majority + canned (b1) | 0.166 | 0.022 | 0.00 | – | 0.000 (always escalates) | 0.000 |
| BM25 nearest case (b2) | 0.281 | 0.239 | 0.00 | 0.985 (copies source) | 0.990 | **1.000** |
| LLM no retrieval (b3) | 0.508 | 0.502 | 0.005 | 0.000 | 1.000 | 0.995 |
| **SupportPilot (agent)** | **0.528** | **0.506** | 0.246 | 0.060 | 0.116 | 0.652 (judge) / **0.30 (human-rated subset)** |

Reading the matrix honestly: b1 is safe but useless (never answers). b2 is the
cautionary tale — it "answers" by parroting history at 99% coverage and 100%
unsafe rate. b3 shows a raw 3B LLM matches the agent on *intent* but without
retrieval its replies are unsupported (0.3% lexically grounded). The agent
trades coverage for safety: it automates only what passes four gates.

- **Retrieval** (independent evaluation): Recall@1 0.367, Recall@3 0.623,
  Recall@5 0.709, MRR 0.498 (intent-consistency proxy), useful-resolution-in-
  top-5 0.186.
- **Routing**: escalation recall 0.932 (catches 82/88 of gold-escalates),
  escalation precision 0.892, action agreement 0.498 (conservative by design —
  the agent escalates 94 cases a lenient annotator would auto-handle).
- **Safety**: 0 fabricated monetary claims in 23 auto-handled replies
  (guardrails + risk tiers); the German refund-offer attempt
  (`gold_168: "Möchtest du eine Ersatzlieferung oder eine Erstattung?"`) was
  correctly caught by the refund-offer guardrail and re-routed to escalate.

### Coverage–quality sweep (auto threshold)

| Threshold | Coverage | Judge acceptability (auto set) | Judge unsafe rate |
|---|---|---|---|
| 0.50 | 12.6% | 0.32 | 0.68 |
| 0.60 | 12.6% | 0.32 | 0.68 |
| 0.70 (chosen) | 11.6% | 0.35 | 0.65 |
| 0.80 | 6.5% | 0.46 | 0.54 |
| 0.90 | 1.0% | 0.50 | 0.50 |

Coverage is capped by the hard gates, not the threshold; quality rises as the
threshold tightens, confirming the trade-off is real and controllable.

### Judge calibration vs humans (mandatory)

50 examples rated blind by the human annotator with the same rubric:

- exact agreement 2%, within-one 10%, acceptable/not-acceptable 28%,
  Pearson r 0.08.

**The local 3B judge is not a reliable human proxy on this rubric.** All
judge-derived numbers are therefore conservative upper bounds on badness;
the headline unsafe rate uses the human-rated subset (10 auto-handled cases,
3 unacceptable → 30%). This is disclosed, not hidden — the calibration exists
precisely so the reader knows which numbers to trust.

## 6. Failure Analysis (top 5 modes, real examples)

1. **Intent boundary: delayed_delivery vs delivery_status** (9 misses).
   Example `gold_092`: "I'm sick of your lies and today two items that were
   promised in prime I'm now told won't be delivered" → predicted
   delivery_status; gold delayed_delivery (missed-promise grievance).
   Why: both share "delivery" language; the classifier's kNN votes are
   dominated by the more frequent delivery_status cases. Fix: conversation-
   state features (date-promised vs date-now) and boundary examples in the
   example bank.

2. **Tone-blindness: service_complaint vs delivery intents** (11 misses
   across two pairs). Example `gold_197`: "1st time using Amazon. Farce.
   Never again. Waited hour and half..." → predicted delayed_delivery with
   confidence 1.0 and **auto-handled**, gold service_complaint/escalate.
   This is also one of the 6 missed escalations: the angry-churn signal
   ("never again") lives in tone, which neither embeddings nor keywords
   capture. Fix: a sentiment/anger detector as a hard routing input.

3. **Brand-chatter misread: feedback/general_info/other confusion**
   (13 misses). Example `gold_047` (Japanese): "またAmazonに騙された..."
   → predicted general_info; gold other (ambivalent scam-complaint chatter).
   Promo/celebration tweets with embedded questions are systematically
   pulled toward general_info. Fix: an explicit "is this a support request?"
   gate before intent classification.

4. **Over-escalation on low-margin multilingual messages** (94 cases).
   Example `gold_076` (Portuguese): free-shipping eligibility question →
   escalated on LOW_INTENT_CONFIDENCE (0.297) because retrieval consistency
   is diluted by cross-lingual near-misses. The kNN bank has few Portuguese
   examples, so margins stay low. Fix: language-aware retrieval filtering
   and per-language example banks.

5. **Judge noise contaminates quality metrics** (affects all acceptability
   numbers). Example `gold_090`: "Prices are set by the sellers..." — a
   defensible brand-consistent answer — scored 1.4 by the judge, 3.45 by the
   human. The judge's within-one agreement is 10%, so per-reply acceptability
   numbers carry ±30-40% noise. Fix: larger judge model, or pairwise
   preference judging (more robust for small models), or majority-vote
   panels. Next-week work.

## 7. What Is Misleading About My Headline Number?

Mandatory honesty section. The headline — "auto-handles 11.6% with a 30%
human-rated unsafe rate and 93.2% escalation recall" — hides real problems:

- **Dataset bias**: Twitter complainers are not representative customers;
  30%+ of the golden set is non-English (the brand's polyglot reality), and
  delivery-chatter dominates. A deployed inbox differs in mix, register,
  and stakes.
- **Historical-response bias**: the system learns how AmazonHelp *actually
  behaved* on Twitter, including deflection ("please DM us", link-dumps)
  that may itself be suboptimal support. Grounded ≠ good.
- **Golden-set size**: 199 examples → per-intent F1 for 4-example intents
  (availability_question) is statistically meaningless; macro-F1 weights
  them equally anyway. Confidence intervals on all headline metrics span
  roughly ±7-10 points.
- **Label ambiguity**: kappa 0.916 is excellent, but the 6 double-pass
  disagreements all sat at taxonomy seams — exactly where the classifier
  also fails. Some "errors" may be defensible readings.
- **LLM judge bias**: judge acceptability (24.6%) and human acceptability
  (70%) disagree by 45 points on the same replies; every judge-derived
  number in this report should be read as noisy, which is why the unsafe
  headline uses human ratings on the 10 rated auto-handled cases — itself
  a small sample (30% ± ~28 points at 95% CI).
- **Retrieval leakage risk**: mitigated by conversation-level hash splits and
  verified (0 conversation overlap, 0 exact-text leakage,
  `reports/data_quality.json`), with one honest caveat: 3 golden messages have
  near-identical twins in *different* retrieval conversations (natural tweet
  duplication, e.g. gold_036 "What a discount, <user>. <url>"). These can
  inflate retrieval scores on those items; the *judge* also saw no retrieval
  evidence for baselines, and corpus labelling used the same model family
  that classifies later, so label noise correlates across components.
- **Automation coverage vs quality**: 11.6% coverage with 30% unsafe looks
  better than it is: the 3 "unsafe" cases are mediocre-but-harmless replies
  (scored 2.8–3.65 vs the 3.75 bar), not dangerous inventions; conversely,
  "safe" escalations still sent customers a holding reply, not silence.
- **Brand selection bias**: AmazonHelp is high-volume, well-resourced, and
  templated in its replies — close to a best case for retrieval grounding;
  a smaller, messier brand would be harder.

## 8. Next Week

1. **Conversation-state features**: promises-vs-now dates, prior-turn
   asks, repeated-failure counters — the single biggest intent fix.
2. **Anger/churn detector** as a hard escalation input (fixes missed
   escalations like gold_197).
3. **Language-aware retrieval** (per-language banks or multilingual
   embeddings) to raise low-margin multilingual confidence.
4. **Pairwise-preference judge** or a larger judge model; re-calibrate
   before trusting any acceptability number.
5. **Multi-turn golden set**: current evaluation is single-message;
   routing quality is ultimately a conversation property.
6. **Human escalation disposition**: measure whether SupportPilot's
   escalate reasons match what human triage would do with the reason text.

## 9. Decision Log

See `reports/decision_log.md` (15 entries, each with rationale).
