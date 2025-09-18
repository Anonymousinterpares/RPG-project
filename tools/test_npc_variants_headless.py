#!/usr/bin/env python3
"""
Headless test for generating NPCs from variants in families mode.

Usage (PowerShell):
  py -3 -X utf8 tools\test_npc_variants_headless.py
"""
import sys
from pathlib import Path as _Path
import sys as _sys

# Ensure project root is on sys.path
_proj_root = _Path(__file__).resolve().parents[1]
if str(_proj_root) not in _sys.path:
    _sys.path.insert(0, str(_proj_root))

from core.base.config import get_config
from core.character.npc_family_generator import NPCFamilyGenerator
from core.stats.stats_base import DerivedStatType

def main() -> int:
    cfg = get_config()
    fams = (cfg.get("npc_families.families") or {})
    fams_factions = (cfg.get("npc_families_factions.families") or {})
    merged = {**fams, **fams_factions}
    variants = (cfg.get("npc_variants.variants") or {})

    if not variants:
        print("ERROR: No variants found in config.")
        return 1

    gen = NPCFamilyGenerator()

    # Pick a few known variants from the provided config
    picks = []
    for vid in [
        "concordant_medic",
        "concordant_enforcer",
        "verdant_pathfinder",
        "crystalline_calculator",
        "ashen_binder",
        "tempest_duelist",
        "verdant_alpha",
        "crystalline_bulwark",
    ]:
        if vid in variants:
            picks.append(vid)
    if not picks:
        picks = list(variants.keys())[:3]

    errors = 0
    for vid in picks:
        try:
            npc = gen.generate_npc_from_variant(vid, name=f"TestVar {vid}", level=1, difficulty="normal", encounter_size="solo")
            sm = npc.stats_manager
            max_hp = sm.get_stat_value(DerivedStatType.MAX_HEALTH)
            cur_hp = sm.get_current_stat_value(DerivedStatType.HEALTH)
            defense = sm.get_stat_value(DerivedStatType.DEFENSE)
            initiative = sm.get_stat_value(DerivedStatType.INITIATIVE)
            role = npc.known_information.get("role") if npc.known_information else None
            abilities = npc.known_information.get("abilities") if npc.known_information else None
            print(f"OK: variant={vid} name={npc.name} hp={cur_hp:.0f}/{max_hp:.0f} def={defense:.0f} init={initiative:.0f} role={role} abilities={abilities}")
        except Exception as e:
            print(f"FAIL: variant={vid} error={e}")
            errors += 1

    return 1 if errors else 0

if __name__ == "__main__":
    raise SystemExit(main())

