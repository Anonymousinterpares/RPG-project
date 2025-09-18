#!/usr/bin/env python3
"""
Attempt to enrich NPC flavor (short description and short backstory) using the LLM system.
This function is safe to call: it catches exceptions and only updates fields if LLM returns
usable content. It respects existing description if provided and only fills what's missing
or appends a short backstory if absent.
"""
from __future__ import annotations

from typing import Optional
from core.utils.logging_config import get_logger
from core.base.config import get_config

logger = get_logger("NPC_FLAVOR")


def attempt_enrich_npc_flavor(npc) -> None:
    try:
        cfg = get_config()
        llm_enabled = bool(cfg.get("llm.enabled", False))
    except Exception:
        llm_enabled = False

    if not llm_enabled:
        return

    try:
        from core.agents.agent_manager import get_agent_manager
        am = get_agent_manager()
    except Exception as e:
        logger.warning(f"LLM agent manager unavailable: {e}")
        return

    # Build a compact structured prompt reflecting rules and context
    ki = getattr(npc, "known_information", None) or {}
    tags = ki.get("tags", [])
    flavor_ctx = ki.get("flavor_context", {})
    family_id = flavor_ctx.get("family_id") or ki.get("family_id")
    culture = flavor_ctx.get("culture")
    location = flavor_ctx.get("location")
    kind = flavor_ctx.get("kind")

    system_directives = (
        "You are enriching NPC flavor for a deterministic RPG system. Follow rules strictly:\n"
        "- Keep descriptions concise and lore-consistent.\n"
        "- No spoilers or meta.\n"
        "- Social NPCs are usually not bosses (is_boss:false), but if context strongly supports it, suggest a hidden leadership flavor; engine validates boss overlays.\n"
        "- Use culturally appropriate tone.\n"
        "- Provide a short backstory (1–3 sentences) that fits tags and location.\n"
    )

    user_request = {
        "name": npc.name,
        "family_id": family_id,
        "tags": tags,
        "culture": culture,
        "location": location,
        "kind": kind,
        "need_description": not bool(getattr(npc, "description", None)),
        "need_backstory": not bool(ki.get("backstory")),
    }

    try:
        # Use a generic agent call; adapt to your agent schema as needed
        res = am.simple_completion(
            system=system_directives,
            user=("Enrich the following NPC with a brief in-world description and a short backstory.\n"
                  f"DATA: {user_request}"),
            max_tokens=180,
        )
        text = (res or "").strip()
        if not text:
            return
        # Simple extraction: split into two paragraphs if possible
        parts = [p.strip() for p in text.split("\n\n") if p.strip()]
        if user_request["need_description"] and parts:
            npc.description = parts[0][:240]
        if user_request["need_backstory"]:
            backstory = parts[1] if len(parts) > 1 else (parts[0] if parts else "")
            if backstory:
                ki["backstory"] = backstory[:480]
                npc.known_information = ki
    except Exception as e:
        logger.warning(f"Flavor enrichment failed: {e}")

