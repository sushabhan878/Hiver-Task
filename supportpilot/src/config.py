"""Configuration loading for SupportPilot."""

from __future__ import annotations

from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent

_CACHE: dict[str, dict] = {}


def load_yaml(path: str | Path) -> dict:
    p = Path(path)
    key = str(p.resolve())
    if key not in _CACHE:
        with open(p, encoding="utf-8") as f:
            _CACHE[key] = yaml.safe_load(f)
    return _CACHE[key]


def config() -> dict:
    return load_yaml(ROOT / "configs" / "config.yaml")


def intents_cfg() -> dict:
    return load_yaml(ROOT / "configs" / "intents.yaml")


def thresholds_cfg() -> dict:
    return load_yaml(ROOT / "configs" / "thresholds.yaml")


def project_path(rel: str) -> Path:
    return (ROOT / rel).resolve()
