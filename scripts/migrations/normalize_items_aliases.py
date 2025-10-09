#!/usr/bin/env python3
"""
Normalize item JSON stat names and fields using the unified stat registry.

- Scans config/items/**/*.json (recursively).
- Normalizes stat names in any list entries under the "stats" key using registry aliases.
- Detects top-level field typos/synonyms (e.g., "nouse" -> "noise").
- Validates dice_roll_effects[].effect_type against canonical lists (if available).
- Writes a JSON report of findings; optional --apply will write changes back to files.

USAGE (Windows PowerShell):
  python scripts/migrations/normalize_items_aliases.py --report logs/item_normalization_report.json
  # or to apply changes
  python scripts/migrations/normalize_items_aliases.py --apply --report logs/item_normalization_report.json

This script performs a dry-run by default and does not change any source files.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from typing import Dict, Any, List, Tuple

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from core.stats.registry import normalize_to_canonical_id, resolve_stat_enum, is_supported

# Optional: load canonical lists directly from config files
CANONICAL_LISTS_PATH = os.path.join(PROJECT_ROOT, "config", "gameplay", "canonical_lists.json")

def _load_json(path: str) -> Any:
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return None


def _save_json(path: str, data: Any) -> bool:
    try:
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        return True
    except Exception:
        return False


def _gather_item_files(root: str) -> List[str]:
    items_dir = os.path.join(root, "config", "items")
    matches: List[str] = []
    for base, _dirs, files in os.walk(items_dir):
        for fn in files:
            if fn.lower().endswith(".json"):
                matches.append(os.path.join(base, fn))
    return matches


def _normalize_stats_list(stats: Any) -> Tuple[Any, Dict[str, Any]]:
    """Normalize a list of {name,value} entries using registry aliases.
    Returns (new_stats, info) where info contains counts and unknowns.
    """
    info = {
        "entries": 0,
        "renamed": [],  # list of {from, to}
        "unknown": [],  # list of names that could not resolve
        "unsupported": [],  # list of names that resolve but not supported by engine
    }
    if not isinstance(stats, list):
        return stats, info

    new_list = []
    for entry in stats:
        if not isinstance(entry, dict):
            continue
        info["entries"] += 1
        name_raw = str(entry.get("name", "")).strip()
        if not name_raw:
            new_list.append(entry)
            continue
        canon = normalize_to_canonical_id(name_raw) or name_raw.upper()
        enum_val = resolve_stat_enum(name_raw)
        if enum_val is None:
            # Could not resolve; keep as-is and report
            info["unknown"].append(name_raw)
            new_list.append(entry)
            continue
        # We have an engine enum: use its enum member name (UPPERCASE) as canonical id
        canon_enum_name = enum_val.name
        if canon_enum_name != name_raw:
            info["renamed"].append({"from": name_raw, "to": canon_enum_name})
        # Check supported status
        if not is_supported(name_raw):
            info["unsupported"].append(name_raw)
        # Write back normalized name
        new_entry = dict(entry)
        new_entry["name"] = canon_enum_name
        new_list.append(new_entry)

    return new_list, info


def _normalize_top_level_fields(data: Dict[str, Any]) -> Dict[str, Any]:
    """Fix common top-level typos/synonyms without altering semantics."""
    if not isinstance(data, dict):
        return data
    rename_map = {
        # typos
        "nouse": "noise",
        "strenght_requirement": "strength_requirement",
        # synonyms (prefer canonical naming)
        "armour": "armor",
    }
    for bad, good in list(rename_map.items()):
        if bad in data and good not in data:
            data[good] = data.pop(bad)
    return data


def _validate_dice_effects(data: Dict[str, Any], allowed_effect_types: List[str]) -> Dict[str, Any]:
    info = {
        "effects": 0,
        "unknown_effect_types": [],
    }
    dre = data.get("dice_roll_effects")
    if not isinstance(dre, list):
        return info
    allowed = {et.strip().lower() for et in (allowed_effect_types or [])}
    for e in dre:
        if not isinstance(e, dict):
            continue
        info["effects"] += 1
        et = str(e.get("effect_type", "")).strip().lower()
        if allowed and et and et not in allowed:
            info["unknown_effect_types"].append(et)
    return info


def main():
    ap = argparse.ArgumentParser(description="Normalize item stats using unified stat registry.")
    ap.add_argument("--apply", action="store_true", help="Apply changes to files (default is dry-run)")
    ap.add_argument("--report", type=str, default=os.path.join(PROJECT_ROOT, "logs", "item_normalization_report.json"), help="Path to write JSON report")
    args = ap.parse_args()

    files = _gather_item_files(PROJECT_ROOT)
    canonical_lists = _load_json(CANONICAL_LISTS_PATH) or {}
    allowed_effect_types = canonical_lists.get("damage_types", []) if isinstance(canonical_lists, dict) else []

    report = {
        "root": PROJECT_ROOT,
        "files_scanned": len(files),
        "files": [],
        "summary": {
            "total_entries": 0,
            "total_renamed": 0,
            "total_unknown": 0,
            "total_unsupported": 0,
            "total_unknown_effect_types": 0,
        }
    }

    for fp in files:
        original = _load_json(fp)
        if original is None:
            report["files"].append({"path": fp, "error": "failed_to_load"})
            continue
        data = original
        if isinstance(data, dict):
            items = data.get("items") if "items" in data else data.get("list")
            # Some files may be bare lists, others may be dict with list under specific keys; handle simply
            if isinstance(items, list):
                target_list = items
            else:
                target_list = data if isinstance(data, list) else []
        else:
            target_list = data if isinstance(data, list) else []

        file_stats_entries = 0
        file_renamed = 0
        file_unknown = 0
        file_unsupported = 0
        file_unknown_effect_types = 0

        changed = False

        def _process_item(it: Dict[str, Any]) -> Dict[str, Any]:
            nonlocal file_stats_entries, file_renamed, file_unknown, file_unsupported, file_unknown_effect_types, changed
            if not isinstance(it, dict):
                return it
            # top-level typos
            before_keys = set(it.keys())
            it = _normalize_top_level_fields(it)
            if set(it.keys()) != before_keys:
                changed = True
            # stats list
            stats_list = it.get("stats")
            new_stats, info_stats = _normalize_stats_list(stats_list)
            if new_stats is not stats_list:
                it["stats"] = new_stats
                changed = True
            file_stats_entries += info_stats["entries"]
            file_renamed += len(info_stats["renamed"])
            file_unknown += len(info_stats["unknown"])
            file_unsupported += len(info_stats["unsupported"])
            # dice effects validation
            info_dre = _validate_dice_effects(it, allowed_effect_types)
            file_unknown_effect_types += len(info_dre["unknown_effect_types"])
            return it

        if isinstance(target_list, list):
            for i, item in enumerate(target_list):
                if isinstance(item, dict):
                    target_list[i] = _process_item(item)

        # Save back into the data structure if nested under a key
        if isinstance(data, dict) and isinstance(data.get("items"), list):
            data["items"] = target_list
        elif isinstance(data, dict) and isinstance(data.get("list"), list):
            data["list"] = target_list
        else:
            data = target_list

        report["files"].append({
            "path": fp,
            "entries": file_stats_entries,
            "renamed": file_renamed,
            "unknown": file_unknown,
            "unsupported": file_unsupported,
            "unknown_effect_types": file_unknown_effect_types,
            "changed": bool(changed),
        })

        report["summary"]["total_entries"] += file_stats_entries
        report["summary"]["total_renamed"] += file_renamed
        report["summary"]["total_unknown"] += file_unknown
        report["summary"]["total_unsupported"] += file_unsupported
        report["summary"]["total_unknown_effect_types"] += file_unknown_effect_types

        if args.apply and changed:
            _save_json(fp, data)

    # Write report
    _save_json(args.report, report)
    print(json.dumps({"ok": True, "report": args.report, "files_scanned": report["files_scanned"]}))


if __name__ == "__main__":
    main()
