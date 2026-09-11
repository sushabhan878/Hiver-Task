# Intent Taxonomy Discovery (retrieval corpus)

Corpus: 5,613 resolved AmazonHelp cases, labelled by the local
LLM (`qwen2.5:3b`, temperature 0) against the taxonomy in configs/intents.yaml.
The taxonomy itself was derived by manual consolidation of keyword-cluster
inspection of customer messages (see scripts/build_corpus.py::keyword_intent
for the bootstrap rules that seeded the consolidation).

| intent | count | share |
|---|---|---|
| delivery_status | 1101 | 19.6% |
| delayed_delivery | 787 | 14.0% |
| general_info | 701 | 12.5% |
| refund_request | 521 | 9.3% |
| product_issue | 519 | 9.2% |
| service_complaint | 398 | 7.1% |
| account_access | 324 | 5.8% |
| availability_question | 312 | 5.6% |
| pricing_charge | 281 | 5.0% |
| payment_issue | 200 | 3.6% |
| feedback | 193 | 3.4% |
| other | 172 | 3.1% |
| cancellation | 104 | 1.9% |

Rare intents (<60 cases) risk unreliable per-intent metrics; noted in the
report's limitations section (payment_issue, cancellation).