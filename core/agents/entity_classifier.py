#!/usr/bin/env python3
"""
EntityClassifierAgent: A minimal LLM-backed classifier that maps a free-form enemy
specification (name + brief context) to strict enums:
- actor_type: one of {beast, humanoid, undead, construct, elemental, spirit}
- threat_tier: one of {harmless, easy, normal, dangerous, ferocious, mythic}

Rules:
- Never invent family_id. Only return enums (and optional known variant_id if present in config).
- Keep outputs as strict JSON.

This agent exists to ensure universal, name-agnostic mapping for any enemy name.
"""
from __future__ import annotations

import json
from typing import Any, Dict, Optional

from core.agents.base_agent import BaseAgent, AgentContext
from core.utils.logging_config import get_logger
from core.base.config import get_config

logger = get_logger("AGENT")


class EntityClassifierAgent(BaseAgent):
    """LLM classifier that outputs strict enums for actor_type and threat_tier."""

    def __init__(self) -> None:
        super().__init__("entity_classifier")

    def _generate_system_prompt(self, context: AgentContext) -> str:
        cfg = get_config()
        # Enumerations we support today (families.json defines beast_*, humanoid_*)
        allowed_actor_types = ["beast", "humanoid", "undead", "construct", "elemental", "spirit"]
        allowed_threat_tiers = ["harmless", "easy", "normal", "dangerous", "ferocious", "mythic"]
        # Strict JSON schema in prose
        system = f"""
You are the EntityClassifier for an RPG engine. Your task is to classify a described enemy
into STRICT enums and return a compact JSON object. Do not write anything except the JSON.

CRITICAL RULES
- NEVER invent or output a family_id.
- Output ONLY these fields:
  {{
    "actor_type": one of {allowed_actor_types},
    "threat_tier": one of {allowed_threat_tiers},
    "variant_id": string | null,
    "overlay": string | null,
    "confidence": number between 0 and 1
  }}
- variant_id is optional and MUST refer to a real known variant if used; otherwise set null.
- overlay is optional; usually null.
- Choose actor_type and threat_tier based on the description and context. Prefer conservative mapping if uncertain.
- If information is insufficient, set confidence low (e.g., 0.4–0.6) and still choose enums.

OUTPUT FORMAT (JSON ONLY)
{{"actor_type":"...","threat_tier":"...","variant_id":null,"overlay":null,"confidence":0.0}}
""".replace("{allowed_actor_types}", ", ".join(allowed_actor_types)).replace("{allowed_threat_tiers}", ", ".join(allowed_threat_tiers))
        return system

    def process(self, context: AgentContext) -> Dict[str, Any]:
        """Call the LLM and parse a strict classification JSON."""
        messages = []
        system_prompt = self._generate_system_prompt(context)
        messages.append({"role": "system", "content": system_prompt})

        # The user message contains compact details to help classification
        user_msg = context.player_input.strip()
        messages.append({"role": "user", "content": user_msg})

        try:
            llm_response = self._llm_manager.get_completion(
                messages=messages,
                provider_type=self._provider_type,
                model=self._model,
                temperature=min(0.2, float(self._temperature or 0.2)),
                max_tokens=self._settings.get("max_tokens", 300),
                timeout=self._settings.get("timeout_seconds", 15),
            )
            raw = (llm_response.content or "").strip()
            # Strip possible code fences
            if raw.startswith("```"):
                raw = raw.strip("` ")
                # try to find JSON braces
                l = raw.find("{")
                r = raw.rfind("}")
                if l != -1 and r != -1:
                    raw = raw[l : r + 1]
            # Parse JSON
            data = json.loads(raw)
            # Basic sanitation
            actor_type = str(data.get("actor_type", "")).lower()
            threat_tier = str(data.get("threat_tier", "")).lower()
            variant_id = data.get("variant_id")
            overlay = data.get("overlay")
            confidence = float(data.get("confidence", 0.5))

            allowed_actor_types = {"beast", "humanoid", "undead", "construct", "elemental", "spirit"}
            allowed_threat_tiers = {"harmless", "easy", "normal", "dangerous", "ferocious", "mythic"}

            if actor_type not in allowed_actor_types:
                actor_type = "beast"  # conservative default
            if threat_tier not in allowed_threat_tiers:
                threat_tier = "normal"

            # Validate variant against config (optional)
            try:
                variants = cfg.get("npc_variants.variants") or {}
                if not isinstance(variants, dict) or not variant_id or variant_id not in variants:
                    variant_id = None
            except Exception:
                variant_id = None

            return {
                "actor_type": actor_type,
                "threat_tier": threat_tier,
                "variant_id": variant_id,
                "overlay": overlay if isinstance(overlay, str) else None,
                "confidence": max(0.0, min(1.0, confidence)),
            }
        except Exception as e:
            logger.error(f"EntityClassifierAgent error: {e}")
            # Safe default
            return {
                "actor_type": "beast",
                "threat_tier": "normal",
                "variant_id": None,
                "overlay": None,
                "confidence": 0.0,
            }


# Convenience
_singleton: Optional[EntityClassifierAgent] = None

def get_entity_classifier_agent() -> EntityClassifierAgent:
    global _singleton
    if _singleton is None:
        _singleton = EntityClassifierAgent()
    return _singleton
