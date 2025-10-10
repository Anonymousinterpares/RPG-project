#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
backfill_spell_roles.py

Purpose
- Clean and normalize existing magic systems and spells in a JSON file.
- Deduplicate erroneous or duplicate effect specifications per deterministic rules.
- Backfill a new spell-level field "combat_role" with allowed values: 'offensive', 'defensive', 'utility'.
- Produce a structured JSON report with details of duplicate merges, role assignments, ambiguities, and malformed fields corrected.
- Support dry run (default) writing only a report, and an --apply mode that replaces the original file after making a timestamped backup.

Windows 11 friendly: uses pathlib for path handling. Pretty-prints JSON output.

Key Rules Implemented
1) Deduplication of effects within a spell (effects array):
   - Effects are grouped by a semantic key: (effect_type, target_type, stat_affected, status_effect) after trimming/lowercasing string fields.
   - Exact duplicates: if all canonical fields match exactly (including numeric values and duration), keep the first and drop the rest; record in report.
   - Near-duplicates (AI artifacts) differing only by magnitude or duration are merged using deterministic rules:
     a) damage/healing: prefer an entry with non-empty dice_notation; if multiple have dice_notation, keep the first; otherwise keep the one with the highest numeric value; if tie, keep the first.
     b) stat_modification: keep the entry with the largest absolute value; if a tie, keep the one with the longer duration; if still a tie, keep the first.
     c) status_effect: keep the entry with the longer duration; if tie, keep the first.
   - All removed entries for a group are recorded in duplicates_found with the kept_effect and reason.

2) Normalization:
   - Trim all string fields in spells and effects.
   - Coerce numeric fields: value -> float; duration -> int (rounding down); if coercion fails, set to a safe default (0) and record the correction in malformed_entries.
   - Ensure optional effect fields exist with empty string when not set: stat_affected, status_effect, dice_notation, description.
   - Ensure the spell-level fields target, casting_time, and range exist; if missing, set to an empty string and record the correction.
   - Do not introduce any new effect fields beyond the existing set.

3) Combat role backfilling per spell:
   - offensive if any effect is damage OR tags include 'debuff' OR an effect reduces stats (stat_modification with value < 0) OR applies a negative status (e.g., Frightened, Stunned, Poisoned, Restrained, Silenced, Cursed, Blinded, Weakened, Slowed, Disrupted).
   - defensive if any effect is healing OR a cleanse/status removal OR a stat increase (stat_modification with value > 0) or shield/buff on the caster or allies.
   - utility otherwise.
   - If both offensive and defensive indicators appear:
       Prefer offensive if there is direct damage or a negative status; otherwise prefer defensive.
   - Ambiguities are recorded under ambiguous_role including signals and chosen role.

4) Structure handling and output:
   - The input may contain top-level { "magic_systems": ... } or be directly the magic systems. Systems/spells can be dicts or lists; the script normalizes to dicts keyed by their 'id'.
   - Pretty-printed JSON output with indent=2. Does not change top-level structure beyond normalizing containers.
   - On --apply, creates a timestamped backup in the provided backup directory and overwrites the input file.

CLI
- Dry run and report:
    python tools/backfill_spell_roles.py --input "config/world/base/magic_systems.json" --report "logs/magic_systems_clean_report.json"
- Apply in place (with backup):
    python tools/backfill_spell_roles.py --input "config/world/base/magic_systems.json" --apply --backup-dir "config/world/base/backup" --report "logs/magic_systems_clean_report.json"
- Optional output without applying:
    python tools/backfill_spell_roles.py --input ".../magic_systems.json" --output ".../magic_systems.cleaned.json" --report "logs/magic_systems_clean_report.json"

Exit Codes
- 0 on success
- non-zero on critical errors

Notes
- This script performs data cleaning only; it does not change gameplay behavior.
- The new parameter is written exactly as combat_role with values 'offensive', 'defensive', or 'utility'.
"""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Tuple, Optional
from datetime import datetime
import shutil

# Allowed effect fields
EFFECT_FIELDS = [
    "target_type",          # "caster" | "target"
    "effect_type",          # "damage" | "healing" | "stat_modification" | "status_effect"
    "value",                # number
    "stat_affected",        # string
    "status_effect",        # string
    "duration",             # int
    "dice_notation",        # string
    "description",          # string
]

NEGATIVE_STATUS_TOKENS = {
    # common negative statuses (case-insensitive match via substring search)
    "fright", "stun", "poison", "blind", "restrain", "silenc", "curse", "weaken", "slow", "disrupt", "paraly", "daze", "fear"
}

CLEANSING_TOKENS = {"cleanse", "purify", "dispel", "remove", "cure"}

SpellDict = Dict[str, Any]
Effect = Dict[str, Any]


@dataclass
class DuplicateRecord:
    system_id: str
    spell_id: str
    reason: str
    kept_effect: Effect
    removed_effects: List[Effect]


@dataclass
class RoleAssignment:
    system_id: str
    spell_id: str
    role: str
    reasons: List[str]


@dataclass
class AmbiguousRole:
    system_id: str
    spell_id: str
    signals_found: List[str]
    chosen_role: str
    note: str


@dataclass
class MalformedEntry:
    path: str
    reason: str
    raw: Any


@dataclass
class Report:
    duplicates_found: List[DuplicateRecord] = field(default_factory=list)
    role_assignments: List[RoleAssignment] = field(default_factory=list)
    ambiguous_role: List[AmbiguousRole] = field(default_factory=list)
    malformed_entries: List[MalformedEntry] = field(default_factory=list)
    summary: Dict[str, Any] = field(default_factory=dict)

    def to_json(self) -> Dict[str, Any]:
        return {
            "duplicates_found": [
                {
                    "system_id": d.system_id,
                    "spell_id": d.spell_id,
                    "reason": d.reason,
                    "kept_effect": d.kept_effect,
                    "removed_effects": d.removed_effects,
                }
                for d in self.duplicates_found
            ],
            "role_assignments": [
                {
                    "system_id": r.system_id,
                    "spell_id": r.spell_id,
                    "role": r.role,
                    "reasons": r.reasons,
                }
                for r in self.role_assignments
            ],
            "ambiguous_role": [
                {
                    "system_id": a.system_id,
                    "spell_id": a.spell_id,
                    "signals_found": a.signals_found,
                    "chosen_role": a.chosen_role,
                    "note": a.note,
                }
                for a in self.ambiguous_role
            ],
            "malformed_entries": [
                {
                    "path": m.path,
                    "reason": m.reason,
                    "raw": m.raw,
                }
                for m in self.malformed_entries
            ],
            "summary": self.summary,
        }


def _trim(s: Any) -> str:
    if s is None:
        return ""
    if isinstance(s, str):
        return s.strip()
    return str(s).strip()


def _to_float(value: Any, on_error: float, report: Report, path: str) -> float:
    try:
        if isinstance(value, (int, float)):
            return float(value)
        text = str(value).strip()
        # handle commas or other locale artifacts
        text = text.replace(",", "")
        return float(text)
    except Exception:
        report.malformed_entries.append(
            MalformedEntry(path=path, reason="value not numeric; coerced to 0", raw=value)
        )
        return float(on_error)


def _to_int(value: Any, on_error: int, report: Report, path: str) -> int:
    try:
        if isinstance(value, bool):
            # Avoid True -> 1 surprises
            raise ValueError("bool not allowed for duration")
        if isinstance(value, int):
            return value
        if isinstance(value, float):
            return int(value)
        text = str(value).strip()
        # drop trailing non-digits if basic forms like "10s"
        num = ""
        for ch in text:
            if ch.isdigit() or (ch == "-" and not num):
                num += ch
            elif num:
                break
        return int(num) if num else on_error
    except Exception:
        report.malformed_entries.append(
            MalformedEntry(path=path, reason="duration not integer; coerced to 0", raw=value)
        )
        return int(on_error)


def _normalize_effect(effect: Effect, report: Report, base_path: str) -> Effect:
    # Create a shallow copy and normalize allowed fields only; preserve unknown fields as-is
    eff = dict(effect)

    # Ensure required fields exist
    for k in EFFECT_FIELDS:
        if k not in eff:
            # create default for missing fields
            if k in ("value", "duration"):
                eff[k] = 0
            else:
                eff[k] = ""
            report.malformed_entries.append(
                MalformedEntry(path=f"{base_path}.effects[].{k}", reason="missing field; defaulted", raw=None)
            )

    eff["target_type"] = _trim(eff.get("target_type"))
    eff["effect_type"] = _trim(eff.get("effect_type")).lower()
    eff["stat_affected"] = _trim(eff.get("stat_affected"))
    eff["status_effect"] = _trim(eff.get("status_effect"))
    eff["dice_notation"] = _trim(eff.get("dice_notation"))
    eff["description"] = _trim(eff.get("description"))

    eff["value"] = _to_float(eff.get("value"), 0.0, report, f"{base_path}.effects[].value")
    eff["duration"] = _to_int(eff.get("duration"), 0, report, f"{base_path}.effects[].duration")

    return eff


def _semantic_group_key(eff: Effect) -> Tuple[str, str, str, str]:
    return (
        _trim(eff.get("effect_type", "")).lower(),
        _trim(eff.get("target_type", "")).lower(),
        _trim(eff.get("stat_affected", "")).lower(),
        _trim(eff.get("status_effect", "")).lower(),
    )


def _canonical_effect_snapshot(eff: Effect) -> Dict[str, Any]:
    # Snapshot with only allowed fields for exact comparison
    snap: Dict[str, Any] = {}
    for k in EFFECT_FIELDS:
        snap[k] = eff.get(k)
    return snap


def _choose_preferred_effect(effect_type: str, candidates: List[Effect]) -> Tuple[Effect, str]:
    reason = ""
    if effect_type in ("damage", "healing"):
        # Prefer an effect that uses dice_notation if present; if multiple, keep the first
        dice_candidates = [e for e in candidates if _trim(e.get("dice_notation"))]
        if dice_candidates:
            reason = "preferred dice_notation variant among near-duplicates"
            return dice_candidates[0], reason
        # Else choose the one with highest numeric value
        best = max(candidates, key=lambda e: float(e.get("value", 0.0)))
        reason = "kept highest numeric value among near-duplicates"
        return best, reason
    elif effect_type == "stat_modification":
        # Keep largest absolute value; if tie, longest duration; else first
        def key(e: Effect) -> Tuple[float, int]:
            return (abs(float(e.get("value", 0.0))), int(e.get("duration", 0)))

        best = max(candidates, key=key)
        reason = "kept largest absolute value (then longer duration) among near-duplicates"
        return best, reason
    elif effect_type == "status_effect":
        # Keep longer duration
        best = max(candidates, key=lambda e: int(e.get("duration", 0)))
        reason = "kept longer duration among near-duplicates"
        return best, reason
    # Fallback: keep first
    return candidates[0], "kept first occurrence by default"


def _deduplicate_effects(effects: List[Effect], report: Report, system_id: str, spell_id: str, base_path: str) -> Tuple[List[Effect], int]:
    # Normalize and group effects
    normalized: List[Effect] = []
    for idx, eff in enumerate(effects or []):
        norm = _normalize_effect(eff, report, f"{base_path}.effects[{idx}]")
        normalized.append(norm)

    by_group: Dict[Tuple[str, str, str, str], List[Effect]] = {}
    for eff in normalized:
        by_group.setdefault(_semantic_group_key(eff), []).append(eff)

    deduped: List[Effect] = []
    removed_count = 0

    for key, group in by_group.items():
        if len(group) == 1:
            deduped.append(group[0])
            continue

        # Check if exact duplicates exist (by canonical snapshot)
        seen_snapshots: Dict[str, Effect] = {}
        exact_dupes: List[Effect] = []
        unique_in_group: List[Effect] = []

        for eff in group:
            snap = json.dumps(_canonical_effect_snapshot(eff), sort_keys=True)
            if snap in seen_snapshots:
                exact_dupes.append(eff)
            else:
                seen_snapshots[snap] = eff
                unique_in_group.append(eff)

        if exact_dupes:
            kept = unique_in_group[0]
            removed = exact_dupes
            removed_count += len(removed)
            report.duplicates_found.append(
                DuplicateRecord(
                    system_id=system_id,
                    spell_id=spell_id,
                    reason="exact duplicate effects detected in same semantic group",
                    kept_effect=kept,
                    removed_effects=removed,
                )
            )

        # If more than one unique remains, apply near-duplicate merge rule
        if len(unique_in_group) > 1:
            effect_type = key[0]
            kept, why = _choose_preferred_effect(effect_type, unique_in_group)
            removed = [e for e in unique_in_group if e is not kept]
            removed_count += len(removed)
            report.duplicates_found.append(
                DuplicateRecord(
                    system_id=system_id,
                    spell_id=spell_id,
                    reason=f"near-duplicates merged: {why}",
                    kept_effect=kept,
                    removed_effects=removed,
                )
            )
            deduped.append(kept)
        else:
            deduped.append(unique_in_group[0])

    # Preserve original order as much as possible: deduped currently groups by semantic key order
    # To preserve original order, sort deduped by first occurrence index from original list
    index_map = {id(eff): idx for idx, eff in enumerate(normalized)}
    deduped.sort(key=lambda e: index_map.get(id(e), 0))

    return deduped, removed_count


def _has_negative_status(name: str) -> bool:
    low = name.strip().lower()
    if not low:
        return False
    return any(tok in low for tok in NEGATIVE_STATUS_TOKENS)


def _looks_like_cleansing(status_name: str, description: str) -> bool:
    low = (status_name or "") + " " + (description or "")
    low = low.lower()
    return any(tok in low for tok in CLEANSING_TOKENS)


def _derive_combat_role(spell: SpellDict) -> Tuple[str, List[str], List[str]]:
    reasons: List[str] = []
    signals: List[str] = []

    tags = [(_trim(t)).lower() for t in (spell.get("tags") or []) if isinstance(t, str)]

    # Effect signals
    offense = False
    defense = False

    for eff in spell.get("effects") or []:
        et = _trim(eff.get("effect_type")).lower()
        tgt = _trim(eff.get("target_type")).lower()
        val = eff.get("value", 0)
        valf = 0.0
        try:
            valf = float(val)
        except Exception:
            valf = 0.0
        status_name = _trim(eff.get("status_effect"))
        desc = _trim(eff.get("description"))

        if et == "damage":
            offense = True
            signals.append("damage_effect_present")
            reasons.append("damage effect present")
        if et == "healing":
            defense = True
            signals.append("healing_effect_present")
            reasons.append("healing effect present")
        if et == "stat_modification":
            if valf < 0:
                offense = True
                signals.append("negative_stat_mod")
                reasons.append(f"stat_modification negative value {valf}")
            elif valf > 0:
                defense = True
                # target_type is caster or target; positive buff is defensive either way per rule
                if tgt == "caster":
                    signals.append("positive_stat_mod_self")
                    reasons.append("positive stat_mod on caster")
                else:
                    signals.append("positive_stat_mod")
                    reasons.append("positive stat_mod")
        if et == "status_effect":
            if _has_negative_status(status_name):
                offense = True
                signals.append(f"negative_status:{status_name}")
                reasons.append(f"applies negative status '{status_name}'")
            if _looks_like_cleansing(status_name, desc):
                defense = True
                signals.append("cleanse_or_removal")
                reasons.append("status cleanse/removal")

    # Tag-based signals
    if "debuff" in tags:
        offense = True
        signals.append("tag:debuff")
        reasons.append("tag includes 'debuff'")

    # Decide role
    if offense and defense:
        # Prefer offensive if there is direct damage or negative status
        prefer_offensive = any(s.startswith("damage_effect_present") or s.startswith("negative_status:") for s in signals)
        role = "offensive" if prefer_offensive else "defensive"
        return role, reasons, signals
    if offense:
        return "offensive", reasons, signals
    if defense:
        return "defensive", reasons, signals
    return "utility", reasons or ["no offensive/defensive indicators; defaulting to utility"], signals


def _normalize_spells_container(spells: Any, report: Report, sys_id: str) -> Dict[str, SpellDict]:
    # Normalize spells from dict or list to dict keyed by id
    result: Dict[str, SpellDict] = {}
    if isinstance(spells, dict):
        for sid, sobj in spells.items():
            if isinstance(sobj, dict):
                result[sid] = sobj
        return result
    if isinstance(spells, list):
        for idx, sobj in enumerate(spells):
            if not isinstance(sobj, dict):
                report.malformed_entries.append(
                    MalformedEntry(path=f"magic_systems.{sys_id}.spells[{idx}]", reason="spell entry not object; skipped", raw=sobj)
                )
                continue
            sid = _trim(sobj.get("id")) or f"__auto_{idx}"
            result[sid] = sobj
        return result
    # Unknown type
    report.malformed_entries.append(
        MalformedEntry(path=f"magic_systems.{sys_id}.spells", reason="spells container not dict/list; skipped", raw=str(type(spells)))
    )
    return {}


def _normalize_systems_container(data: Any, report: Report) -> Tuple[Dict[str, Any], bool]:
    # Returns (systems_dict, wrapped) where wrapped indicates whether systems were inside a top-level 'magic_systems'
    if isinstance(data, dict) and "magic_systems" in data:
        systems = data["magic_systems"]
        systems_dict: Dict[str, Any] = {}
        if isinstance(systems, dict):
            for sid, sobj in systems.items():
                if isinstance(sobj, dict):
                    systems_dict[sid] = sobj
        elif isinstance(systems, list):
            for idx, sobj in enumerate(systems):
                if not isinstance(sobj, dict):
                    report.malformed_entries.append(
                        MalformedEntry(path=f"magic_systems[{idx}]", reason="system entry not object; skipped", raw=sobj)
                    )
                    continue
                sid = _trim(sobj.get("id")) or f"__auto_sys_{idx}"
                systems_dict[sid] = sobj
        else:
            report.malformed_entries.append(
                MalformedEntry(path="magic_systems", reason="magic_systems container not dict/list", raw=str(type(systems)))
            )
        return systems_dict, True
    # Data might itself be the systems container
    systems_dict: Dict[str, Any] = {}
    if isinstance(data, dict):
        # assume map of id -> system objects
        for sid, sobj in data.items():
            if isinstance(sobj, dict):
                systems_dict[sid] = sobj
        return systems_dict, False
    if isinstance(data, list):
        for idx, sobj in enumerate(data):
            if not isinstance(sobj, dict):
                report.malformed_entries.append(
                    MalformedEntry(path=f"[systems][{idx}]", reason="system entry not object; skipped", raw=sobj)
                )
                continue
            sid = _trim(sobj.get("id")) or f"__auto_sys_{idx}"
            systems_dict[sid] = sobj
        return systems_dict, False
    report.malformed_entries.append(
        MalformedEntry(path="<root>", reason="top-level not dict/list", raw=str(type(data)))
    )
    return {}, False


def process_file(input_path: Path) -> Tuple[Dict[str, Any], Report, Dict[str, Any]]:
    report = Report()
    with input_path.open("r", encoding="utf-8") as f:
        data = json.load(f)

    systems_dict, wrapped = _normalize_systems_container(data, report)

    total_systems = 0
    total_spells = 0
    spells_modified = 0
    effects_deduplicated = 0

    for sys_id, system in systems_dict.items():
        total_systems += 1
        # Normalize spells container
        spells_dict = _normalize_spells_container(system.get("spells"), report, sys_id)

        for spell_id, spell in spells_dict.items():
            total_spells += 1
            base_path = f"magic_systems.{sys_id}.spells.{spell_id}"

            # Ensure spell-level fields
            initial_spell_snapshot = json.dumps(spell, sort_keys=True)

            # Normalize string fields
            for fld in ("id", "name", "description", "casting_time", "range", "target"):
                if fld in spell:
                    spell[fld] = _trim(spell[fld])
                else:
                    # add missing required display fields as empty string
                    if fld in ("casting_time", "range", "target"):
                        spell[fld] = ""
                        report.malformed_entries.append(
                            MalformedEntry(path=f"{base_path}.{fld}", reason="missing field; defaulted to empty string", raw=None)
                        )

            # Coerce mana_cost numeric if present
            if "mana_cost" in spell:
                spell["mana_cost"] = _to_float(spell["mana_cost"], 0.0, report, f"{base_path}.mana_cost")

            # Deduplicate effects
            original_effects = list(spell.get("effects") or [])
            deduped_effects, removed = _deduplicate_effects(original_effects, report, sys_id, spell_id, base_path)
            effects_deduplicated += removed
            spell["effects"] = deduped_effects

            # Derive combat role
            role, reasons, signals = _derive_combat_role(spell)
            chosen_role = role

            # Determine ambiguity:
            offense = any(r.startswith("damage effect present") or s.startswith("negative_status:") or s == "negative_stat_mod" or s == "tag:debuff" for r, s in zip(reasons + [""], signals + [""]))
            # The above zip approach only checks some; implement robust offense/defense flags again
            offense_flag = any(s in signals for s in ["damage_effect_present", "negative_stat_mod", "tag:debuff"]) or any(s.startswith("negative_status:") for s in signals)
            defense_flag = any(s in signals for s in ["healing_effect_present", "cleanse_or_removal", "positive_stat_mod_self", "positive_stat_mod"]) \
                or ("shield" in ",".join((spell.get("tags") or [])).lower())

            is_ambiguous = offense_flag and defense_flag
            if is_ambiguous:
                report.ambiguous_role.append(
                    AmbiguousRole(
                        system_id=sys_id,
                        spell_id=spell_id,
                        signals_found=signals,
                        chosen_role=chosen_role,
                        note="Both offensive and defensive indicators present; applied preference rule",
                    )
                )

            # Record role assignment
            report.role_assignments.append(
                RoleAssignment(system_id=sys_id, spell_id=spell_id, role=chosen_role, reasons=reasons)
            )

            # Backfill combat_role into spell
            if spell.get("combat_role") != chosen_role:
                spell["combat_role"] = chosen_role

            # Track modified
            final_snapshot = json.dumps(spell, sort_keys=True)
            if final_snapshot != initial_spell_snapshot:
                spells_modified += 1

        # Save normalized spells back
        system["spells"] = spells_dict

    # Rewrap if needed
    cleaned: Dict[str, Any]
    if isinstance(data, dict) and "magic_systems" in data:
        cleaned = dict(data)
        cleaned["magic_systems"] = systems_dict
    else:
        cleaned = systems_dict

    report.summary = {
        "total_systems": total_systems,
        "total_spells": total_spells,
        "spells_modified": spells_modified,
        "effects_deduplicated": effects_deduplicated,
    }

    return cleaned, report, data


def write_json(path: Path, payload: Dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)
        f.write("\n")


def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(description="Clean, deduplicate, and backfill combat_role for magic systems JSON.")
    parser.add_argument("--input", required=True, help="Path to input magic_systems.json")
    parser.add_argument("--report", required=False, default="logs/magic_systems_clean_report.json", help="Path to write structured JSON report")
    parser.add_argument("--output", required=False, default=None, help="Optional path to write cleaned JSON (no overwrite unless --apply)")
    parser.add_argument("--apply", action="store_true", help="If provided, replace the input file with cleaned data after creating a timestamped backup")
    parser.add_argument("--backup-dir", required=False, default="config/world/base/backup", help="Backup directory used when --apply is set")

    args = parser.parse_args(argv)

    try:
        input_path = Path(args.input)
        if not input_path.exists():
            print(f"ERROR: input file not found: {input_path}", file=sys.stderr)
            return 2

        cleaned, report, original = process_file(input_path)

        # Write report
        if args.report:
            report_path = Path(args.report)
            write_json(report_path, report.to_json())
            print(f"Report written to: {report_path}")

        # Apply or output
        if args.apply:
            backup_dir = Path(args.backup_dir)
            backup_dir.mkdir(parents=True, exist_ok=True)
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_path = backup_dir / f"magic_systems.backup_{timestamp}.json"
            # Copy original file to backup first
            shutil.copy2(input_path, backup_path)
            print(f"Backup created at: {backup_path}")
            # Overwrite input with cleaned
            write_json(input_path, cleaned)
            print(f"Applied cleaned data to: {input_path}")
        else:
            if args.output:
                output_path = Path(args.output)
                write_json(output_path, cleaned)
                print(f"Cleaned JSON written to: {output_path}")
            else:
                print("Dry run complete (no cleaned JSON written; use --output to write or --apply to replace input)")

        # Success
        return 0
    except Exception as e:
        print(f"ERROR: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
