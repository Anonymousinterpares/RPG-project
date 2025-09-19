#!/usr/bin/env python3
"""
Headless test to verify spawn intent resolution in families mode.

Usage:
  py -3 -X utf8 tools\test_spawn_intent_resolution_headless.py
"""
from __future__ import annotations
import json
import sys

from core.base.config import get_config
from core.base.state import get_state_manager
from core.character.npc_system import NPCSystem


def main() -> int:
    # Ensure families mode for this run (in-memory)
    cfg = get_config()
    try:
        cfg._config_data.setdefault("system", {})["npc_generation_mode"] = "families"  # type: ignore[attr-defined]
        print("INFO: Running with system.npc_generation_mode=families (in-memory)")
    except Exception:
        print("WARN: Could not set in-memory families mode; behavior may vary.")

    # Initialize NPCSystem
    sm = get_state_manager()
    try:
        npc_system = sm.get_npc_system()
        if not npc_system:
            npc_system = NPCSystem()
            sm.set_npc_system(npc_system)
    except Exception:
        npc_system = NPCSystem()

    # Simulate mode transition spawn hints (wolf, easy, non-boss)
    spawn_request = {
        "target_mode": "COMBAT",
        "origin_mode": "NARRATIVE",
        "reason": "Player attacks the wolf.",
        "enemy_template": None,
        "enemy_count": 1,
        "enemy_level": 1,
        "spawn_hints": {
            "actor_type": "beast",
            "threat_tier": "easy",
            "species_tags": ["wolf"],
            "is_boss": False
        }
    }
    print("REQUEST:")
    print(json.dumps(spawn_request, indent=2))

    # Emulate the same logic mode_transitions would perform to build a template
    enemy_template = None
    hints = spawn_request.get("spawn_hints") or {}
    tier = (hints.get("threat_tier") or "normal").lower()
    atype = (hints.get("actor_type") or "beast").lower()
    computed_id = f"{atype}_{tier}_base"
    enemy_template = computed_id

    # Create the NPC via families path
    npc = npc_system.create_enemy_for_combat(
        name="Wolf",
        enemy_type=enemy_template,
        level=int(spawn_request.get("enemy_level", 1)),
        location="test_forest"
    )

    if not npc:
        print("FAIL: NPC creation returned None")
        return 1

    known = getattr(npc, "known_information", {}) or {}
    tags = known.get("tags") or []
    family_id = known.get("family_id")

    print("RESULT:")
    print(json.dumps({
        "name": npc.name,
        "family_id": family_id,
        "tags": tags,
        "hp": getattr(npc, "current_hp", None),
        "defense": getattr(npc, "defense", None),
        "generator": known.get("generator"),
    }, indent=2))

    # Basic assertions
    if not family_id or not isinstance(tags, list):
        print("FAIL: Missing family_id or tags")
        return 1
    if not family_id.startswith("beast_"):
        print(f"FAIL: Expected a beast family, got {family_id}")
        return 1

    print("PASS: Families-mode spawn intent resolution OK.")
    return 0


if __name__ == "__main__":
    sys.exit(main())

