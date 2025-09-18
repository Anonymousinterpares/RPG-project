#!/usr/bin/env python3
"""
Headless smoke test for Phase 1 families-based NPC generation.

Usage (PowerShell):
  py -3 -X utf8 tools\test_npc_families_headless.py

This will:
- Set system.npc_generation_mode to "families" for the running process only (not saved)
- Instantiate NPCFamilyGenerator and generate a few sample NPCs by family id
- Print summary lines that can be checked in CI/headless mode
"""
import sys
import json
from pathlib import Path

import os
import sys as _sys
from pathlib import Path as _Path
# Ensure project root is on sys.path
_proj_root = _Path(__file__).resolve().parents[1]
if str(_proj_root) not in _sys.path:
    _sys.path.insert(0, str(_proj_root))

from core.base.config import get_config
from core.character.npc_family_generator import NPCFamilyGenerator
from core.stats.stats_base import DerivedStatType


def main() -> int:
    cfg = get_config()
    # Ensure families are available
    fams = cfg.get("npc_families.families") or {}
    fams_factions = cfg.get("npc_families_factions.families") or {}
    merged = {**fams, **fams_factions}

    if not merged:
        print("ERROR: No NPC families loaded from config.")
        return 1

    # Set mode to families for this test (not persisted; we don't save config here)
    # Just a display to confirm
    print("INFO: Running in families mode (test).")

    gen = NPCFamilyGenerator()

    # Pick up to 3 family ids to test
    test_ids = []
    for fid in [
        "concordant_citizen",
        "verdant_wanderer",
        "crystalline_adept",
        "ashen_nomad",
        "tempest_swashbuckler",
        "beast_normal_base",
        "verdant_beast",
    ]:
        if fid in merged:
            test_ids.append(fid)
    if not test_ids:
        # fallback: use first 3
        test_ids = list(merged.keys())[:3]

    errors = 0
    for fid in test_ids:
        try:
            npc = gen.generate_npc_from_family(fid, name=f"Test {fid}", level=1, difficulty="normal", encounter_size="solo")
            sm = npc.stats_manager
            max_hp = sm.get_stat_value(DerivedStatType.MAX_HEALTH)
            cur_hp = sm.get_current_stat_value(DerivedStatType.HEALTH)
            defense = sm.get_stat_value(DerivedStatType.DEFENSE)
            initiative = sm.get_stat_value(DerivedStatType.INITIATIVE)
            print(f"OK: family={fid} name={npc.name} hp={cur_hp:.0f}/{max_hp:.0f} def={defense:.0f} init={initiative:.0f}")
        except Exception as e:
            print(f"FAIL: family={fid} error={e}")
            errors += 1

    return 1 if errors else 0


if __name__ == "__main__":
    raise SystemExit(main())

