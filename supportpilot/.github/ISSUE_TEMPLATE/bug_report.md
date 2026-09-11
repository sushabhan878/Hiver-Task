name: Bug report
description: Something is broken or behaves incorrectly
title: "[bug]: "
labels: [bug]
body:
  - type: markdown
    attributes:
      value: |
        Thanks for taking the time to file a bug report. Before you submit,
        please search existing issues to avoid duplicates.

  - type: textarea
    id: what-happened
    attributes:
      label: What happened?
      description: A clear description of the bug. Include the full traceback if there is one (redact personal data).
      placeholder: |
        Ran `python -m scripts.run_agent --message "..."` and expected X, but got Y.
    validations:
      required: true

  - type: textarea
    id: reproduce
    attributes:
      label: Steps to reproduce
      description: Minimal commands to reproduce the behavior from a fresh clone.
      placeholder: |
        1. `pip install -r requirements.txt`
        2. `make tests`
        3. ...
    validations:
      required: true

  - type: textarea
    id: expected
    attributes:
      label: Expected behavior
      description: What did you expect to happen instead?
    validations:
      required: true

  - type: dropdown
    id: component
    attributes:
      label: Component
      options:
        - data pipeline (src/data, scripts)
        - taxonomy / intent (src/taxonomy)
        - retrieval (src/retrieval)
        - generation (src/generation)
        - routing / guardrails (src/routing)
        - evaluation / judge (src/evaluation)
        - llm client (src/llm)
        - build / CI / tooling
        - other
    validations:
      required: true

  - type: textarea
    id: environment
    attributes:
      label: Environment
      description: OS, Python version, Ollama version, models pulled.
      placeholder: "Windows 11, Python 3.14.2, Ollama 0.x, qwen2.5:3b + nomic-embed-text"
    validations:
      required: true

  - type: checkboxes
    id: checks
    attributes:
      label: Preflight checks
      options:
        - label: I searched existing issues and found no duplicate.
          required: true
        - label: "`make check` and `make tests` pass on my machine (or I described the failure above)."
          required: false
