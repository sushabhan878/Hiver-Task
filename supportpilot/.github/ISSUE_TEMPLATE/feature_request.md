name: Feature request
description: Suggest a new capability or improvement
title: "[feat]: "
labels: [enhancement]
body:
  - type: markdown
    attributes:
      value: |
        Thanks for the suggestion. This project is evaluation-first:
        features that improve trustworthiness, measurability, or
        reproducibility are prioritized over raw capability.

  - type: textarea
    id: problem
    attributes:
      label: Problem to solve
      description: What is hard or impossible today? Who is affected?
    validations:
      required: true

  - type: textarea
    id: solution
    attributes:
      label: Proposed solution
      description: What should exist instead? Sketch the API/command/behavior if you can.
    validations:
      required: true

  - type: textarea
    id: alternatives
    attributes:
      label: Alternatives considered
      description: Other approaches, including "do nothing".

  - type: textarea
    id: evidence
    attributes:
      label: How would we know it works? (evaluation plan)
      description: |
        Which metric would move (intent macro-F1, Recall@5, escalation
        recall, unsafe auto-handle rate, judge agreement)? A feature
        without a measurement plan will be labeled `needs-evidence`.

  - type: dropdown
    id: area
    attributes:
      label: Area
      options:
        - agent behavior (intents, retrieval, generation, routing)
        - evaluation & metrics
        - data pipeline
        - tooling / DX / CI
        - documentation
    validations:
      required: true
