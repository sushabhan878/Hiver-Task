"""Ollama-backed LLM client with disk caching and JSON-mode helpers.

All calls are cached on disk keyed by (model, prompt, options) so evaluation
runs are deterministic and cheap to repeat. Temperature is 0 everywhere.
"""

from __future__ import annotations

import hashlib
import json
import re
import time
import urllib.error
import urllib.request
from threading import Lock

from src.config import config, project_path

_lock = Lock()


class LLMError(RuntimeError):
    pass


def _cache_key(payload: dict) -> str:
    raw = json.dumps(payload, sort_keys=True, ensure_ascii=True)
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


class OllamaClient:
    def __init__(self, cfg: dict | None = None):
        self.cfg = (cfg or config())["ollama"]
        self.base_url = self.cfg["base_url"].rstrip("/")
        self.chat_model = self.cfg["chat_model"]
        self.embed_model = self.cfg["embed_model"]
        self.cache_dir = project_path(self.cfg.get("cache_dir", "cache/llm"))
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.stats = {"chat_calls": 0, "chat_cached": 0, "embed_calls": 0, "embed_cached": 0}

    def _post(self, method: str, payload: dict, timeout: int | None = None) -> dict:
        req = urllib.request.Request(
            f"{self.base_url}{method}",
            data=json.dumps(payload).encode("utf-8"),
            headers={"content-type": "application/json"},
        )
        last_err = None
        for attempt in range(self.cfg.get("max_retries", 3)):
            try:
                with urllib.request.urlopen(
                    req, timeout=timeout or self.cfg["timeout_seconds"]
                ) as r:
                    return json.loads(r.read().decode("utf-8"))
            except (urllib.error.URLError, TimeoutError, ConnectionError) as e:  # noqa: PERF203
                last_err = e
                time.sleep(1.5 * (attempt + 1))
        raise LLMError(f"Ollama call failed after retries: {last_err}")

    def _cached(self, kind: str, payload: dict) -> dict | None:
        key = _cache_key(payload)
        f = self.cache_dir / f"{kind}_{key}.json"
        if f.exists():
            try:
                return json.loads(f.read_text(encoding="utf-8"))
            except json.JSONDecodeError:
                return None
        return None

    def _store(self, kind: str, payload: dict, result: dict) -> None:
        key = _cache_key(payload)
        f = self.cache_dir / f"{kind}_{key}.json"
        with _lock:
            f.write_text(json.dumps(result, ensure_ascii=False), encoding="utf-8")

    def chat(
        self,
        messages: list[dict],
        model: str | None = None,
        num_predict: int = 512,
        json_mode: bool = False,
    ) -> str:
        payload = {
            "model": model or self.chat_model,
            "messages": messages,
            "stream": False,
            "options": {
                "temperature": self.cfg.get("temperature", 0),
                "num_predict": num_predict,
                "seed": 42,
            },
        }
        if json_mode:
            payload["format"] = "json"
        cached = self._cached("chat", payload)
        if cached is not None:
            self.stats["chat_cached"] += 1
            return cached["content"]
        out = self._post("/api/chat", payload)
        if "message" not in out:
            raise LLMError(f"Unexpected chat response: {str(out)[:200]}")
        content = out["message"]["content"]
        self._store("chat", payload, {"content": content})
        self.stats["chat_calls"] += 1
        return content

    def chat_json(
        self,
        messages: list[dict],
        model: str | None = None,
        num_predict: int = 512,
        retries: int = 2,
    ) -> dict:
        """Chat call that must return a JSON object; retries on malformed output."""
        last_err = None
        for _ in range(retries + 1):
            text = self.chat(messages, model=model, num_predict=num_predict, json_mode=True)
            parsed = _extract_json(text)
            if parsed is not None and isinstance(parsed, dict):
                return parsed
            last_err = text[:200]
        raise LLMError(f"Could not parse JSON output: {last_err}")

    def embed(self, texts: list[str]) -> list[list[float]]:
        if not texts:
            return []
        results: list[list[float] | None] = [None] * len(texts)
        to_compute: list[tuple[int, str]] = []
        # batch cache lookups
        for i, t in enumerate(texts):
            payload = {"model": self.embed_model, "input": t}
            cached = self._cached("embed", payload)
            if cached is not None:
                results[i] = cached["embedding"]
                self.stats["embed_cached"] += 1
            else:
                to_compute.append((i, t))
        if to_compute:
            chunk = 32
            for start in range(0, len(to_compute), chunk):
                batch = to_compute[start : start + chunk]
                payload = {"model": self.embed_model, "input": [t for _, t in batch]}
                out = self._post("/api/embed", payload, timeout=max(60, len(batch) * 10))
                if "embeddings" not in out:
                    raise LLMError(f"Unexpected embed response: {str(out)[:200]}")
                for (i, t), emb in zip(batch, out["embeddings"], strict=True):
                    results[i] = emb
                    self._store(
                        "embed", {"model": self.embed_model, "input": t}, {"embedding": emb}
                    )
                    self.stats["embed_calls"] += 1
        return [r for r in results if r is not None]


def _extract_json(text: str) -> dict | None:
    text = text.strip()
    # strip markdown fences if present
    if text.startswith("```"):
        text = re.sub(r"^```(json)?\s*", "", text)
        text = re.sub(r"\s*```$", "", text)
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass
    # find first {...} block
    match = re.search(r"\{.*\}", text, re.DOTALL)
    if match:
        try:
            return json.loads(match.group(0))
        except json.JSONDecodeError:
            return None
    return None


_client: OllamaClient | None = None


def get_client() -> OllamaClient:
    global _client
    if _client is None:
        _client = OllamaClient()
    return _client
