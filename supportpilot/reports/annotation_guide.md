# Golden Set Annotation Guide (AmazonHelp)

This guide governs all human labelling for the golden evaluation set. It was
applied for (a) the first full annotation pass (199 examples, draft-assisted),
(b) the second independent pass over a 40-example stratified subset, and
(c) the 50-example human rubric-rating pass used to calibrate the LLM judge.

## Labelling an example

1. **Read the complete conversation context** (all customer messages; the
   first brand reply is used only as resolution evidence, never to change
   the customer-side intent).
2. **Select exactly one intent** using the taxonomy definitions below.
   Boundary rules resolve conflicts.
3. **Select the expected action**: `auto_handle` (a safe, grounded,
   non-committal reply is possible) or `escalate` (a human should look).
4. **Provide a short rationale** (stored in `annotator_notes`).
5. **Mark difficulty**: `easy` / `medium` / `hard` (see rules).

## Intent decision rules (in order)

Apply the first rule that matches:

1. **Safety/legal signals** (`lawyer`, `sue`, `legal`, `court`, `attorney`,
   fraud accusations): intent = whatever the surface topic is, but action is
   **always escalate**.
2. **Financial ask** (refund, money back, wrong/extra charge, credit):
   intent = `refund_request` for money-back asks, `payment_issue` for
   charge/billing problems; action = **always escalate**.
3. **Account/security** (login, password, locked, hacked, account changes):
   intent = `account_access`; action = **always escalate**.
4. **Explicit cancel request** (order, Prime, subscription): intent =
   `cancellation`. If a refund is also requested, rule 2 wins.
5. **"Marked delivered but not received"** or any delivered-state dispute:
   intent = `delivery_status`; action = **escalate** (requires investigation;
   a tracking-check reply is insufficient).
6. **Delay complaint** (late, stuck, past promised date): intent =
   `delayed_delivery`. Neutral "where is it" without a missed-date grievance:
   intent = `delivery_status`.
7. **Damaged/defective/wrong/missing item**: intent = `product_issue`
   (even when a return/refund is implied, unless money-back is the explicit
   ask, in which case rule 2 wins).
8. **Vague dissatisfaction with no concrete transactional ask**: intent =
   `service_complaint`.
9. **Price questions/disputes without a charge problem**: intent =
   `pricing_charge`.
10. **Stock/availability questions**: intent = `availability_question`.
11. **General policy/how-to questions with no transactional ask**: intent =
    `general_info`.
12. **Praise/thanks with no request**: intent = `feedback`.
13. **Non-English**: assign the intent by translating the message; the
    taxonomy applies across languages. Non-English does NOT automatically
    mean `other`.
14. **Spam, marketing chatter, promos, cryptic content with no support
    request**: intent = `other`; action = **escalate** (auto-handling noise
    is not useful).

## Action rules

- **escalate** always for: safety/legal, financial, account/security,
  delivered-not-received disputes, `other` (ambiguity), angry customers
  (`unacceptable`, `worst`, `furious`, `never again`, `ridiculous`,
  `disgusted`), repeated unresolved failures, seller disputes.
- **auto_handle** when: the intent is low/medium risk AND the brand's
  standard historical reply (tracking-check, policy explanation, help link,
  availability info, feedback thanks) fully addresses the message.

## Difficulty rules

- `hard`: financial/account disputes, repeated failures, sarcasm, mixed
  intents, cancellation+refund combos, delivered-state disputes.
- `medium`: multi-turn context needed, tone ambiguity, non-English without
  explicit keywords.
- `easy`: single clear ask matching one intent with obvious policy answer.

## Second-pass disagreements and taxonomy impact

From the 40-example double-annotated subset (reports/annotator_agreement.json):

- Intent agreement 92.5% (Cohen's kappa 0.916); action agreement 92.5%.
- Disagreements were concentrated at: service_complaint vs
  delivery_status/delayed_delivery tone boundaries; general_info vs
  feedback for promos; escalate threshold for repeated-failure delivery
  complaints; general_info vs delayed_delivery for prime-benefit questions.
- Taxonomy note: `feedback` and `general_info` overlap for brand-chatter;
  we kept both but documented that promo chatter with a question defaults
  to `general_info`, pure praise to `feedback`.

## Judge rubric (for the 50-example human rating pass)

Identical dimensions and anchors as the LLM judge (see
`src/generation/prompts.py`, judge_v2), scored 1-5 per dimension, then
weighted (relevance .25, groundedness .25, actionability .20,
brand_consistency .15, safety .10, concision .05). Replies were rated blind:
the judge's outputs were hidden during rating.
