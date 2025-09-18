#!/usr/bin/env python3
import sys
import json
from pathlib import Path

# Simple cross-file sanity checks for NPC config files.
# - Verify variant.family_id points to an existing family across both families.json and families_factions.json
# - Verify tags used in default_tags/rules.* and variants.tags_* are known in config/npc/tags.json (if present)
# - Verify aliases file conforms to its schema via the existing validator (optional if schema already validated)

ROOT = Path(__file__).resolve().parents[1]
NPC_DIR = ROOT / "config" / "npc"
SCHEMAS = ROOT / "config" / "schemas"

FAMILY_FILES = [
    NPC_DIR / "families.json",
    NPC_DIR / "families_factions.json",
]
VARIANTS_FILE = NPC_DIR / "variants.json"
TAGS_FILE = NPC_DIR / "tags.json"
ALIASES_FILE = ROOT / "config" / "aliases" / "entities.json"


def load_json(path: Path):
    if not path.exists():
        return None
    return json.loads(path.read_text(encoding="utf-8"))


def collect_families():
    families = {}
    for f in FAMILY_FILES:
        data = load_json(f)
        if not data:
            continue
        fams = data.get("families", {})
        for k, v in fams.items():
            if k in families:
                # Note: later files win; record duplicate warning
                pass
            families[k] = v
    return families


def parse_tags(tag_str: str):
    if ":" not in tag_str:
        return None, None
    cat, val = tag_str.split(":", 1)
    return cat, val


def collect_known_tags():
    data = load_json(TAGS_FILE) or {}
    catalog = data.get("tags", {})
    return {cat: set(vals) for cat, vals in catalog.items()}


def check_families_and_variants():
    problems = []
    families = collect_families()
    known_family_ids = set(families.keys())

    # family.id should match its key
    for key, fam in families.items():
        fid = fam.get("id")
        if fid != key:
            problems.append(f"Family key '{key}' has mismatched id '{fid}'")

    # variants reference existing family_id
    variants = (load_json(VARIANTS_FILE) or {}).get("variants", {})
    for vkey, var in variants.items():
        fam_id = var.get("family_id")
        if fam_id not in known_family_ids:
            problems.append(f"Variant '{vkey}' references unknown family_id '{fam_id}'")

    return problems


def check_tags_usage():
    problems = []
    catalog = collect_known_tags()

    def validate_tag(tag: str, context: str):
        cat, val = parse_tags(tag)
        if not cat:
            problems.append(f"{context}: tag '{tag}' missing category:value format")
            return
        if cat not in catalog:
            problems.append(f"{context}: tag category '{cat}' not in catalog")
            return
        if val not in catalog[cat]:
            problems.append(f"{context}: tag value '{val}' not in catalog[{cat}]")

    families = collect_families()
    for fkey, fam in families.items():
        for tag in fam.get("default_tags", []) or []:
            validate_tag(tag, f"family:{fkey}:default_tags")
        rules = fam.get("rules", {}) or {}
        for tag in rules.get("require_tags", []) or []:
            validate_tag(tag, f"family:{fkey}:rules.require_tags")
        for tag in rules.get("forbid_tags", []) or []:
            validate_tag(tag, f"family:{fkey}:rules.forbid_tags")

    variants = (load_json(VARIANTS_FILE) or {}).get("variants", {})
    for vkey, var in variants.items():
        for tag in var.get("tags_add", []) or []:
            validate_tag(tag, f"variant:{vkey}:tags_add")
        for tag in var.get("tags_remove", []) or []:
            validate_tag(tag, f"variant:{vkey}:tags_remove")

    return problems


def main() -> int:
    problems = []
    problems += check_families_and_variants()
    problems += check_tags_usage()

    if problems:
        print("SANITY CHECK: FAIL")
        for p in problems:
            print(f"- {p}")
        return 1

    print("SANITY CHECK: OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

