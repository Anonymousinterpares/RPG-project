#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Analyze magic systems for effect patterns and summarize per-spell effects.

Outputs:
- JSON report with:
  - spells: list of all spells, each with effect summaries
  - groups: repeated patterns across spells (damage, healing, stat_modification, status_effect)
  - summary: counts
- Optional Markdown summary for human review

Usage examples (Windows-friendly paths):
  python tools/analyze_magic_effects.py --input "config/world/base/magic_systems.json" --json-out "logs/magic_effects_analysis.json"
  python tools/analyze_magic_effects.py --input "config/world/base/magic_systems.json" --json-out "logs/magic_effects_analysis.json" --md-out "logs/magic_effects_analysis.md"
"""
from __future__ import annotations

import argparse
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Tuple


@dataclass
class Occurrence:
    system_id: str
    spell_id: str
    spell_name: str


def _trim(s: Any) -> str:
    if s is None:
        return ""
    if isinstance(s, str):
        return s.strip()
    return str(s).strip()


def _normalize_systems(data: Any) -> Dict[str, Dict[str, Any]]:
    # Returns dict of system_id -> system_obj
    if isinstance(data, dict) and "magic_systems" in data:
        systems = data["magic_systems"]
    else:
        systems = data
    result: Dict[str, Dict[str, Any]] = {}
    if isinstance(systems, dict):
        for sid, sobj in systems.items():
            if isinstance(sobj, dict):
                result[_trim(sid) or _trim(sobj.get("id"))] = sobj
    elif isinstance(systems, list):
        for sobj in systems:
            if isinstance(sobj, dict):
                sid = _trim(sobj.get("id"))
                if sid:
                    result[sid] = sobj
    return result


def _normalize_spells_container(spells: Any) -> Dict[str, Dict[str, Any]]:
    if isinstance(spells, dict):
        return {k: v for k, v in spells.items() if isinstance(v, dict)}
    if isinstance(spells, list):
        res: Dict[str, Dict[str, Any]] = {}
        for idx, v in enumerate(spells):
            if isinstance(v, dict):
                sid = _trim(v.get("id")) or f"__auto_{idx}"
                res[sid] = v
        return res
    return {}


def analyze(input_path: Path) -> Dict[str, Any]:
    data = json.loads(input_path.read_text(encoding="utf-8"))
    systems = _normalize_systems(data)

    spells_out: List[Dict[str, Any]] = []

    groups_damage: Dict[str, Dict[str, Any]] = {}
    groups_healing: Dict[str, Dict[str, Any]] = {}
    groups_stat_mod: Dict[str, Dict[str, Any]] = {}
    groups_status: Dict[str, Dict[str, Any]] = {}

    total_effects = 0

    for sys_id, system in systems.items():
        sys_name = _trim(system.get("name")) or sys_id
        spells = _normalize_spells_container(system.get("spells"))
        for spell_id, spell in spells.items():
            spell_name = _trim(spell.get("name")) or spell_id
            level = spell.get("level")
            tags = [ _trim(t) for t in (spell.get("tags") or []) if isinstance(t, str) ]
            effects = spell.get("effects") or []

            spell_effects: List[Dict[str, Any]] = []
            for eff in effects:
                et = _trim(eff.get("effect_type")).lower()
                tgt = _trim(eff.get("target_type")).lower()
                stat = _trim(eff.get("stat_affected"))
                status = _trim(eff.get("status_effect"))
                val = eff.get("value", 0)
                dice = _trim(eff.get("dice_notation"))
                dur = eff.get("duration", 0)
                desc = _trim(eff.get("description"))

                total_effects += 1

                # Record spell-level listing
                spell_effects.append({
                    "effect_type": et,
                    "target_type": tgt,
                    "stat_affected": stat,
                    "status_effect": status,
                    "value": val,
                    "dice_notation": dice,
                    "duration": dur,
                    "description": desc,
                })

                # Groupings across spells
                occ = {"system_id": sys_id, "spell_id": spell_id, "spell_name": spell_name}
                if et == "damage":
                    key = f"{et}::{dice or str(val)}"
                    g = groups_damage.setdefault(key, {"count": 0, "occurrences": []})
                    g["count"] += 1
                    g["occurrences"].append(occ)
                elif et == "healing":
                    key = f"{et}::{dice or str(val)}"
                    g = groups_healing.setdefault(key, {"count": 0, "occurrences": []})
                    g["count"] += 1
                    g["occurrences"].append(occ)
                elif et == "stat_modification":
                    sign = "zero"
                    try:
                        fv = float(val)
                        if fv > 0: sign = "pos"
                        elif fv < 0: sign = "neg"
                    except Exception:
                        pass
                    key = f"{et}::{stat or 'UNSPEC'}::{sign}"
                    g = groups_stat_mod.setdefault(key, {"count": 0, "occurrences": []})
                    g["count"] += 1
                    g["occurrences"].append(occ)
                elif et == "status_effect":
                    key = f"{et}::{status or 'UNSPEC'}"
                    g = groups_status.setdefault(key, {"count": 0, "occurrences": []})
                    g["count"] += 1
                    g["occurrences"].append(occ)

            spells_out.append({
                "system_id": sys_id,
                "system_name": sys_name,
                "spell_id": spell_id,
                "spell_name": spell_name,
                "level": level,
                "tags": tags,
                "effects": spell_effects,
            })

    def sort_groups(g: Dict[str, Dict[str, Any]]) -> List[Tuple[str, Dict[str, Any]]]:
        return sorted(g.items(), key=lambda kv: (-kv[1]["count"], kv[0]))

    result = {
        "spells": spells_out,
        "groups": {
            "damage": {k: v for k, v in sort_groups(groups_damage)},
            "healing": {k: v for k, v in sort_groups(groups_healing)},
            "stat_modification": {k: v for k, v in sort_groups(groups_stat_mod)},
            "status_effect": {k: v for k, v in sort_groups(groups_status)},
        },
        "summary": {
            "total_systems": len(systems),
            "total_spells": len(spells_out),
            "total_effects": total_effects,
        },
    }
    return result


def write_json(path: Path, data: Dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def write_markdown(path: Path, data: Dict[str, Any]) -> None:
    lines: List[str] = []
    lines.append("# Magic Effects Analysis\n")
    summ = data.get("summary", {})
    lines.append(f"Total systems: {summ.get('total_systems', 0)}  ")
    lines.append(f"Total spells: {summ.get('total_spells', 0)}  ")
    lines.append(f"Total effects: {summ.get('total_effects', 0)}\n")

    lines.append("## Spells and Effects\n")
    for sp in data.get("spells", []):
        lines.append(f"### {sp['spell_name']} ({sp['system_id']})")
        tag_str = ", ".join(sp.get("tags", []))
        if tag_str:
            lines.append(f"Tags: {tag_str}")
        for eff in sp.get("effects", []):
            et = eff.get("effect_type")
            tgt = eff.get("target_type")
            stat = eff.get("stat_affected")
            status = eff.get("status_effect")
            val = eff.get("value")
            dice = eff.get("dice_notation")
            dur = eff.get("duration")
            desc = eff.get("description")
            parts = [f"type={et}", f"target={tgt}"]
            if stat:
                parts.append(f"stat={stat}")
            if status:
                parts.append(f"status={status}")
            if dice:
                parts.append(f"dice={dice}")
            else:
                parts.append(f"value={val}")
            if dur:
                parts.append(f"duration={dur}")
            if desc:
                parts.append(f"desc={desc}")
            lines.append("- " + "; ".join(parts))
        lines.append("")

    lines.append("## Grouped Patterns\n")
    groups = data.get("groups", {})
    for gname in ("damage", "healing", "stat_modification", "status_effect"):
        lines.append(f"### {gname}")
        grp = groups.get(gname, {})
        # show top 25 entries by count
        items = list(grp.items())[:25]
        for key, meta in items:
            lines.append(f"- {key}: {meta['count']} occurrences")
        lines.append("")

    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines), encoding="utf-8")


def main() -> int:
    ap = argparse.ArgumentParser(description="Analyze magic effects and group repeated patterns.")
    ap.add_argument("--input", required=True, help="Path to magic_systems.json")
    ap.add_argument("--json-out", required=True, help="Path to write JSON analysis")
    ap.add_argument("--md-out", required=False, help="Optional path to write Markdown summary")
    args = ap.parse_args()

    input_path = Path(args.input)
    out_json = Path(args.json_out)
    out_md = Path(args.md_out) if args.md_out else None

    result = analyze(input_path)
    write_json(out_json, result)
    print(f"Analysis JSON written to: {out_json}")

    if out_md:
        write_markdown(out_md, result)
        print(f"Markdown summary written to: {out_md}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
