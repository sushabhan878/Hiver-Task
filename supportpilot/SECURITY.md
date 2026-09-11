# Security Policy

## Supported Versions

SupportPilot is a research/evaluation project. Security fixes target the
latest release on `main`.

| Version | Supported |
|---------|-----------|
| main    | yes       |
| older   | no        |

## Reporting a Vulnerability

**Do not open a public GitHub issue for security vulnerabilities.**

Please report privately via [GitHub Security Advisories](https://docs.github.com/en/code-security/security-advisories/guidance-on-reporting-and-reviewing/privately-reporting-a-security-vulnerability)
using the *"Report a vulnerability"* button on the Security tab of the
repository. Include:

1. Steps to reproduce (or a proof of concept).
2. Affected component (`src/data`, `src/retrieval`, `src/generation`,
   `src/routing`, `src/evaluation`, `src/llm`, scripts, CI).
3. Potential impact and your assessment of severity.
4. Any suggested mitigation.

You should receive an acknowledgment within 72 hours. Please do not
publicly disclose the issue until a fix is released. We credit reporters in
release notes when desired.

## Security expectations and design boundaries

This project is designed to run **fully locally** (Ollama) with **no API
keys and no secrets**. Keep it that way:

- Do not commit API keys, tokens, `.env` files, or credentials.
  `.env` is gitignored; use `.env.example` as the template.
- Conversation data is treated as sensitive even though the dataset is
  public: no raw conversation text or personal data in logs or reports —
  use the existing redaction/masking utilities before writing artifacts.
- All LLM and embedding calls go through the local Ollama client
  (`src/llm/client.py`) with disk caching. Do not add outbound network
  calls to new endpoints without a maintainer discussion.
- Generated replies are passed through the deterministic guardrails
  (`src/routing/guardrails.py`) before any auto-handle decision. Do not
  bypass guardrails for convenience; widen them only with evidence and a
  routing safety regression check.

## Scope

In scope:

- Any component in this repository that runs on a contributor's or
  reviewer's machine (data pipeline, scripts, tests, CI).
- Prompt-injection-resistant generation and guardrail bypasses in the
  routing policy that could cause unsafe auto-handled replies.

Out of scope:

- Vulnerabilities in Ollama or third-party models themselves (report to
  the upstream projects).
- Theoretical attacks requiring access to already-compromised machines.
- Social engineering of maintainers.
