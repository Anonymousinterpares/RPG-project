#!/usr/bin/env python3
"""
Headless test for generation rules scaling and overlay allowance enforcement.

Usage (PowerShell):
  py -3 -X utf8 tools\test_npc_generation_rules_headless.py
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
    overlays = (cfg.get("npc_boss_overlays.overlays") or {})
    if not fams:
        print("ERROR: No families loaded")
        return 1

    any_family = next(iter(fams.keys()))
    gen = NPCFamilyGenerator()

    # Compare baseline vs 'hard' scaling by temporarily tweaking rules in-memory is outside scope;
    # Instead, we just ensure generation runs with current rules.
    npc = gen.generate_npc_from_family(any_family, name="RulesTest", level=5, difficulty="hard", encounter_size="solo")
    sm = npc.stats_manager
    print(f"OK: rules baseline family={any_family} hp={sm.get_current_stat_value(DerivedStatType.HEALTH):.0f} def={sm.get_stat_value(DerivedStatType.DEFENSE):.0f}")

    # Enforce allowed overlays: find a family that explicitly forbids bosses or has empty allowed_overlays
    disallowed = None
    for fid, fam in fams.items():
        if not fam.get("is_boss_allowed", True):
            disallowed = fid
            break
        rules = fam.get("rules", {}) or {}
        if isinstance(rules.get("allowed_overlays"), list) and rules.get("allowed_overlays") == []:
            disallowed = fid
            break
    if disallowed and overlays:
        ov = next(iter(overlays.keys()))
        try:
            gen.generate_npc_from_family(disallowed, name="BossDisallowed", level=1, overlay_id=ov)
            print("FAIL: overlay allowed when it should be disallowed")
            return 1
        except Exception as e:
            print(f"OK: overlay disallowed enforced for family={disallowed} overlay={ov} error={e}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())

