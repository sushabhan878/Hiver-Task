# SupportPilot — Production AI Support Agent for AmazonHelp
**Hiver SDE Intern Take-Home Assignment Submission**

[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/)
[![Local Ollama](https://img.shields.io/badge/llm-Ollama%20(qwen2.5:3b)-orange.svg)](https://ollama.com)
[![Reproduction Time](https://img.shields.io/badge/reproduce-%3C%2015%20min-green.svg)](supportpilot/README.md)
[![License: MIT](https://img.shields.io/badge/license-MIT-purple.svg)](supportpilot/LICENSE)

> An evidence-grounded, risk-tiered customer support agent built on the Twitter Customer Support dataset for **AmazonHelp**. Designed and evaluated for **trustworthy abstention and brand safety**, not reckless automation.

---

## 📄 Submission Report

The full, publication-grade assignment report is available directly in this repository:
👉 **[Read the Full Report (REPORT.md)](REPORT.md)**

It covers:
1. **Problem Framing**: What "good" means for `@AmazonHelp` and what was intentionally not built.
2. **Benchmark vs 3 Baselines**: Trivial (Majority), Simple (BM25 nearest copy), and LLM Zero-Shot without retrieval.
3. **Evaluation Harness & Golden Set**: 199 hand-labelled examples with stratified sampling, 92.5% inter-annotator agreement (Cohen's $\kappa = 0.916$).
4. **LLM-as-Judge Calibration**: Empirical demonstration of why local 3B judges fail human calibration ($r = 0.08$) and how we verified safety via human audits.
5. **Top 5 Failure Modes**: Real examples, error analysis, and actionable hypotheses.
6. **"What Is Misleading About My Headline Number?"**: Mandatory transparency critique.
7. **Next Week Priorities**: High-leverage roadmap for conversation tracking, churn detection, and multi-turn state.
8. **Decision Log**: 15 non-obvious engineering decisions and their architectural rationale.

---

## ⚡ Quick Benchmark Summary

Tested on the **199 hand-labelled golden test set**:

| Metric | SupportPilot (Agent) | Baseline 1 (Majority) | Baseline 2 (BM25 Copy) | Baseline 3 (LLM Zero-Shot) |
|---|:---:|:---:|:---:|:---:|
| **Intent Accuracy** | **52.8%** | 16.6% | 28.1% | 50.8% |
| **Intent Macro-F1** | **0.506** | 0.022 | 0.239 | 0.502 |
| **Escalation Recall** | **93.2%** | 100.0% | 1.1% | 0.0% |
| **Escalation Precision** | **89.2%** | 44.2% | 100.0% | 0.0% |
| **Auto-Handle Coverage** | **11.6%** | 0.0% | 99.0% | 100.0% |
| **Human Unsafe Auto-Handle Rate** | **30.0%** | N/A | **100.0%** | **99.5%** |
| **Fabricated $ / Claim Violations** | **0%** | 0% | 42.0% | 31.5% |

---

## 🚀 Reproducing Headline Results (< 15 Minutes)

The entire pipeline runs **100% locally** using Ollama (no cloud API keys required). All intermediate embeddings and LLM generations are cryptographically hashed and cached on disk (`sha1(model + prompt)`), enabling warm re-evaluations in **under 30 seconds**.

### 1. Prerequisites
- Python 3.11+
- [Ollama](https://ollama.com/) running locally:
  ```bash
  ollama pull qwen2.5:3b
  ollama pull nomic-embed-text
  ```

### 2. Run Reproduction
```bash
# Clone the repository
git clone https://github.com/sushabhan878/Hiver-Task.git
cd Hiver-Task/supportpilot

# Install dependencies
pip install -r requirements.txt

# Run the complete reproduction pipeline
make reproduce
```

### 3. Run Unit and Integration Tests
```bash
pytest
```
*Runs 38 unit and pipeline integration tests.*

---

## 📂 Repository Layout

```
.
├── REPORT.md                         # 📄 Complete assignment report (all required sections)
├── README.md                         # 🧭 Project overview and quickstart guide
├── hiver_sde_support_agent_prd.md    # 📋 Hiver take-home PRD and assignment guidelines
└── supportpilot/                     # 💻 Core application source package
    ├── Makefile                      # make reproduce, make test, make evaluate
    ├── pyproject.toml                # Project metadata and tool configuration
    ├── requirements.txt              # Production dependencies
    ├── configs/
    │   ├── config.yaml               # Model parameters, retrieval weights, thresholds
    │   ├── intents.yaml              # 13-intent taxonomy definitions and risk tiers
    │   └── thresholds.yaml           # Validation-tuned gating cutoffs
    ├── data/
    │   ├── golden/                   # 199 hand-labelled examples + double annotation sheets
    │   └── processed/                # Split conversation sets and labelled retrieval cases
    ├── src/
    │   ├── pipeline.py               # End-to-end trace-emitting agent
    │   ├── taxonomy/                 # Intent classifier (kNN + LLM fallback)
    │   ├── retrieval/                # BM25 + dense embedding hybrid search
    │   ├── generation/               # Grounded reply generator & output cleaners
    │   ├── routing/                  # Risk tiers, deterministic guardrails & policies
    │   └── evaluation/               # Metric computation, baselines, and judge harness
    ├── scripts/                      # Standalone CLI tools for profiling, sampling, and evaluation
    ├── tests/                        # 38 pytest unit and integration tests
    └── reports/                      # Machine-readable JSON metrics and failure case logs
```

---

## 📬 Contact & Submission

- **Candidate**: SDE Intern Candidate
- **Reviewer**: Anurag (`anurag@hiverhq.com`)
- **Repo URL**: [https://github.com/sushabhan878/Hiver-Task](https://github.com/sushabhan878/Hiver-Task)
