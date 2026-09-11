"""One-command reproduction: the complete evaluation pipeline.

Usage: python -m scripts.reproduce [--skip-download] [--systems ...]

Runs, in order (all steps cached; resumable):
  1. environment check (ollama models present)
  2. dataset download (public mirrors)            [skipped if present]
  3. brand profiling + corpus + splits
  4. LLM intent labelling of retrieval corpus     [cached; longest cold step]
  5. embedding index build
  6. golden set build (uses committed hand labels; no re-annotation needed)
  7. threshold tuning on validation split
  8. full evaluation: agent + baselines + judge
  9. judge-vs-human calibration
 10. failure analysis
"""

from __future__ import annotations

import argparse
import subprocess
import sys
import time

from scripts._bootstrap import ROOT  # noqa: F401

STEPS = [
    ("environment check", ["python", "-m", "scripts.check_env"]),
    ("dataset download", ["python", "-m", "scripts.download_data"]),
    ("brand profiling", ["python", "-m", "scripts.profile_dataset"]),
    ("corpus build", ["python", "-m", "scripts.build_corpus"]),
    ("corpus labelling", ["python", "-m", "scripts.label_corpus"]),
    ("index build", ["python", "-m", "scripts.build_index"]),
    ("data quality gate", ["python", "-m", "scripts.data_quality"]),
    ("threshold tuning", ["python", "-m", "scripts.evaluate", "--thresholds"]),
    ("full evaluation", ["python", "-m", "scripts.evaluate", "--systems", "agent,b1,b2,b3"]),
    ("judge calibration", ["python", "-m", "scripts.calibrate_judge"]),
    ("failure analysis", ["python", "-m", "scripts.analyze_failures"]),
]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--skip-download", action="store_true")
    args, extra = parser.parse_known_args()

    t0 = time.time()
    for name, cmd in STEPS:
        if args.skip_download and name == "dataset download":
            print("== skipping dataset download")
            continue
        print(f"\n===== {name} ".ljust(70, "="), flush=True)
        result = subprocess.run(cmd, cwd=str(ROOT))
        if result.returncode != 0:
            print(f"STEP FAILED: {name} (exit {result.returncode})")
            sys.exit(result.returncode)

    print(f"\n{'=' * 70}")
    print(f"Reproduction complete in {time.time() - t0:.0f}s")
    print("Headline results: reports/results.json")
    print("Full report:      reports/final_report.md")


if __name__ == "__main__":
    main()
