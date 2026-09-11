"""Risk tiering per intent, loaded from configs/intents.yaml."""

from __future__ import annotations

from src.config import intents_cfg


class RiskTiers:
    def __init__(self, cfg: dict | None = None):
        cfg = cfg or intents_cfg()
        self.intent_risk: dict[str, str] = {}
        for intent, spec in cfg["intents"].items():
            self.intent_risk[intent] = spec["risk"]
        self.tier_intents: dict[str, list[str]] = cfg["risk_tiers"]
        self.default_action: dict[str, str] = cfg["default_action_by_risk"]

    def risk_of(self, intent: str) -> str:
        return self.intent_risk.get(intent, "medium")

    def is_high_risk(self, intent: str) -> bool:
        return self.risk_of(intent) == "high"

    def default_action_for(self, intent: str) -> str:
        return self.default_action.get(self.risk_of(intent), "conditional")
