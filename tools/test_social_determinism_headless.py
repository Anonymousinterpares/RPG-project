#!/usr/bin/env python3
"""
Headless determinism test for social/commerce/quest NPC family selection and naming.
Runs multiple seeds for the same location and roles and prints chosen families/names.

Usage (PowerShell):
  py -3 -X utf8 tools\test_social_determinism_headless.py
"""
from pathlib import Path as _Path
import sys as _sys

_proj_root = _Path(__file__).resolve().parents[1]
if str(_proj_root) not in _sys.path:
    _sys.path.insert(0, str(_proj_root))

from core.base.config import get_config
from core.character.npc_system import NPCSystem

def main() -> int:
    cfg = get_config()
    # Ensure families mode for this run
    cfg._config_data.setdefault("system", {})
    cfg._config_data["system"]["npc_generation_mode"] = "families"

    loc = "harmonia"

    system = NPCSystem()

    seeds = ["A", "B", "C", "D"]
    print("-- Merchants --")
    for s in seeds:
        npc = system.creator.create_merchant(name=None, shop_type="general", location=loc)
        fam = (npc.known_information or {}).get("family_id")
        print(f"seed={s}: name={npc.name} family={fam}")

    print("-- Services --")
    for s in seeds:
        npc = system.creator.create_service_npc(name=None, service_type="innkeeper", location=loc)
        fam = (npc.known_information or {}).get("family_id")
        print(f"seed={s}: name={npc.name} family={fam}")

    print("-- Quest givers --")
    for s in seeds:
        npc = system.creator.create_quest_giver(name=None, quest_type="delivery", location=loc)
        fam = (npc.known_information or {}).get("family_id")
        print(f"seed={s}: name={npc.name} family={fam}")

    return 0

if __name__ == "__main__":
    raise SystemExit(main())

