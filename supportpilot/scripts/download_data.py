"""Download the dataset mirrors used by this project.

Primary dataset: Customer Support on Twitter (thoughtvector/customer-support-on-twitter).
The original HF repo is gated; this project uses two public mirrors that preserve
the full data:
  - TNE-AI/customer-support-on-twitter-conversation (conversation-level; primary)
  - gorkemsevinc/Customer_Support_on_Twitter (tweet-level; auxiliary)

If the mirrors are unavailable, obtain twcs.csv from Kaggle
(thoughtvector/customer-support-on-twitter) and convert to parquet.
"""

from __future__ import annotations

import sys
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

CONV_URL = (
    "https://huggingface.co/datasets/TNE-AI/"
    "customer-support-on-twitter-conversation/resolve/main/"
    "data/train-00000-of-00001.parquet"
)
TWEET_URL = (
    "https://huggingface.co/datasets/gorkemsevinc/"
    "Customer_Support_on_Twitter/resolve/main/"
    "data/train-00000-of-00001.parquet"
)

FILES = {
    "data/raw/twcs_conversations.parquet": CONV_URL,
    "data/raw/twcs.parquet": TWEET_URL,
}


def main():
    for rel, url in FILES.items():
        dest = ROOT / rel
        if dest.exists() and dest.stat().st_size > 10_000_000:
            print(f"already present: {rel} ({dest.stat().st_size // 1_000_000} MB)")
            continue
        dest.parent.mkdir(parents=True, exist_ok=True)
        print(f"downloading {rel} ...")
        urllib.request.urlretrieve(url, dest)
        print(f"  saved {dest.stat().st_size // 1_000_000} MB")


if __name__ == "__main__":
    main()
