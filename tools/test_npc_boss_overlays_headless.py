#!/usr/bin/env python3
"""
Headless test for boss overlays in families mode.

Usage (PowerShell):
  py -3 -X utf8 tools\test_npc_boss_overlays_headless.py
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
    fams = {**(cfg.get("npc_families.families") or {}), **(cfg.get("npc_families_factions.families") or {})}
    variants = (cfg.get("npc_variants.variants") or {})
    overlays = (cfg.get("npc_boss_overlays.overlays") or {})

    if not fams or not overlays:
        print("ERROR: Missing families or overlays.")
        return 1

    gen = NPCFamilyGenerator()

    # Choose an overlay and a family that allows it
    overlay_id = next(iter(overlays.keys()))
    family_id = None
    for fid, fam in fams.items():
        if not fam.get("is_boss_allowed", True):
            continue
        rules = fam.get("rules", {}) or {}
        allowed = rules.get("allowed_overlays")
        if isinstance(allowed, list) and allowed and overlay_id not in allowed:
            continue
        family_id = fid
        break

    errors = 0
    if family_id is not None:
        try:
            npc_fam = gen.generate_npc_from_family(family_id, name=f"Boss {family_id}", level=1, overlay_id=overlay_id, difficulty="normal", encounter_size="solo")
            sm = npc_fam.stats_manager
            max_hp = sm.get_stat_value(DerivedStatType.MAX_HEALTH)
            cur_hp = sm.get_current_stat_value(DerivedStatType.HEALTH)
            defense = sm.get_stat_value(DerivedStatType.DEFENSE)
            initiative = sm.get_stat_value(DerivedStatType.INITIATIVE)
            tags = npc_fam.known_information.get("tags") if npc_fam.known_information else None
            print(f"OK: family+overlay family={family_id} overlay={overlay_id} hp={cur_hp:.0f}/{max_hp:.0f} def={defense:.0f} init={initiative:.0f} tags={tags}")
        except Exception as e:
            print(f"FAIL: family+overlay error={e}")
            errors += 1
    else:
        print("SKIP: No family found that allows the chosen overlay")

    # If variants exist, test one as boss too
    if variants:
        vid = next(iter(variants.keys()))
        try:
            npc_var = gen.generate_npc_from_variant(vid, name=f"BossVar {vid}", level=1, overlay_id=overlay_id, difficulty="normal", encounter_size="solo")
            sm = npc_var.stats_manager
            max_hp = sm.get_stat_value(DerivedStatType.MAX_HEALTH)
            cur_hp = sm.get_current_stat_value(DerivedStatType.HEALTH)
            defense = sm.get_stat_value(DerivedStatType.DEFENSE)
            initiative = sm.get_stat_value(DerivedStatType.INITIATIVE)
            tags = npc_var.known_information.get("tags") if npc_var.known_information else None
            print(f"OK: variant+overlay variant={vid} overlay={overlay_id} hp={cur_hp:.0f}/{max_hp:.0f} def={defense:.0f} init={initiative:.0f} tags={tags}")
        except Exception as e:
            print(f"FAIL: variant+overlay error={e}")
            errors += 1

    return 1 if errors else 0

if __name__ == "__main__":
    raise SystemExit(main())

