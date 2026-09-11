# Hiver SDE Intern Take-Home --- AI Customer Support Agent

## Detailed Product Requirements Document (PRD)

**Project codename:** SupportPilot\
**Primary dataset:** Customer Support on Twitter
(`thoughtvector/customer-support-on-twitter`)\
**Target deliverable:** A reproducible, evaluation-first AI support
agent for one selected brand\
**Audience:** Hiver SDE internship reviewers\
**Primary objective:** Demonstrate that the system is trustworthy,
measurable, reproducible, and technically well-engineered---not merely
that an LLM can generate plausible replies.

------------------------------------------------------------------------

# 1. Executive Summary

Build an AI customer-support agent for one brand represented in the
Customer Support on Twitter dataset.

For every incoming customer message, the system must:

1.  **Understand the request** by assigning it to a small,
    brand-specific intent taxonomy.
2.  **Retrieve evidence** from historically resolved conversations that
    are similar to the incoming request.
3.  **Draft a grounded response** that reflects how the brand
    historically handled similar situations.
4.  **Decide whether to auto-handle or escalate** the conversation to a
    human.
5.  **Explain the decision** using explicit evidence and confidence
    signals.
6.  **Prove performance** using a hand-labelled golden set, automated
    metrics, baselines, an LLM judge calibrated against humans, and
    detailed failure analysis.

The core product philosophy is:

> **Optimize for trustworthy support automation, not maximum
> automation.**

A high-quality system should know when it does not have enough evidence
and should escalate instead of confidently inventing a policy, refund,
commitment, or troubleshooting step.

------------------------------------------------------------------------

# 2. Problem Statement

Customer-support conversations on social media are noisy:

-   tweets are short and ambiguous;
-   customers may send multiple messages;
-   brands have different policies and tones;
-   conversations contain URLs, mentions, emojis, spelling errors, and
    incomplete context;
-   the same intent can be expressed in many ways;
-   historical replies are not necessarily correct or consistent;
-   some requests are safe to automate while others require a human.

A generic chatbot can generate fluent responses but fluency is not
enough.

The system therefore needs to answer four separate questions:

### Q1 --- What is the customer trying to do?

Example: - delivery status - refund request - payment problem - account
access - product/service issue - cancellation - complaint - general
information

### Q2 --- What has this brand historically done for similar requests?

The answer should come from retrieved historical evidence rather than
unsupported model knowledge.

### Q3 --- What should the agent say?

The response should be concise, brand-appropriate, and grounded in
retrieved examples.

### Q4 --- Is automation safe?

The system should auto-handle only when intent confidence, retrieval
quality, and risk are sufficiently strong.

------------------------------------------------------------------------

# 3. Product Vision

Create a small but credible **evidence-grounded support copilot**.

The ideal output for one incoming message is:

``` json
{
  "intent": "refund_request",
  "confidence": 0.91,
  "action": "escalate",
  "reason": "Refund policy is not sufficiently supported by retrieved historical examples.",
  "reply": "I’m sorry you’ve had trouble with this. I’d like to make sure your refund request is handled correctly. Please send us your order details via DM and our support team can review it.",
  "evidence": [
    {
      "conversation_id": "abc123",
      "relevance": 0.89,
      "resolution_summary": "Agent asked customer to provide order details via DM before reviewing refund."
    }
  ]
}
```

The agent is not expected to execute refunds, change accounts, issue
credits, or access private customer systems.

This assignment focuses on **understanding, retrieval, drafting, and
routing**.

------------------------------------------------------------------------

# 4. Goals

## 4.1 Primary Goals

-   Select one brand with enough high-quality conversations.
-   Build a defensible intent taxonomy from the selected brand's data.
-   Create a clean conversation-level dataset from raw tweets.
-   Build a retrieval system for historically resolved cases.
-   Generate grounded support replies.
-   Build a transparent auto-handle/escalate policy.
-   Construct a 150--250 example golden evaluation set.
-   Compare against at least two baselines.
-   Evaluate reply quality with automated metrics and an LLM judge.
-   Measure agreement between the LLM judge and human ratings.
-   Perform systematic failure analysis.
-   Make the entire headline evaluation reproducible in under 15 minutes
    on a subsample.
-   Document non-obvious engineering/product decisions.

## 4.2 Secondary Goals

-   Demonstrate production-minded architecture.
-   Make the system easy to inspect and debug.
-   Preserve evidence for every generated answer.
-   Make unsafe hallucination visible.
-   Keep API/LLM costs low enough for repeated evaluation.

------------------------------------------------------------------------

# 5. Non-Goals

Explicitly do **not** build:

-   a full production Twitter/X integration;
-   a live customer-support inbox;
-   actual refund/payment/account operations;
-   authentication or authorization infrastructure;
-   multilingual support unless the selected dataset requires it;
-   fine-tuning unless there is a strong empirical reason;
-   a complicated agentic workflow;
-   a large enterprise deployment;
-   a perfect representation of all brands in the dataset.

The assignment rewards a strong, measurable prototype over unnecessary
infrastructure.

------------------------------------------------------------------------

# 6. Success Criteria

The project succeeds if a reviewer can:

1.  Clone the repository.
2.  Install dependencies.
3.  Download or load the documented dataset subset.
4.  Run one command.
5.  Reproduce the headline evaluation.
6.  Inspect example predictions.
7.  Understand why the system auto-handled or escalated a case.
8.  Inspect retrieved evidence.
9.  Compare results against baselines.
10. Understand where the system fails.

### Recommended headline metrics

Report at least:

-   Intent macro-F1
-   Intent accuracy
-   Reply groundedness
-   Reply relevance
-   Reply actionability
-   Human/LLM-judge agreement
-   Unsafe auto-handle rate
-   Escalation precision
-   Coverage / auto-handle rate

A strong headline should combine **quality and coverage**, for example:

> "On our 200-example golden set, SupportPilot produced acceptable
> grounded replies on 84% of cases while auto-handling 62%; unsafe
> auto-handles occurred on 3% of cases."

Do not report a single accuracy number without explaining what it hides.

------------------------------------------------------------------------

# 7. Product Principles

## P1 --- Evidence before eloquence

A fluent answer without supporting evidence is worse than a short
escalation.

## P2 --- Abstention is a feature

The agent should be allowed to say:

> "I don't have enough evidence to safely answer this."

and escalate.

## P3 --- Brand behavior beats generic advice

The reply should reflect historical brand behavior rather than generic
customer-service language.

## P4 --- Evaluation is part of the product

The evaluation harness should be treated as a first-class component.

## P5 --- Every decision must be inspectable

For every prediction, retain:

-   input message;
-   predicted intent;
-   confidence;
-   retrieved examples;
-   evidence score;
-   generated reply;
-   action;
-   escalation reason;
-   evaluation scores.

------------------------------------------------------------------------

# 8. User Stories

## Customer

**As a customer**, I want the brand to understand my issue and receive a
useful response quickly.

## Support Agent

**As a support agent**, I want AI to handle repetitive low-risk
questions while routing uncertain or sensitive cases to me.

## Support Manager

**As a support manager**, I want evidence that automated replies are
accurate enough to trust.

## Engineering Reviewer

**As an evaluator**, I want to reproduce the reported results and
inspect failures.

------------------------------------------------------------------------

# 9. End-to-End System

``` text
                    ┌──────────────────────┐
                    │ Raw Twitter Dataset  │
                    └──────────┬───────────┘
                               │
                               ▼
                    ┌──────────────────────┐
                    │ Cleaning & Threading  │
                    └──────────┬───────────┘
                               │
                               ▼
                    ┌──────────────────────┐
                    │ Brand Selection      │
                    │ + Conversation DB    │
                    └──────────┬───────────┘
                               │
                 ┌─────────────┴─────────────┐
                 ▼                           ▼
       ┌──────────────────┐        ┌──────────────────┐
       │ Intent Discovery │        │ Resolution       │
       │ / Taxonomy       │        │ Extraction       │
       └────────┬─────────┘        └────────┬─────────┘
                │                           │
                └────────────┬──────────────┘
                             ▼
                  ┌──────────────────────┐
                  │ Historical Case Index│
                  │ BM25 + Embeddings   │
                  └──────────┬───────────┘
                             │
Incoming message ────────────┤
                             ▼
                  ┌──────────────────────┐
                  │ Intent Classifier    │
                  └──────────┬───────────┘
                             │
                             ▼
                  ┌──────────────────────┐
                  │ Similar Case Retrieval│
                  └──────────┬───────────┘
                             │
                             ▼
                  ┌──────────────────────┐
                  │ Grounded Reply Draft │
                  └──────────┬───────────┘
                             │
                             ▼
                  ┌──────────────────────┐
                  │ Safety / Confidence  │
                  │ + Routing Policy     │
                  └──────────┬───────────┘
                             │
                    ┌────────┴─────────┐
                    ▼                  ▼
               AUTO-HANDLE          ESCALATE
```

------------------------------------------------------------------------

# 10. Data Strategy

## 10.1 Dataset

Use the Customer Support on Twitter dataset as the primary source.

The dataset contains multi-turn interactions between customers and
brands.

Do not treat individual tweets as independent examples if the
surrounding conversation provides useful context.

------------------------------------------------------------------------

# 11. Brand Selection

Do not choose the brand arbitrarily.

Create a small profiling script that calculates, for each brand:

-   number of conversations;
-   number of customer messages;
-   number of brand replies;
-   median conversation length;
-   percentage of conversations with an apparent resolution;
-   number of distinct interaction patterns;
-   language consistency;
-   duplicate/near-duplicate rate.

Select a brand using an explicit scoring function.

Example:

``` text
brand_score =
    0.30 * normalized_conversation_count
  + 0.25 * normalized_resolved_conversation_rate
  + 0.20 * normalized_message_quality
  + 0.15 * normalized_intent_diversity
  + 0.10 * normalized_thread_completeness
```

Do not optimize only for dataset size.

A smaller but coherent brand may produce a better evaluation.

Document the chosen brand and why.

------------------------------------------------------------------------

# 12. Conversation Reconstruction

Raw tweets should be converted into conversation-level records.

Recommended structure:

``` json
{
  "conversation_id": "...",
  "brand": "...",
  "customer_messages": [
    "...",
    "..."
  ],
  "brand_messages": [
    "...",
    "..."
  ],
  "turns": [
    {
      "speaker": "customer",
      "text": "..."
    },
    {
      "speaker": "brand",
      "text": "..."
    }
  ],
  "resolution": "...",
  "metadata": {}
}
```

## Cleaning

Perform:

-   URL normalization;
-   mention normalization;
-   whitespace cleanup;
-   duplicate detection;
-   obvious bot/spam filtering;
-   empty-message filtering;
-   malformed row handling.

Do not over-clean the text because realistic noise is part of the
problem.

------------------------------------------------------------------------

# 13. Leakage Prevention

This is a critical requirement.

The same conversation must never appear in both training/retrieval data
and the golden evaluation set.

Preferred split:

``` text
Raw conversations
       │
       ├── Development / Retrieval corpus
       │
       ├── Validation / threshold tuning
       │
       └── Golden evaluation set
```

If multiple messages from the same conversation exist, keep the entire
conversation in one split.

Where possible, use time-aware splitting:

``` text
Earlier conversations → retrieval/development
Later conversations   → evaluation
```

This better simulates future customer requests.

------------------------------------------------------------------------

# 14. Intent Taxonomy

## 14.1 Principle

Do not use a generic taxonomy such as Banking77 unchanged.

The assignment explicitly asks for intents defined from the selected
brand's data.

Start with exploratory clustering and manually consolidate the most
common patterns.

Target:

**8--15 intents**

Too few: - loses meaningful distinctions.

Too many: - creates sparse classes and poor evaluation reliability.

## 14.2 Example taxonomy

The actual taxonomy must be derived from the chosen brand, but it may
resemble:

1.  Delivery / Shipping Status
2.  Delayed Delivery
3.  Refund Request
4.  Payment Problem
5.  Account Access
6.  Cancellation
7.  Product/Service Problem
8.  Pricing / Charges
9.  Availability
10. General Information
11. Complaint
12. Positive Feedback
13. Unknown / Other

Each intent must have:

-   name;
-   definition;
-   positive examples;
-   negative examples;
-   boundary cases.

------------------------------------------------------------------------

# 15. Intent Classification

Implement a classifier using one of:

### Option A --- LLM classification

Prompt the LLM with the taxonomy and require structured JSON.

### Option B --- Embedding classifier

Use embeddings and nearest-centroid / nearest-example classification.

### Option C --- Hybrid

Recommended:

1.  embedding retrieval identifies candidate intents;
2.  LLM resolves ambiguous cases.

The project should favor simplicity unless a hybrid approach
demonstrates measurable gains.

------------------------------------------------------------------------

# 16. Intent Confidence

Confidence should not simply be the raw LLM's self-reported probability.

Construct a confidence signal from measurable evidence.

Example:

``` text
intent_confidence =
    0.50 * classifier_confidence
  + 0.30 * top_intent_margin
  + 0.20 * retrieval_consistency
```

Where:

-   classifier confidence = model score;
-   top_intent_margin = difference between top-1 and top-2 intent
    scores;
-   retrieval_consistency = fraction of top-k historical cases belonging
    to the predicted intent.

Calibrate thresholds on a validation set.

------------------------------------------------------------------------

# 17. Historical Resolution Extraction

The most important dataset transformation is converting conversations
into reusable historical cases.

For each resolved conversation, derive:

``` json
{
  "case_id": "...",
  "customer_problem": "...",
  "resolution": "...",
  "brand_response": "...",
  "intent": "...",
  "resolution_type": "...",
  "source_conversation_id": "..."
}
```

Resolution type examples:

-   asked customer to DM;
-   provided tracking information;
-   apologized and explained;
-   directed to help center;
-   requested additional details;
-   confirmed cancellation;
-   explained policy;
-   escalated internally.

If resolution is unclear, exclude the conversation from the retrieval
corpus.

This prevents weak historical data from becoming "evidence."

------------------------------------------------------------------------

# 18. Retrieval System

Use retrieval rather than relying on LLM memory.

## Recommended MVP

Use two retrieval methods:

### Sparse retrieval

BM25 over normalized customer-problem text.

### Dense retrieval

Sentence-transformer embeddings over the same text.

### Hybrid score

``` text
retrieval_score =
    0.45 * normalized_bm25
  + 0.55 * normalized_embedding_similarity
```

Retrieve top 5--8 cases.

Then optionally rerank using an LLM or cross-encoder.

------------------------------------------------------------------------

# 19. Retrieval Quality

Evaluate retrieval independently.

For golden examples, measure:

-   Recall@1
-   Recall@3
-   Recall@5
-   MRR
-   intent consistency among top-k
-   whether a useful resolution appears in top-k

This is important because poor retrieval will make a good generator look
bad.

------------------------------------------------------------------------

# 20. Grounded Reply Generation

The generator receives:

``` text
CUSTOMER MESSAGE

PREDICTED INTENT

HISTORICAL CASES
1. Customer problem
   Historical response
   Resolution type

2. ...

INSTRUCTIONS
- Use only supported facts.
- Match the brand's historical support behavior.
- Do not invent policies.
- Do not invent refund amounts, dates, eligibility, or commitments.
- If evidence is insufficient, explicitly recommend escalation.
- Keep the reply concise.
```

Output:

``` json
{
  "reply": "...",
  "supporting_case_ids": ["..."],
  "grounded_claims": ["..."]
}
```

------------------------------------------------------------------------

# 21. Reply Quality Rubric

Score every reply on 1--5 for:

## 21.1 Relevance

Does it directly address the customer's issue?

## 21.2 Groundedness

Are claims supported by retrieved historical evidence?

## 21.3 Actionability

Does the customer know what to do next?

## 21.4 Brand consistency

Does the response resemble the brand's historical support style?

## 21.5 Safety

Does it avoid unsupported promises or risky claims?

## 21.6 Concision

Does it avoid unnecessary verbosity?

Recommended overall score:

``` text
reply_score =
    0.25 relevance
  + 0.25 groundedness
  + 0.20 actionability
  + 0.15 brand_consistency
  + 0.10 safety
  + 0.05 concision
```

Safety should additionally act as a hard constraint.

A reply containing a dangerous unsupported claim should fail regardless
of fluency.

------------------------------------------------------------------------

# 22. Auto-Handle vs Escalate

This is a core product feature.

## Auto-handle when

All or most of the following are true:

-   intent confidence ≥ threshold;
-   retrieval quality ≥ threshold;
-   at least one strong historical match exists;
-   evidence supports the proposed response;
-   no high-risk intent;
-   no unresolved ambiguity;
-   generated response passes safety checks.

## Escalate when

Examples:

-   low intent confidence;
-   conflicting historical resolutions;
-   no strong retrieval match;
-   sensitive/account-specific request;
-   financial commitment;
-   legal/safety issue;
-   angry or highly escalated customer;
-   request requires information unavailable in the dataset;
-   reply contains unsupported claims.

------------------------------------------------------------------------

# 23. Risk Tiering

Assign each intent a risk level:

  -----------------------------------------------------------------------
  Risk                    Examples                Default
  ----------------------- ----------------------- -----------------------
  Low                     General information,    Auto-handle
                          basic status            

  Medium                  Cancellation, delivery  Conditional
                          issue                   

  High                    Refund, payment         Escalate unless
                          dispute,                evidence is
                          account/security        exceptionally strong

  Critical                Legal/safety threats,   Escalate
                          sensitive personal data 
  -----------------------------------------------------------------------

The exact mapping must be based on the selected brand and dataset.

------------------------------------------------------------------------

# 24. Routing Score

A practical routing score:

``` text
automation_score =
    0.35 * intent_confidence
  + 0.35 * retrieval_confidence
  + 0.20 * response_groundedness
  + 0.10 * safety_score
```

Then:

``` text
if high_risk:
    escalate

elif automation_score >= AUTO_THRESHOLD:
    auto_handle

else:
    escalate
```

Tune `AUTO_THRESHOLD` using validation data.

Do not tune it directly on the golden test set.

------------------------------------------------------------------------

# 25. Escalation Reason Taxonomy

Use a fixed set of reasons.

Examples:

-   `LOW_INTENT_CONFIDENCE`
-   `WEAK_RETRIEVAL_EVIDENCE`
-   `CONFLICTING_HISTORICAL_RESOLUTIONS`
-   `HIGH_RISK_INTENT`
-   `INSUFFICIENT_CUSTOMER_CONTEXT`
-   `UNSUPPORTED_REQUEST`
-   `UNSUPPORTED_GENERATED_CLAIM`
-   `SAFETY_CONCERN`

This makes routing measurable.

------------------------------------------------------------------------

# 26. Golden Evaluation Set

Create:

**150--250 hand-labelled examples**

Recommended target:

**200 examples**

## Sampling

Use stratified sampling across:

-   intents;
-   conversation length;
-   common vs rare intents;
-   high/low retrieval similarity;
-   easy/hard examples;
-   positive/negative sentiment;
-   ambiguous cases.

Do not randomly sample 200 tweets and call it a golden set.

------------------------------------------------------------------------

# 27. Golden Set Schema

Recommended CSV/JSONL:

``` json
{
  "example_id": "gold_001",
  "conversation_id": "...",
  "customer_message": "...",
  "context": "...",
  "gold_intent": "refund_request",
  "gold_action": "escalate",
  "gold_reason": "financial_request",
  "gold_resolution_summary": "...",
  "difficulty": "hard",
  "annotator_notes": "..."
}
```

For reply evaluation, optionally include:

``` json
{
  "acceptable_response_characteristics": [
    "acknowledge issue",
    "avoid promising refund",
    "request order details or route to human"
  ]
}
```

------------------------------------------------------------------------

# 28. Human Labelling Process

Use a written annotation guide.

For each example:

1.  Read the complete available conversation context.
2.  Select exactly one intent.
3.  Select expected action:
    -   auto-handle
    -   escalate
4.  Provide a short rationale.
5.  Mark difficulty:
    -   easy
    -   medium
    -   hard

For a subset of 30--50 examples, use a second human annotation pass.

Report:

-   annotator agreement;
-   disagreement categories;
-   taxonomy changes caused by disagreements.

This strengthens the credibility of the golden set.

------------------------------------------------------------------------

# 29. Baselines

At least two baselines are required.

## Baseline 1 --- Trivial

### Majority intent + canned response

-   predict the most frequent intent;
-   return a generic support message;
-   always escalate.

This establishes a lower bound.

## Baseline 2 --- Simple

### TF-IDF / BM25 nearest historical example

-   retrieve the closest historical customer message;
-   return the associated historical brand response;
-   infer intent from the nearest example.

This tests whether a relatively simple retrieval system already solves
the problem.

## Optional Baseline 3

### LLM without retrieval

Ask the LLM to classify and answer using only the customer message.

This is highly valuable because it demonstrates the benefit of
grounding.

------------------------------------------------------------------------

# 30. Evaluation Matrix

Compare:

  -----------------------------------------------------------------------------------
  System            Intent F1        Reply   Groundedness   Auto-Handle        Unsafe
                                   Quality                     Coverage   Auto-Handle
  -------------- ------------ ------------ -------------- ------------- -------------
  Majority +                                                            
  canned                                                                

  BM25 nearest                                                          
  case                                                                  

  LLM no                                                                
  retrieval                                                             

  SupportPilot                                                          
  -----------------------------------------------------------------------------------

Do not cherry-pick metrics.

------------------------------------------------------------------------

# 31. LLM-as-Judge

Use an LLM judge for scalable reply evaluation.

The judge receives:

-   customer message;
-   historical evidence;
-   generated reply;
-   expected intent/action where appropriate.

It outputs structured scores.

Example:

``` json
{
  "relevance": 4,
  "groundedness": 5,
  "actionability": 4,
  "brand_consistency": 4,
  "safety": 5,
  "overall": 4,
  "reason": "..."
}
```

Use a deterministic rubric.

------------------------------------------------------------------------

# 32. Judge Calibration Against Humans

This is mandatory.

Take approximately:

**40--60 examples**

Have humans rate the replies using the same rubric.

Then compare:

-   exact agreement;
-   ±1 score agreement;
-   Pearson/Spearman correlation where appropriate;
-   pass/fail agreement for "acceptable reply."

Report something like:

``` text
LLM judge vs human:
- exact agreement: 72%
- within-one agreement: 93%
- acceptable/not acceptable agreement: 88%
```

Do not present the judge's scores as ground truth without calibration.

------------------------------------------------------------------------

# 33. Headline Metrics

Recommended final metrics:

## Intent

-   Accuracy
-   Macro-F1
-   Per-intent F1

Macro-F1 is preferred because it prevents common intents from
dominating.

## Retrieval

-   Recall@3
-   Recall@5
-   MRR

## Reply

-   Average human score
-   Average LLM-judge score
-   Groundedness pass rate
-   Safety pass rate

## Routing

-   Auto-handle coverage
-   Auto-handle precision
-   Unsafe auto-handle rate
-   Escalation recall for high-risk/uncertain cases

------------------------------------------------------------------------

# 34. The Most Important Routing Metric

Define:

``` text
Unsafe Auto-Handle Rate =
incorrect_or_unsafe_auto_handled_cases
/
all_auto_handled_cases
```

This is more meaningful than raw automation coverage.

A system that auto-handles 95% of cases but gives unsafe answers is not
production-worthy.

------------------------------------------------------------------------

# 35. Coverage vs Quality Curve

Instead of reporting one automation threshold, evaluate multiple
thresholds.

Example:

  -----------------------------------------------------------------------
          Threshold       Auto-Handle             Reply            Unsafe
                             Coverage     Acceptability       Auto-Handle
  ----------------- ----------------- ----------------- -----------------
               0.50               82%               79%                8%

               0.60               74%               83%                5%

               0.70               65%               88%                3%

               0.80               52%               92%                1%

               0.90               31%               96%                0%
  -----------------------------------------------------------------------

This demonstrates that the system can trade automation for safety.

------------------------------------------------------------------------

# 36. Mandatory Section: "What Is Misleading About My Headline Number?"

Include this section in the final report.

Discuss at least:

### Dataset bias

Twitter users are not representative of all support customers.

### Historical-response bias

The system learns how the brand responded historically, including
potentially inconsistent behavior.

### Golden-set size

200 examples provide useful evidence but cannot establish
production-level reliability.

### Label ambiguity

Some customer requests naturally belong to multiple intents.

### LLM judge bias

The judge is not a perfect human substitute.

### Retrieval leakage risk

Explain exactly how conversation-level splitting prevented leakage.

### Automation coverage

High quality at low coverage may look better than it is.

### Brand selection bias

The chosen brand may be unusually easy or difficult.

The goal is to demonstrate intellectual honesty.

------------------------------------------------------------------------

# 37. Failure Analysis

Identify the top five failure modes using actual examples from the
golden set.

Recommended template:

## Failure 1 --- Ambiguous Intent

**Example:**\
Customer message...

**Expected:**\
Refund request

**Predicted:**\
Delivery issue

**Why it happened:**\
Both intents share language around missing orders and money.

**Hypothesis:**\
Classifier relies too heavily on lexical overlap.

**Potential fix:**\
Add boundary examples and context-aware classification.

Repeat for five failures.

Possible categories:

1.  ambiguous intent;
2.  weak retrieval;
3.  contradictory historical responses;
4.  hallucinated policy;
5.  inappropriate auto-handle.

------------------------------------------------------------------------

# 38. Observability

Every prediction should generate a trace.

Example:

``` json
{
  "request_id": "...",
  "intent": {
    "label": "refund_request",
    "confidence": 0.87
  },
  "retrieval": {
    "top_k": 5,
    "best_score": 0.91,
    "case_ids": ["c1", "c2", "c3"]
  },
  "generation": {
    "model": "...",
    "temperature": 0
  },
  "routing": {
    "decision": "escalate",
    "score": 0.62,
    "reason": "HIGH_RISK_INTENT"
  }
}
```

This makes debugging and live explanation easy.

------------------------------------------------------------------------

# 39. Recommended Repository Structure

``` text
supportpilot/
│
├── README.md
├── PRD.md
├── requirements.txt
├── .env.example
├── Makefile
│
├── configs/
│   ├── brand.yaml
│   ├── intents.yaml
│   └── thresholds.yaml
│
├── data/
│   ├── raw/
│   ├── interim/
│   ├── processed/
│   └── golden/
│
├── src/
│   ├── data/
│   │   ├── loader.py
│   │   ├── cleaner.py
│   │   ├── threading.py
│   │   └── splitter.py
│   │
│   ├── taxonomy/
│   │   ├── discover.py
│   │   └── classifier.py
│   │
│   ├── retrieval/
│   │   ├── bm25.py
│   │   ├── embeddings.py
│   │   └── hybrid.py
│   │
│   ├── generation/
│   │   ├── prompts.py
│   │   └── generator.py
│   │
│   ├── routing/
│   │   ├── risk.py
│   │   └── policy.py
│   │
│   ├── evaluation/
│   │   ├── metrics.py
│   │   ├── baselines.py
│   │   ├── judge.py
│   │   └── calibration.py
│   │
│   └── pipeline.py
│
├── scripts/
│   ├── profile_dataset.py
│   ├── build_corpus.py
│   ├── build_index.py
│   ├── run_agent.py
│   └── evaluate.py
│
├── notebooks/
│   ├── 01_dataset_exploration.ipynb
│   └── 02_failure_analysis.ipynb
│
├── tests/
│   ├── test_cleaning.py
│   ├── test_threading.py
│   ├── test_retrieval.py
│   └── test_routing.py
│
└── reports/
    ├── results.json
    ├── failure_cases.json
    └── final_report.md
```

------------------------------------------------------------------------

# 40. CLI Design

The reviewer should be able to run:

``` bash
python -m scripts.profile_dataset
```

Then:

``` bash
python -m scripts.build_corpus
```

Then:

``` bash
python -m scripts.build_index
```

Then:

``` bash
python -m scripts.evaluate
```

Ideally provide a single command:

``` bash
make reproduce
```

which executes the complete evaluation on the documented sample.

------------------------------------------------------------------------

# 41. 15-Minute Reproduction Requirement

The README should clearly specify:

### Environment

-   Python version;
-   dependency installation;
-   environment variables;
-   model/API requirements.

### Data

-   exact dataset source;
-   exact subsample;
-   preprocessing version.

### Command

``` bash
make reproduce
```

### Expected output

Example:

``` text
Loading 8,000 conversations...
Building retrieval index...
Evaluating 200 golden examples...

Intent macro-F1:             0.81
Retrieval Recall@5:          0.86
Reply acceptability:         0.87
Auto-handle coverage:        0.63
Unsafe auto-handle rate:     0.03

Results written to:
reports/results.json
```

Use cached embeddings/indexes if needed to keep reproduction fast.

------------------------------------------------------------------------

# 42. Caching

Cache:

-   cleaned dataset;
-   embeddings;
-   retrieval index;
-   LLM classifications;
-   generated replies;
-   judge evaluations.

Use stable hashes for cache keys.

Example:

``` text
hash(model + prompt + input + evidence)
```

This makes evaluation cheaper and deterministic.

------------------------------------------------------------------------

# 43. Determinism

Use:

-   temperature = 0 where supported;
-   fixed random seeds;
-   deterministic train/test split;
-   versioned configuration;
-   cached LLM outputs.

If the external LLM is inherently nondeterministic, state this
explicitly.

------------------------------------------------------------------------

# 44. Prompt Engineering

Keep prompts version-controlled.

Example generation policy:

``` text
You are a customer-support assistant for BRAND.

Your job is to draft a response using only the historical support evidence provided.

Rules:
1. Do not invent policies.
2. Do not invent prices, refund amounts, timelines, or eligibility.
3. Do not claim an action was completed unless the evidence supports it.
4. If the evidence is insufficient, recommend escalation.
5. Be concise.
6. Match the brand's historical support tone.
7. Do not expose internal reasoning.
```

Version prompts:

``` text
PROMPT_VERSION = "reply_v3"
```

------------------------------------------------------------------------

# 45. Structured Outputs

All model-facing components should return machine-readable outputs.

Example:

``` json
{
  "intent": "delivery_status",
  "confidence": 0.93,
  "reply": "Thanks for reaching out...",
  "action": "auto_handle",
  "reason": "Strong intent match and high-quality historical evidence.",
  "evidence_ids": ["case_102", "case_811"]
}
```

Validate JSON with a schema.

Reject or retry malformed outputs.

------------------------------------------------------------------------

# 46. Guardrails

Implement deterministic checks before auto-handling.

Reject auto-handle if:

-   reply contains unsupported numerical claims;
-   reply contains invented URLs;
-   reply contains refund/credit promises without evidence;
-   reply claims access to internal systems;
-   reply contains sensitive data;
-   no evidence IDs are attached;
-   retrieval score is below threshold;
-   predicted intent is high-risk.

This is intentionally simple and explainable.

------------------------------------------------------------------------

# 47. Data Quality Checks

Before evaluation, run:

-   null-rate report;
-   duplicate-rate report;
-   conversation-length distribution;
-   brand distribution;
-   intent distribution;
-   train/eval overlap check;
-   exact-text leakage check;
-   near-duplicate leakage check.

Fail the pipeline if leakage is detected.

------------------------------------------------------------------------

# 48. Testing Strategy

## Unit Tests

Test:

-   tweet normalization;
-   thread reconstruction;
-   split logic;
-   intent parsing;
-   retrieval ranking;
-   routing thresholds;
-   JSON schema validation.

## Integration Tests

Test:

``` text
message
→ classify
→ retrieve
→ generate
→ route
```

using mocked LLM calls.

## Evaluation Tests

Test that:

-   golden set remains immutable;
-   evaluation does not alter thresholds;
-   retrieval excludes evaluation conversations;
-   metrics are reproducible.

------------------------------------------------------------------------

# 49. Security and Privacy

Although the dataset is public, treat customer conversations as
sensitive.

Do not:

-   add real personal information to logs;
-   send unnecessary customer text to third-party APIs;
-   expose raw conversations in the README;
-   publish secrets/API keys;
-   commit `.env`.

If examples are used in the report, minimize or redact personally
identifying content.

------------------------------------------------------------------------

# 50. Cost Control

Keep LLM usage bounded.

Recommended:

-   use embeddings for bulk retrieval;
-   use LLM only for classification/generation/judging;
-   cache every LLM response;
-   run judge on the golden set rather than the full raw dataset;
-   use a smaller model for routine classification if performance is
    sufficient.

Track approximate evaluation cost in the README.

------------------------------------------------------------------------

# 51. Development Phases

## Phase 1 --- Dataset reconnaissance

Deliver:

-   brand profile;
-   conversation reconstruction;
-   quality statistics;
-   selected brand.

## Phase 2 --- Taxonomy

Deliver:

-   8--15 intents;
-   annotation guide;
-   representative examples.

## Phase 3 --- Retrieval baseline

Deliver:

-   BM25;
-   embeddings;
-   retrieval metrics.

## Phase 4 --- Agent MVP

Deliver:

-   classification;
-   retrieval;
-   grounded response;
-   routing.

## Phase 5 --- Golden evaluation

Deliver:

-   200 labelled examples;
-   annotation guide;
-   human agreement sample.

## Phase 6 --- Evaluation harness

Deliver:

-   baselines;
-   automated metrics;
-   LLM judge;
-   judge calibration.

## Phase 7 --- Failure analysis

Deliver:

-   top five failure modes;
-   real examples;
-   hypotheses;
-   proposed fixes.

## Phase 8 --- Final packaging

Deliver:

-   README;
-   6-page report or equivalent README section;
-   decision log;
-   reproducibility command;
-   clean repository.

------------------------------------------------------------------------

# 52. Suggested One-Week Execution Plan

## Day 1 --- Data

-   download dataset;
-   inspect schema;
-   profile brands;
-   choose brand;
-   reconstruct conversations.

## Day 2 --- Taxonomy + Corpus

-   discover intent clusters;
-   define taxonomy;
-   extract historical resolutions;
-   create leakage-safe split.

## Day 3 --- Retrieval

-   implement BM25;
-   implement embeddings;
-   evaluate Recall@K;
-   build case index.

## Day 4 --- Agent

-   implement classifier;
-   implement grounded generator;
-   implement routing policy;
-   add deterministic guardrails.

## Day 5 --- Golden Set

-   sample 200 examples;
-   label intents/actions;
-   double-label 40--50;
-   resolve disagreements.

## Day 6 --- Evaluation

-   implement baselines;
-   run agent;
-   build LLM judge;
-   calibrate judge against humans.

## Day 7 --- Report

-   analyze failures;
-   produce coverage-quality curve;
-   write misleading-number section;
-   document decisions;
-   finalize README;
-   test 15-minute reproduction.

------------------------------------------------------------------------

# 53. Decision Log

Maintain 10--15 non-obvious decisions.

Recommended entries:

1.  Why this brand was selected.
2.  Why conversation-level splitting was used.
3.  Why 8--15 intents were preferred.
4.  Why some conversations were excluded from retrieval.
5.  Why hybrid retrieval was chosen.
6.  Why retrieval evidence is required for auto-handle.
7.  Why high-risk intents default to escalation.
8.  Why thresholds were tuned on validation data.
9.  Why the golden set was stratified.
10. Why LLM judging was calibrated against humans.
11. Why an LLM-without-retrieval baseline was included.
12. Why the system does not perform real support actions.
13. Why temperature/caching were configured as they were.
14. Why the final headline metric includes coverage/safety.
15. Why certain failure cases were intentionally left unresolved.

------------------------------------------------------------------------

# 54. Recommended Report Structure

Maximum six pages, or equivalent README section.

## 1. Executive Summary

One paragraph.

## 2. Problem Framing

Define "good" for this brand.

## 3. System Design

One architecture diagram.

## 4. Data + Golden Set

Sampling and labeling methodology.

## 5. Results

Baselines + final system.

## 6. Failure Analysis

Top five failures.

## 7. Misleading Headline Number

Mandatory.

## 8. Next Week

What you would build next.

## 9. Decision Log

10--15 bullets.

------------------------------------------------------------------------

# 55. Recommended Architecture Diagram for README

``` text
                    CUSTOMER MESSAGE
                           |
                           v
                  +------------------+
                  | Intent Classifier|
                  +--------+---------+
                           |
                           v
                  +------------------+
                  | Hybrid Retrieval|
                  | BM25 + Embedding|
                  +--------+---------+
                           |
                    top historical
                       resolutions
                           |
                           v
                  +------------------+
                  | Grounded LLM     |
                  | Reply Generator  |
                  +--------+---------+
                           |
                           v
                  +------------------+
                  | Safety + Routing |
                  +--------+---------+
                           |
                 +---------+---------+
                 |                   |
                 v                   v
             AUTO-HANDLE          ESCALATE
```

------------------------------------------------------------------------

# 56. Example End-to-End Prediction

### Input

``` text
Customer:
"My package still hasn't arrived and tracking hasn't changed for 4 days."
```

### Intent

``` text
delayed_delivery
confidence = 0.94
```

### Retrieved evidence

``` text
Case A:
Customer reported package delay.
Brand requested order/tracking information.

Case B:
Customer reported no tracking movement.
Brand asked customer to DM order details.
```

### Draft

``` text
Sorry about the delay. Please send us your order/tracking details via DM so we can look into this for you.
```

### Routing

``` text
AUTO-HANDLE
```

### Reason

``` text
High intent confidence, strong historical matches, and no unsupported commitment.
```

------------------------------------------------------------------------

# 57. Example Unsafe Prediction

### Input

``` text
Customer:
"I want my money back immediately. Your service charged me twice."
```

### Possible classification

``` text
payment_issue / refund_request
```

### Retrieval

Historical evidence is mixed.

### Routing

``` text
ESCALATE
```

### Reason

``` text
Financial request with insufficient evidence to determine refund eligibility.
```

### Reply

``` text
I’m sorry about the duplicate charge. Please send us your order/account details via DM so our support team can review the payment and help you with the next steps.
```

The system should not say:

> "We have refunded you."

unless historical evidence and system capabilities actually support that
action.

------------------------------------------------------------------------

# 58. Recommended Evaluation Output

Produce both human-readable and machine-readable results.

### `reports/results.json`

``` json
{
  "system": {
    "name": "SupportPilot",
    "version": "0.1.0"
  },
  "dataset": {
    "brand": "...",
    "retrieval_cases": 5000,
    "golden_examples": 200
  },
  "intent": {
    "accuracy": 0.84,
    "macro_f1": 0.81
  },
  "retrieval": {
    "recall_at_3": 0.79,
    "recall_at_5": 0.86
  },
  "reply": {
    "acceptability": 0.87,
    "groundedness": 0.91
  },
  "routing": {
    "coverage": 0.63,
    "unsafe_auto_handle_rate": 0.03
  }
}
```

Do not fabricate these numbers before running the system.

------------------------------------------------------------------------

# 59. What a Strong Submission Looks Like

A strong submission does **not** need:

-   the largest model;
-   the most complicated architecture;
-   a huge training pipeline;
-   production infrastructure.

It should instead demonstrate:

### 1. Good problem decomposition

Classification, retrieval, generation, and routing are evaluated
separately.

### 2. Strong data discipline

Leakage prevention and conversation reconstruction are explicit.

### 3. Grounding

Historical evidence is used as the source of truth.

### 4. Safe automation

The agent knows when to escalate.

### 5. Honest evaluation

Baselines, human labels, judge calibration, and failure analysis are
visible.

### 6. Reproducibility

The reviewer can run the headline result quickly.

### 7. Engineering quality

The code is modular, tested, configurable, and easy to inspect.

------------------------------------------------------------------------

# 60. Final Acceptance Checklist

## Dataset

-   [ ] Primary Twitter dataset used.
-   [ ] One brand selected with documented rationale.
-   [ ] Conversations reconstructed.
-   [ ] Data cleaning documented.
-   [ ] Leakage checks implemented.

## Intent

-   [ ] Brand-specific taxonomy created.
-   [ ] 8--15 intents.
-   [ ] Annotation guide created.
-   [ ] Macro-F1 reported.

## Retrieval

-   [ ] Historical resolved cases extracted.
-   [ ] BM25/simple retrieval baseline implemented.
-   [ ] Dense or hybrid retrieval implemented.
-   [ ] Recall@K reported.

## Generation

-   [ ] Reply grounded in historical evidence.
-   [ ] Structured output.
-   [ ] Prompt versioned.
-   [ ] Hallucination/unsupported-claim checks.

## Routing

-   [ ] Auto-handle/escalate decision.
-   [ ] Explicit reason.
-   [ ] Risk tiering.
-   [ ] Threshold tuned on validation set.
-   [ ] Unsafe auto-handle metric.

## Golden Set

-   [ ] 150--250 examples.
-   [ ] Hand-labelled.
-   [ ] Sampling methodology documented.
-   [ ] Double-labelled subset.
-   [ ] Agreement reported.

## Evaluation

-   [ ] Trivial baseline.
-   [ ] Simple baseline.
-   [ ] Optional LLM-without-retrieval baseline.
-   [ ] LLM judge.
-   [ ] Human-vs-judge calibration.
-   [ ] Failure analysis.
-   [ ] Coverage-quality analysis.

## Report

-   [ ] Problem framing.
-   [ ] Results.
-   [ ] Five real failure modes.
-   [ ] "What is misleading about my headline number?"
-   [ ] One-week next steps.
-   [ ] 10--15 decision log entries.

## Reproducibility

-   [ ] README complete.
-   [ ] `.env.example`.
-   [ ] One-command evaluation.
-   [ ] Cached expensive artifacts.
-   [ ] Reproduces headline results in \<15 minutes.
-   [ ] No secrets committed.

------------------------------------------------------------------------

# 61. Recommended Final Positioning

The project should be presented as:

> **An evidence-grounded customer-support agent that learns a brand's
> historical support behavior, retrieves similar resolved cases, drafts
> a constrained response, and abstains when the evidence is
> insufficient.**

The most important claim should not be:

> "Our LLM achieves X% accuracy."

Instead, aim for:

> **"We built a support agent that can automate a meaningful fraction of
> routine requests while measuring---and explicitly controlling---the
> risk of unsafe automation."**

That framing aligns the technical implementation with the assignment's
real evaluation criterion: **whether the system is trustworthy enough to
use.**
