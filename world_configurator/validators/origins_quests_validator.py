#!/usr/bin/env python3
"""
Validate world config data: ensure Origins.initial_quests reference valid quest IDs
and report duplicates.

Usage (module import): call validate(origins: dict, quests: dict) -> dict with results.
This module is used by the World Configurator or CI checks.
"""
from __future__ import annotations
from typing import Dict, List, Any


def _as_str_list(value: Any) -> List[str]:
    out: List[str] = []
    if isinstance(value, list):
        for el in value:
            if isinstance(el, str) and el.strip():
                out.append(el.strip())
            elif isinstance(el, dict):
                vid = el.get("id")
                if isinstance(vid, str) and vid.strip():
                    out.append(vid.strip())
    return out


def validate(origins: Dict[str, Any], quests: Dict[str, Any]) -> Dict[str, Any]:
    """
    Validate initial_quests across all origins.

    Returns a report dict with keys:
    - ok: bool
    - issues: List[str]
    - stats: dict
    """
    issues: List[str] = []
    quest_ids = set(quests.keys()) if isinstance(quests, dict) else set()

    total_refs = 0
    invalid_refs = 0
    duplicates = 0

    if not isinstance(origins, dict):
        return {"ok": False, "issues": ["origins is not a dict"], "stats": {}}

    for oid, odata in origins.items():
        init = _as_str_list(odata.get("initial_quests", []))
        total_refs += len(init)
        seen = set()
        for qid in init:
            if qid in seen:
                duplicates += 1
                issues.append(f"Origin '{oid}': duplicate quest id '{qid}' in initial_quests")
            else:
                seen.add(qid)
            if qid not in quest_ids:
                invalid_refs += 1
                issues.append(f"Origin '{oid}': unknown quest id '{qid}' in initial_quests")

    ok = (invalid_refs == 0)
    return {
        "ok": ok,
        "issues": issues,
        "stats": {
            "total_refs": total_refs,
            "invalid_refs": invalid_refs,
            "duplicates": duplicates,
        },
    }

