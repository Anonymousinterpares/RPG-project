#!/usr/bin/env python3
"""
Headless NPC generation report for families-based system.
Generates non-combat (merchant/quest-giver/service) and combat enemies across a few locations,
using families-mode logic, and writes a JSON report plus prints a concise summary.

Safe to run repeatedly. Does not persistently change config files; applies in-memory override for mode.
"""
from __future__ import annotations

import os
import json
import random
import sys
from typing import Any, Dict, List, Optional

# Ensure project root on sys.path
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, PROJECT_ROOT)

# Import core systems
from core.base.config import get_config
from core.character.npc_manager import NPCManager
from core.character.npc_creator import NPCCreator
from core.character.npc_base import NPCType, NPCRelationship
from core.stats.stats_base import DerivedStatType

REPORT_DIR = os.path.join("reports")
REPORT_PATH = os.path.join(REPORT_DIR, "npc_headless_report.json")


def _ensure_dir(path: str) -> None:
    d = os.path.dirname(path)
    if d and not os.path.exists(d):
        os.makedirs(d, exist_ok=True)


def _get_locations(cfg) -> List[str]:
    locs = cfg.get("locations") or {}
    if isinstance(locs, dict):
        return list(locs.keys())
    return []


def _get_families(cfg) -> List[str]:
    fams = cfg.get("npc_families.families") or {}
    if isinstance(fams, dict):
        return list(fams.keys())
    return []


def _get_variants(cfg) -> List[str]:
    vars_ = cfg.get("npc_variants.variants") or {}
    if isinstance(vars_, dict):
        return list(vars_.keys())
    return []


def _stats_summary(npc) -> Dict[str, Any]:
    out = {
        "HP": None,
        "Defense": None,
        "Initiative": None,
    }
    try:
        if npc and npc.stats_manager:
            out["HP"] = f"{npc.stats_manager.get_stat_value(DerivedStatType.HEALTH):.0f}/{npc.stats_manager.get_stat_value(DerivedStatType.MAX_HEALTH):.0f}"
            out["Defense"] = round(npc.stats_manager.get_stat_value(DerivedStatType.DEFENSE))
            out["Initiative"] = round(npc.stats_manager.get_stat_value(DerivedStatType.INITIATIVE))
    except Exception:
        pass
    return out


def _info(npc) -> Dict[str, Any]:
    ki = npc.known_information or {}
    fam_id = ki.get("family_id")
    is_boss = any(str(t).lower() == "is_boss:true" for t in ki.get("tags", []) or []) or bool(ki.get("boss_overlay_id"))
    role = ki.get("role")
    abilities = ki.get("abilities") or []
    return {
        "name": npc.name,
        "npc_type": npc.npc_type.name if hasattr(npc.npc_type, "name") else str(npc.npc_type),
        "relationship": npc.relationship.name if hasattr(npc.relationship, "name") else str(npc.relationship),
        "location": npc.location,
        "family_id": fam_id,
        "role": role,
        "abilities_count": len(abilities),
        "is_boss": is_boss,
        "tags": ki.get("tags", []),
        "stats": _stats_summary(npc),
    }


def run_report() -> Dict[str, Any]:
    cfg = get_config()
    # In-memory override to families mode for this run only (do not persist)
    try:
        # Access internal structure carefully
        if hasattr(cfg, "_config_data") and isinstance(cfg._config_data, dict):
            sys_data = cfg._config_data.get("system", {})
            sys_data["npc_generation_mode"] = "families"
            cfg._config_data["system"] = sys_data
    except Exception:
        pass

    # Prepare managers
    manager = NPCManager(save_directory=os.path.join("saves", "npcs", "_report_tmp"))
    creator = NPCCreator(manager)

    # Choose up to 3 locations for context variety
    loc_ids = _get_locations(cfg)
    sample_locations = loc_ids[:3] if len(loc_ids) >= 3 else loc_ids
    if not sample_locations:
        sample_locations = [""]

    families = _get_families(cfg)
    variants = _get_variants(cfg)

    # Difficulty and encounter from config (if present)
    difficulty = (cfg.get("game.difficulty", "normal") or "normal")
    encounter = (cfg.get("game.encounter_size", "solo") or "solo")

    report: Dict[str, Any] = {
        "meta": {
            "mode": "families",
            "difficulty": difficulty,
            "encounter_size": encounter,
        },
        "non_combat": [],
        "combat": [],
    }

    # Non-combat: merchant, quest giver, service across locations
    service_types = ["innkeeper", "healer", "blacksmith"]
    for loc in sample_locations:
        # Merchant
        try:
            npc = creator.create_merchant(name=None, shop_type=random.choice(["general", "weapons", "potions"]), location=loc)
            report["non_combat"].append(_info(npc))
        except Exception as e:
            report["non_combat"].append({"error": f"merchant failed at {loc}: {e}"})
        # Quest giver
        try:
            npc = creator.create_quest_giver(name=None, quest_type=random.choice(["general", "fetch", "kill"]), location=loc)
            report["non_combat"].append(_info(npc))
        except Exception as e:
            report["non_combat"].append({"error": f"quest_giver failed at {loc}: {e}"})
        # Service
        try:
            npc = creator.create_service_npc(name=None, service_type=random.choice(service_types), location=loc)
            report["non_combat"].append(_info(npc))
        except Exception as e:
            report["non_combat"].append({"error": f"service failed at {loc}: {e}"})

    # Combat: generate 1-2 enemies per location using families or variants
    fam_choices = families[:3] if len(families) >= 3 else families
    var_choices = variants[:3] if len(variants) >= 3 else variants

    for loc in sample_locations:
        # Family enemy
        if fam_choices:
            try:
                fam_id = random.choice(fam_choices)
                # Use create_enemy (now families-aware) to follow normal flow
                npc = creator.create_enemy(name=None, enemy_type=fam_id, level=random.randint(1, 3), location=loc)
                report["combat"].append(_info(npc))
            except Exception as e:
                report["combat"].append({"error": f"family enemy failed at {loc}: {e}"})
        # Boss overlay example on family
        if fam_choices:
            try:
                fam_id = random.choice(fam_choices)
                enemy_id = f"{fam_id}+boss"
                npc = creator.create_enemy(name=None, enemy_type=enemy_id, level=random.randint(2, 4), location=loc)
                report["combat"].append(_info(npc))
            except Exception as e:
                report["combat"].append({"error": f"boss enemy failed at {loc}: {e}"})
        # Variant enemy
        if var_choices:
            try:
                var_id = random.choice(var_choices)
                npc = creator.create_enemy(name=None, enemy_type=var_id, level=random.randint(1, 3), location=loc)
                report["combat"].append(_info(npc))
            except Exception as e:
                report["combat"].append({"error": f"variant enemy failed at {loc}: {e}"})

    # Persist JSON report
    _ensure_dir(REPORT_PATH)
    with open(REPORT_PATH, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2, ensure_ascii=False)
    return report


def _print_summary(report: Dict[str, Any]) -> None:
    print("NPC Headless Generation Report")
    print(f"Mode: {report['meta'].get('mode')}  Difficulty: {report['meta'].get('difficulty')}  Encounter: {report['meta'].get('encounter_size')}")
    print("")
    print("Non-Combat NPCs:")
    for entry in report.get("non_combat", []):
        if "error" in entry:
            print(" - ERROR:", entry["error"]) 
            continue
        print(f" - {entry['name']}  [{entry['npc_type']}]  loc={entry['location']}  tags={','.join(entry.get('tags', [])) or '-'}")
    print("")
    print("Combat NPCs:")
    for entry in report.get("combat", []):
        if "error" in entry:
            print(" - ERROR:", entry["error"]) 
            continue
        stats = entry.get("stats", {})
        print(f" - {entry['name']}  fam={entry.get('family_id') or '-'} boss={'Y' if entry.get('is_boss') else 'N'} role={entry.get('role') or '-'} abilities={entry.get('abilities_count')} stats=HP:{stats.get('HP')} DEF:{stats.get('Defense')} INIT:{stats.get('Initiative')}")


if __name__ == "__main__":
    rep = run_report()
    _print_summary(rep)

