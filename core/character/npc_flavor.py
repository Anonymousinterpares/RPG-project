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

    # Prefer using the existing engine AgentManager pipeline
    try:
        from core.base.engine import get_game_engine
        engine = get_game_engine()
        game_state = engine.state_manager.current_state if engine and hasattr(engine, 'state_manager') else None
        if not engine or not engine._agent_manager or not game_state:
            return
    except Exception as e:
        logger.warning(f"LLM engine/manager unavailable: {e}")
        return

    # Build a compact structured prompt reflecting rules and context
    ki = getattr(npc, "known_information", None) or {}
    tags = ki.get("tags", [])
    flavor_ctx = ki.get("flavor_context", {})
    family_id = flavor_ctx.get("family_id") or ki.get("family_id")
    culture = flavor_ctx.get("culture")
    location = flavor_ctx.get("location")
    kind = flavor_ctx.get("kind")

    # Construct a user prompt text; engine will pass it to AgentManager
    policy = (
        "Rules: concise, lore-consistent; no meta; do not provide hints or spoilers; respect cultural tone.\n"
    )
    need_desc = not bool(getattr(npc, "description", None))
    need_back = not bool(ki.get("backstory"))
    if not need_desc and not need_back:
        return

    prompt = (
        f"Enrich NPC flavor. {policy}"
        f"DATA: name={npc.name!r} family_id={family_id!r} tags={tags} culture={culture!r} location={location!r} kind={kind!r}.\n"
        f"Please return a short description and a short backstory."
    )

    try:
        text, commands = engine._agent_manager.process_input(game_state=game_state, player_input=prompt)
        text = (text or "").strip()
        if not text:
            return
        parts = [p.strip() for p in text.split("\n\n") if p.strip()]
        if need_desc and parts:
            npc.description = parts[0][:240]
        if need_back:
            backstory = parts[1] if len(parts) > 1 else (parts[0] if parts else "")
            if backstory:
                ki["backstory"] = backstory[:480]
                npc.known_information = ki
    except Exception as e:
        logger.warning(f"Flavor enrichment failed: {e}")

