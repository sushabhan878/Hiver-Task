"""Tweet/text normalization for the Twitter customer-support corpus."""
from __future__ import annotations

import re
from dataclasses import dataclass

URL_RE = re.compile(r"https?://\S+|www\.\S+")
MENTION_RE = re.compile(r"@\w+")
WS_RE = re.compile(r"\s+")
EMOJI_RE = re.compile(
    "[\U0001F300-\U0001FAFF\U00002700-\U000027BF\U0001F000-\U0001F02F"
    "\U0001F0A0-\U0001F0FF\U00002600-\U000026FF\U0000FE0F\U0000200D]"
)


@dataclass
class CleaningStats:
    url_replaced: int = 0
    mentions_replaced: int = 0
    emojis_removed: int = 0
    dropped_empty: int = 0
    dropped_spam: int = 0

    def merge(self, other: "CleaningStats") -> None:
        self.url_replaced += other.url_replaced
        self.mentions_replaced += other.mentions_replaced
        self.emojis_removed += other.emojis_removed
        self.dropped_empty += other.dropped_empty
        self.dropped_spam += other.dropped_spam


def clean_text(text: str, stats: CleaningStats | None = None) -> str:
    """Normalize a tweet while preserving realistic noise (typos, casing).

    - URLs -> <url>
    - @mentions -> <user> (but keep brand-facing handles like @AmazonHelp meaningful)
    - strip emojis, collapse whitespace
    """
    if not isinstance(text, str):
        return ""
    if stats:
        stats.url_replaced += len(URL_RE.findall(text))
        stats.mentions_replaced += len(MENTION_RE.findall(text))
        stats.emojis_removed += len(EMOJI_RE.findall(text))
    text = URL_RE.sub("<url>", text)
    text = MENTION_RE.sub("<user>", text)
    text = EMOJI_RE.sub("", text)
    text = WS_RE.sub(" ", text).strip()
    return text


def is_spam_or_bot(text: str) -> bool:
    """Heuristic obvious spam/bot filter (kept intentionally minimal)."""
    t = text.lower()
    if not t:
        return True
    spam_tokens = ["follow me", "dm for promo", "buy followers", "free followers",
                   "make money fast", "work from home $$$", "click here to win"]
    if any(tok in t for tok in spam_tokens):
        return True
    # excessive hashtag/promo stuffing
    if t.count("#") >= 5:
        return True
    return False
