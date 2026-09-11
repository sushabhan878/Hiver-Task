"""Grounded reply generator with structured output."""

from __future__ import annotations

import re
from dataclasses import dataclass, field

from src.generation.prompts import PROMPT_VERSION, build_reply_prompt
from src.llm.client import OllamaClient

SIG_RE = re.compile(r"\^[A-Z]{2}\b")
QUOTE_RE = re.compile(r'^["\'`\u201c\u201d]+|["\'`\u201c\u201d]+$')
URL_RE = re.compile(r"https?://\S+|www\.\S+")


def clean_reply(reply: str) -> str:
    """Strip artifacts that leak from historical evidence: agent signatures
    (^MJ), enclosing quotes, and raw URLs (masked ones stay as <url>)."""
    if not reply:
        return ""
    r = SIG_RE.sub("", reply)
    r = QUOTE_RE.sub("", r.strip())
    r = URL_RE.sub("<url>", r)
    return r.strip()


@dataclass
class GeneratedReply:
    reply: str
    supporting_case_ids: list[str] = field(default_factory=list)
    grounded_claims: list[str] = field(default_factory=list)
    sufficient_evidence: bool = False
    prompt_version: str = PROMPT_VERSION
    model: str = ""
    parse_failed: bool = False
    raw: str = ""


class ReplyGenerator:
    def __init__(self, client: OllamaClient):
        self.client = client

    def generate(self, customer_message: str, intent: str, cases: list[dict]) -> GeneratedReply:
        msgs = build_reply_prompt(customer_message, intent, cases)
        try:
            out = self.client.chat_json(msgs, num_predict=300)
            reply = clean_reply(str(out.get("reply", "")))
            ids = [str(x) for x in out.get("supporting_case_ids", []) if x]
            claims = [str(x) for x in out.get("grounded_claims", []) if x]
            sufficient = bool(out.get("sufficient_evidence", False))
            ok = bool(reply)
            return GeneratedReply(
                reply=reply,
                supporting_case_ids=ids,
                grounded_claims=claims,
                sufficient_evidence=sufficient,
                model=self.client.chat_model,
                parse_failed=not ok,
                raw=str(out)[:200],
            )
        except Exception as e:
            return GeneratedReply(
                reply="",
                supporting_case_ids=[],
                grounded_claims=[],
                sufficient_evidence=False,
                model=self.client.chat_model,
                parse_failed=True,
                raw=f"error: {e}",
            )
