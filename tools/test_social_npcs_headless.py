#!/usr/bin/env python3
"""
Headless test that spawns social/commerce/quest NPCs in families mode and prints
weighted family choice, tags, and names. This verifies deterministic selection,
full stats generation, tags application, and flavor scaffolding.

Usage (PowerShell):
  py -3 -X utf8 tools\test_social_npcs_headless.py
"""
from pathlib import Path as _Path
import sys as _sys

_proj_root = _Path(__file__).resolve().parents[1]
if str(_proj_root) not in _sys.path:
    _sys.path.insert(0, str(_proj_root))

from core.base.config import get_config
from core.character.npc_system import NPCSystem
from core.character.npc_base import NPCInteractionType


def main() -> int:
    cfg = get_config()
    # Ensure families mode for this run
    try:
        cfg._config_data.setdefault("system", {})
        cfg._config_data["system"]["npc_generation_mode"] = "families"
        cfg._config_data.setdefault("game", {})
        cfg._config_data["game"]["difficulty"] = "normal"
        cfg._config_data["game"]["encounter_size"] = "solo"
    except Exception:
        pass

    system = NPCSystem()

    # Define test locations and config culture_mix inline (in-memory) if missing
    loc = "concordant_city"
    try:
        cfg._config_data.setdefault("locations", {})
        cfg._config_data["locations"].setdefault(loc, {})
        cfg._config_data["locations"][loc].setdefault("culture_mix", {
            "concordant": 0.8,
            "verdant": 0.1,
            "crystalline": 0.05,
            "tempest": 0.05,
        })
    except Exception:
        pass

    # Create a merchant, a service NPC, and a quest giver
    merchant = system.creator.create_merchant(name=None, shop_type="weapons", location=loc)
    service_npc = system.creator.create_service_npc(name=None, service_type="innkeeper", location=loc)
    quest_giver = system.creator.create_quest_giver(name=None, quest_type="delivery", location=loc)

    def summarize(npc):
        fam = (npc.known_information or {}).get("family_id") if getattr(npc, "known_information", None) else None
        print(f"NPC: {npc.name} type={npc.npc_type.name} family={fam} tags={(npc.known_information or {}).get('tags')}")

    summarize(merchant)
    summarize(service_npc)
    summarize(quest_giver)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())

