"""Run the agent on a single message or a small file of messages.

Usage:
  python -m scripts.run_agent --message "where is my order 123?"
  python -m scripts.run_agent --message ""        (empty is valid input)
  python -m scripts.run_agent --file inputs.txt
"""

from __future__ import annotations

import argparse
import json

from scripts._bootstrap import ROOT  # noqa: F401


def _print(obj) -> None:
    """Console-safe JSON printer (Windows cp1252 consoles choke on Unicode)."""
    text = json.dumps(obj, ensure_ascii=True, indent=2)
    print(text)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--message", type=str, default=None)
    parser.add_argument("--file", type=str)
    args = parser.parse_args()

    messages = []
    if args.message is not None:
        messages = [args.message]
    elif args.file:
        with open(args.file, encoding="utf-8") as f:
            messages = [line.strip() for line in f if line.strip()]
    else:
        parser.error("provide --message or --file")

    from scripts.evaluate import load_components

    cfg, client, cases, retriever, classifier, generator, policy = load_components()
    from src.pipeline import SupportPilotAgent

    agent = SupportPilotAgent(classifier, retriever, generator, policy, cfg)

    for msg in messages:
        trace = agent.handle(msg)
        _print(trace)


if __name__ == "__main__":
    main()
