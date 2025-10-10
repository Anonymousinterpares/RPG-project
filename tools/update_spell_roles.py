#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
update_spell_roles.py

Quick one-off updater to inject manually chosen combat_role values into a magic_systems JSON file,
writing to a new output path (does not overwrite input).

Usage:
  python tools/update_spell_roles.py --input "config/world/base/magic_systems.cleaned.json" \
    --output "config/world/base/magic_systems.cleaned.manual_roles.json"
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Dict

ALLOWED = {"offensive", "defensive", "utility"}

# Manual role mapping chosen by designer
ROLE_MAP: Dict[str, Dict[str, str]] = {
    "song_weaving": {
        "harmonic_healing": "defensive",
        "resonant_shield": "defensive",
        "chorus_of_clarity": "defensive",
        "dirge_of_despair": "offensive",
        "planar_harmonization": "utility",
        "song_of_mending": "utility",
    },
    "planar_anchoring": {
        "stability_field": "defensive",
        "reality_tether": "defensive",
        "planar_sight": "utility",
        "boundary_distortion": "utility",
        "resonance_shield": "defensive",
        "planar_transit": "utility",
    },
    "echo_binding": {
        "echo_capture": "utility",
        "bind_echo": "utility",
        "echo_sight": "utility",
        "weapon_echo": "offensive",
        "echo_ward": "defensive",
        "echo_mimicry": "utility",
    },
    "facet_magic": {
        "prismatic_bolt": "offensive",
        "crystalline_shield": "defensive",
        "computational_enhancement": "utility",
        "perfect_analysis": "utility",
        "geometric_restructuring": "utility",
        "crystal_prison": "offensive",
    },
    "ash_walking": {
        "minor_projection": "utility",
        "ashen_transit": "utility",
        "whispers_of_ash": "utility",
        "ashen_knowledge": "utility",
        "ash_veil": "defensive",
        "ashen_body": "defensive",
    },
    "divine_healing": {
        "healing_touch": "defensive",
        "purify_body": "defensive",
        "divine_restoration": "defensive",
        "circle_of_healing": "defensive",
        "protective_blessing": "defensive",
        "revitalize": "defensive",
    },
}


def _norm_systems(data: Any) -> Dict[str, Dict[str, Any]]:
    if isinstance(data, dict) and "magic_systems" in data:
        container = data["magic_systems"]
    else:
        container = data
    if isinstance(container, dict):
        return container
    if isinstance(container, list):
        return {str(i): v for i, v in enumerate(container) if isinstance(v, dict)}
    return {}


def _norm_spells(spells: Any) -> Dict[str, Dict[str, Any]]:
    if isinstance(spells, dict):
        return spells
    if isinstance(spells, list):
        return { (s.get("id") if isinstance(s, dict) else str(i)): s for i, s in enumerate(spells) if isinstance(s, dict)}
    return {}


def main() -> int:
    ap = argparse.ArgumentParser(description="Inject manual combat_role values into magic systems JSON (write to new file)")
    ap.add_argument("--input", required=True, help="Path to input JSON (e.g., cleaned file)")
    ap.add_argument("--output", required=True, help="Path to write updated JSON")
    args = ap.parse_args()

    src = Path(args.input)
    dst = Path(args.output)

    data = json.loads(src.read_text(encoding="utf-8"))

    systems = _norm_systems(data)

    updated_count = 0
    missing_count = 0

    for sys_id, spell_roles in ROLE_MAP.items():
        system = systems.get(sys_id)
        if not system:
            missing_count += len(spell_roles)
            continue
        spells = _norm_spells(system.get("spells"))
        for spell_id, role in spell_roles.items():
            if role not in ALLOWED:
                continue
            spell = spells.get(spell_id)
            if not spell:
                missing_count += 1
                continue
            if spell.get("combat_role") != role:
                spell["combat_role"] = role
                updated_count += 1

        # write back normalized spells mapping if needed
        system["spells"] = spells

    # Write output (preserve top-level shape)
    dst.parent.mkdir(parents=True, exist_ok=True)
    dst.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    print(f"Roles injected: {updated_count}; missing (not found): {missing_count}; written: {dst}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
